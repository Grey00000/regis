import numpy as np
import pandas as pd
from typing import Dict, Any, List
from .markov_model import MarkovChainModel
from .ml_regressor import RegimeMLRegressor

class MonteCarloSimulator:
    """
    Hybrid Markov-ML Monte Carlo Engine.
    Simulates hundreds of forward stochastic price paths by combining:
    1. First-order Markov chain regime transitions.
    2. Regime-conditioned ML regression drift predictions.
    3. Empirical stochastic shocks sampled from regime residuals.
    """
    def __init__(
        self,
        markov_model: MarkovChainModel,
        ml_model: RegimeMLRegressor,
        n_simulations: int = 150,
        forecast_days: int = 30
    ):
        self.markov_model = markov_model
        self.ml_model = ml_model
        self.n_simulations = n_simulations
        self.forecast_days = forecast_days

    def run_simulation(
        self,
        latest_price: float,
        current_state: int,
        latest_features: np.ndarray,
        volatility_multiplier: float = 1.0,
        forced_regime_shock: int = -1,  # -1 means natural Markov transitions, >=0 forces a regime
        shock_duration: int = 5
    ) -> Dict[str, Any]:
        """
        Runs the multi-path Monte Carlo simulation.
        Supports dynamic interactive stress-testing (forced regime shock, volatility shifts).
        """
        simulated_paths = np.zeros((self.n_simulations, self.forecast_days + 1))
        simulated_regimes = np.zeros((self.n_simulations, self.forecast_days + 1), dtype=int)
        
        simulated_paths[:, 0] = latest_price
        simulated_regimes[:, 0] = current_state

        for sim_idx in range(self.n_simulations):
            curr_price = latest_price
            curr_state = current_state
            curr_features = latest_features.copy()

            for day in range(1, self.forecast_days + 1):
                # Check for forced stress-test shock
                if forced_regime_shock >= 0 and day <= shock_duration:
                    next_state = forced_regime_shock
                else:
                    # Transition via Markov Chain
                    probs = self.markov_model.transition_matrix[curr_state]
                    next_state = int(np.random.choice(self.markov_model.n_states, p=probs))

                # Expected drift from regime ML model
                expected_ret = self.ml_model.predict_next(curr_features, next_state)

                # Stochastic shock from empirical residual distribution
                resids = self.ml_model.residuals_by_regime.get(next_state, np.zeros(1))
                if len(resids) > 5:
                    shock = np.random.choice(resids) * volatility_multiplier
                else:
                    default_sigma = 0.015 if next_state == 2 else (0.010 if next_state == 1 else 0.008)
                    shock = np.random.normal(0, default_sigma) * volatility_multiplier

                sim_return = expected_ret + shock
                # Prevent extreme exponential explosion in simulations
                sim_return = np.clip(sim_return, -0.15, 0.15)
                
                curr_price = curr_price * np.exp(sim_return)
                simulated_paths[sim_idx, day] = curr_price
                simulated_regimes[sim_idx, day] = next_state

                # State-space feature update for next step.
                # LIMITATION: only the return (index 0) is updated; volatility, trend, RSI and
                # momentum stay frozen at their last observed values.
                curr_features[0] = sim_return  # updated return
                curr_state = next_state

        # Compute quantiles across all paths
        median_path = np.median(simulated_paths, axis=0)
        p10_path = np.percentile(simulated_paths, 10, axis=0)
        p25_path = np.percentile(simulated_paths, 25, axis=0)
        p75_path = np.percentile(simulated_paths, 75, axis=0)
        p90_path = np.percentile(simulated_paths, 90, axis=0)

        terminal_prices = simulated_paths[:, -1]
        terminal_returns = (terminal_prices - latest_price) / latest_price * 100.0
        
        # Risk metrics
        var_95 = np.percentile(terminal_returns, 5)  # 95% 1-tail VaR
        expected_terminal_return = np.median(terminal_returns)
        prob_positive = np.mean(terminal_returns > 0) * 100.0

        return {
            "paths": simulated_paths,
            "regimes": simulated_regimes,
            "median": median_path,
            "p10": p10_path,
            "p25": p25_path,
            "p75": p75_path,
            "p90": p90_path,
            "terminal_prices": terminal_prices,
            "terminal_returns": terminal_returns,
            "expected_terminal_return": expected_terminal_return,
            "var_95": var_95,
            "prob_positive": prob_positive
        }
