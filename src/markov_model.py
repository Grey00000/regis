import numpy as np
import pandas as pd
from typing import Tuple, List, Dict
from scipy import linalg

class MarkovChainModel:
    """
    First-Order Discrete-Time Markov Chain (DTMC) for Financial Market Regimes.
    Computes:
    - Transition Probability Matrix (P)
    - Stationary Distribution (pi) where pi * P = pi
    - Expected State Holding Times (1 / (1 - P_ii))
    - Multi-step Regime Transitions & Stochastic Path Generation
    """
    def __init__(self, n_states: int = 3, state_names: Dict[int, str] = None):
        self.n_states = n_states
        self.state_names = state_names or {0: "Bull", 1: "Neutral", 2: "Bear"}
        self.transition_counts = np.zeros((n_states, n_states), dtype=int)
        self.transition_matrix = np.zeros((n_states, n_states), dtype=float)
        self.stationary_distribution = np.zeros(n_states, dtype=float)
        self.expected_holding_times = np.zeros(n_states, dtype=float)

    def fit(self, regime_series: pd.Series) -> "MarkovChainModel":
        """
        Estimates the empirical transition probability matrix from a sequence of states.
        """
        states = regime_series.values
        self.transition_counts = np.zeros((self.n_states, self.n_states), dtype=int)
        
        for t in range(len(states) - 1):
            s_from = int(states[t])
            s_to = int(states[t + 1])
            if 0 <= s_from < self.n_states and 0 <= s_to < self.n_states:
                self.transition_counts[s_from, s_to] += 1
                
        # Row-normalize to probabilities
        self.transition_matrix = np.zeros((self.n_states, self.n_states), dtype=float)
        for i in range(self.n_states):
            row_sum = np.sum(self.transition_counts[i])
            if row_sum > 0:
                self.transition_matrix[i] = self.transition_counts[i] / row_sum
            else:
                self.transition_matrix[i, i] = 1.0  # absorbing state fallback
                
        self._compute_stationary_distribution()
        self._compute_holding_times()
        return self

    def _compute_stationary_distribution(self):
        """
        Solves for the stationary distribution pi:
        pi * P = pi  <=>  (P.T - I) * pi = 0, with sum(pi) = 1.
        """
        try:
            P = self.transition_matrix
            # Eigenvector of P.T corresponding to eigenvalue 1
            evals, evecs = linalg.eig(P.T)
            # Find the eigenvalue closest to 1.0
            idx = np.argmin(np.abs(evals - 1.0))
            stationary = np.real(evecs[:, idx])
            # Ensure non-negative and normalized
            stationary = np.maximum(stationary, 0)
            self.stationary_distribution = stationary / np.sum(stationary)
        except Exception:
            # Fallback uniform
            self.stationary_distribution = np.ones(self.n_states) / self.n_states

    def _compute_holding_times(self):
        """
        Expected holding time (sojourn time) in state i:
        E[T_i] = 1 / (1 - P_ii)
        """
        self.expected_holding_times = np.zeros(self.n_states)
        for i in range(self.n_states):
            p_ii = self.transition_matrix[i, i]
            if p_ii < 0.9999:
                self.expected_holding_times[i] = 1.0 / (1.0 - p_ii)
            else:
                self.expected_holding_times[i] = 999.0  # virtually absorbing

    def simulate_path(self, current_state: int, steps: int = 30) -> np.ndarray:
        """
        Generates a sequence of states using the transition probability matrix.
        """
        path = [current_state]
        state = current_state
        for _ in range(steps):
            probs = self.transition_matrix[state]
            state = np.random.choice(self.n_states, p=probs)
            path.append(state)
        return np.array(path[1:])  # return the future 'steps' states

    def get_transition_dataframe(self) -> pd.DataFrame:
        """Returns the transition matrix formatted as a clean DataFrame."""
        labels = [self.state_names.get(i, f"State {i}") for i in range(self.n_states)]
        df = pd.DataFrame(
            self.transition_matrix,
            index=[f"From {lbl}" for lbl in labels],
            columns=[f"To {lbl}" for lbl in labels]
        )
        return df

    def get_theoretical_summary(self) -> pd.DataFrame:
        """Returns key DTMC theoretical properties."""
        records = []
        for i in range(self.n_states):
            records.append({
                "Regime": self.state_names.get(i, f"State {i}"),
                "Self-Transition P(i->i)": f"{self.transition_matrix[i, i]:.3f}",
                "Expected Duration": f"{self.expected_holding_times[i]:.1f} days",
                "Long-Run Equilibrium (π)": f"{self.stationary_distribution[i] * 100:.1f}%"
            })
        return pd.DataFrame(records)
