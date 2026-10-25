import sys
from src.data_loader import generate_synthetic_market_data, fetch_market_data
from src.regime_detector import RegimeDetector, STATE_LABELS
from src.markov_model import MarkovChainModel
from src.ml_regressor import RegimeMLRegressor
from src.monte_carlo import MonteCarloSimulator

def test_full_pipeline():
    print("[1/5] Testing data loading...")
    df, is_real = fetch_market_data("AAPL", period="1y", fallback_if_offline=True)
    print(f"       Loaded {len(df)} rows. Is live data: {is_real}")
    assert len(df) > 50, "Dataframe too small"

    print("[2/5] Testing regime detection (GMM)...")
    detector = RegimeDetector(n_regimes=3, method="gmm")
    classified_df = detector.fit_predict(df)
    stats = detector.get_regime_statistics(classified_df)
    print(f"       Detected regimes successfully:\n{stats}")
    assert "Regime" in classified_df.columns

    print("[3/5] Testing Markov Chain transition matrix & stationary distribution...")
    markov = MarkovChainModel(n_states=3, state_names=STATE_LABELS)
    markov.fit(classified_df["Regime"])
    print(f"       Stationary distribution π: {markov.stationary_distribution}")
    print(f"       Expected holding times: {markov.expected_holding_times}")
    assert markov.transition_matrix.shape == (3, 3)

    print("[4/5] Testing ML Regression models...")
    ml = RegimeMLRegressor(model_type="ridge")
    ml.fit(classified_df)
    eval_res = ml.evaluate(classified_df)
    print(f"       Model Evaluation Comparison:\n{eval_res['comparison_df']}")
    assert "comparison_df" in eval_res

    print("[5/5] Testing Monte Carlo Simulation...")
    latest_price = float(classified_df["Close"].iloc[-1])
    latest_state = int(classified_df["Regime"].iloc[-1])
    latest_feats = classified_df[ml.feature_cols].iloc[-1].values
    mc = MonteCarloSimulator(markov, ml, n_simulations=50, forecast_days=20)
    sim_res = mc.run_simulation(latest_price, latest_state, latest_feats)
    print(f"       Simulated 50 paths. Terminal median: ${sim_res['median'][-1]:.2f}")
    print(f"       95% VaR: {sim_res['var_95']:.2f}%")
    print("ALL TESTS PASSED SUCCESSFULLY! Ready for presentation.")

if __name__ == "__main__":
    test_full_pipeline()
