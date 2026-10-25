import streamlit as st
import numpy as np
import pandas as pd
import datetime
import io

from src.data_loader import fetch_market_data, generate_synthetic_market_data
from src.regime_detector import RegimeDetector, STATE_LABELS, STATE_COLORS
from src.markov_model import MarkovChainModel
from src.ml_regressor import RegimeMLRegressor
from src.monte_carlo import MonteCarloSimulator
from src.visualizations import (
    create_candlestick_regime_chart,
    create_markov_network_diagram,
    create_monte_carlo_fan_chart,
    create_terminal_distribution_chart,
    create_model_comparison_bar,
    generate_matplotlib_report_figure,
    PALETTE
)

# Page configuration
st.set_page_config(
    page_title="RegimeShift AI | Markov-ML Asset Forecaster",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom High-Impact CSS Styling
st.markdown("""
<style>
    /* Global Page Styling */
    .stApp {
        background-color: #0B0E14;
        color: #E6EDF3;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }
    
    /* Metric Card Styling */
    div[data-testid="stMetric"] {
        background: linear-gradient(135deg, #161B22 0%, #1F242C 100%);
        border: 1px solid #30363D;
        border-radius: 12px;
        padding: 14px 18px;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.4);
    }
    div[data-testid="stMetric"]:hover {
        border-color: #00E5FF;
        transform: translateY(-2px);
        transition: all 0.2s ease-in-out;
    }
    div[data-testid="stMetricLabel"] {
        color: #8B949E !important;
        font-size: 0.85rem !important;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    div[data-testid="stMetricValue"] {
        color: #FFFFFF !important;
        font-size: 1.8rem !important;
        font-weight: 700;
    }
    
    /* Header Gradient Banner */
    .hero-banner {
        background: linear-gradient(90deg, rgba(0, 229, 255, 0.12) 0%, rgba(179, 136, 255, 0.15) 100%);
        border: 1px solid rgba(0, 229, 255, 0.3);
        border-radius: 14px;
        padding: 22px 28px;
        margin-bottom: 24px;
    }
    .hero-title {
        font-size: 2.2rem;
        font-weight: 800;
        background: linear-gradient(120deg, #00E5FF, #B388FF, #00E676);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 6px;
    }
    .hero-sub {
        color: #8B949E;
        font-size: 1.05rem;
        margin: 0;
    }
    
    /* Custom Badge */
    .regime-badge {
        display: inline-block;
        padding: 6px 14px;
        border-radius: 20px;
        font-weight: 700;
        font-size: 0.9rem;
        letter-spacing: 0.5px;
    }
</style>
""", unsafe_allow_html=True)

# ----------------- SIDEBAR CONTROLS -----------------
with st.sidebar:
    st.image("https://img.icons8.com/isometric-line/100/line-chart.png", width=64)
    st.title("Control Deck")
    st.caption("Markov Chains & ML Regression")
    
    st.markdown("---")
    st.subheader("1. Asset & Historical Data")
    preset_choice = st.selectbox(
        "Select Market Asset",
        ["SPY (S&P 500)", "NVDA (Nvidia)", "AAPL (Apple)", "TSLA (Tesla)", "BTC-USD (Bitcoin)", "Custom Ticker", "Synthetic Demo (Offline)"]
    )
    
    if preset_choice == "Custom Ticker":
        ticker = st.text_input("Enter Yahoo Finance Ticker", value="MSFT").upper()
    elif preset_choice == "Synthetic Demo (Offline)":
        ticker = "SYNTH_SPY"
    else:
        ticker = preset_choice.split(" ")[0]
        
    period = st.selectbox("Historical Lookback", ["1y", "2y", "3y", "5y"], index=1)
    
    st.markdown("---")
    st.subheader("2. Markov & ML Setup")
    detector_method = st.selectbox("Regime Classifier", ["gmm", "quantile"], format_func=lambda x: "Gaussian Mixture Model (GMM)" if x == "gmm" else "Quantile Rule")
    regressor_type = st.selectbox("ML Regressor", ["ridge", "polynomial", "random_forest"], format_func=lambda x: {"ridge": "Ridge Regression (L2)", "polynomial": "Polynomial Features (deg=2)", "random_forest": "Random Forest Ensemble"}[x])
    
    st.markdown("---")
    st.subheader("3. Monte Carlo Sandbox")
    forecast_days = st.slider("Forecast Horizon (Trading Days)", min_value=10, max_value=60, value=30, step=5)
    n_simulations = st.slider("Simulated Stochastic Paths", min_value=50, max_value=300, value=150, step=25)
    vol_multiplier = st.slider("Volatility Stress Multiplier", min_value=0.5, max_value=2.5, value=1.0, step=0.1)
    
    shock_mode = st.selectbox(
        "Simulate Shock (Stress Test)",
        ["None (Natural Markov Flow)", "Black Swan: Sudden Bear Crash", "Surge: Sudden Bull Explosion"]
    )
    forced_shock = -1
    if "Bear Crash" in shock_mode:
        forced_shock = 2
    elif "Bull Explosion" in shock_mode:
        forced_shock = 0

# ----------------- DATA PIPELINE -----------------
@st.cache_data(show_spinner=False, ttl=3600)
def load_and_process_pipeline(ticker_sym: str, period_str: str, method: str, reg_type: str):
    if ticker_sym == "SYNTH_SPY":
        raw_df = generate_synthetic_market_data()
        is_live = False
    else:
        raw_df, is_live = fetch_market_data(ticker=ticker_sym, period=period_str, fallback_if_offline=True)
        
    detector = RegimeDetector(n_regimes=3, method=method)
    classified_df = detector.fit_predict(raw_df)
    regime_stats = detector.get_regime_statistics(classified_df)
    
    markov = MarkovChainModel(n_states=3, state_names=STATE_LABELS)
    markov.fit(classified_df["Regime"])
    
    ml = RegimeMLRegressor(model_type=reg_type)
    ml.fit(classified_df)
    ml_eval = ml.evaluate(classified_df)
    
    return {
        "raw_df": raw_df,
        "is_live": is_live,
        "classified_df": classified_df,
        "regime_stats": regime_stats,
        "markov": markov,
        "ml": ml,
        "ml_eval": ml_eval
    }

with st.spinner("Crunching historical market regimes & training ML models..."):
    pipeline = load_and_process_pipeline(ticker, period, detector_method, regressor_type)

df = pipeline["classified_df"]
markov = pipeline["markov"]
ml = pipeline["ml"]
eval_res = pipeline["ml_eval"]
current_regime = int(df["Regime"].iloc[-1])
current_price = float(df["Close"].iloc[-1])
prev_price = float(df["Close"].iloc[-2])
day_change = ((current_price - prev_price) / prev_price) * 100

# Monte Carlo Execution
mc = MonteCarloSimulator(markov_model=markov, ml_model=ml, n_simulations=n_simulations, forecast_days=forecast_days)
latest_features = df[ml.feature_cols].iloc[-1].values
sim_results = mc.run_simulation(
    latest_price=current_price,
    current_state=current_regime,
    latest_features=latest_features,
    volatility_multiplier=vol_multiplier,
    forced_regime_shock=forced_shock,
    shock_duration=5
)

# ----------------- MAIN UI -----------------
st.markdown(f"""
<div class="hero-banner">
    <div class="hero-title">QUANTREGIME AI</div>
    <div class="hero-sub">
        Discrete Markov Chains & Conditioned Machine Learning Regression
        {' &bull; <span style="color:#00E676;">● Live Data</span>' if pipeline['is_live'] else ' &bull; <span style="color:#FFD600;">● High-Fidelity Synthetic Fallback</span>'}
    </div>
</div>
""", unsafe_allow_html=True)

# Top KPI Row
col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    st.metric(
        label=f"{ticker} Latest Close",
        value=f"${current_price:,.2f}",
        delta=f"{day_change:+.2f}% (1D)"
    )

with col2:
    regime_name = STATE_LABELS[current_regime].split(" ")[0]
    color_map = {0: "#00E676", 1: "#FFD600", 2: "#FF1744"}
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #161B22 0%, #1F242C 100%); border: 1px solid #30363D; border-radius: 12px; padding: 14px 18px; box-shadow: 0 4px 15px rgba(0,0,0,0.4);">
        <div style="color: #8B949E; font-size: 0.85rem; font-weight: 600; text-transform: uppercase;">Active Markov State</div>
        <div style="color: {color_map[current_regime]}; font-size: 1.6rem; font-weight: 800; margin-top: 4px;">
            ● {regime_name}
        </div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    median_terminal = sim_results["median"][-1]
    expected_pct = sim_results["expected_terminal_return"]
    st.metric(
        label=f"{forecast_days}-Day Median Target",
        value=f"${median_terminal:,.2f}",
        delta=f"{expected_pct:+.2f}%"
    )

with col4:
    regime_dir_acc = eval_res["regime_metrics"]["Directional_Accuracy"]
    global_dir_acc = eval_res["global_metrics"]["Directional_Accuracy"]
    edge = regime_dir_acc - global_dir_acc
    st.metric(
        label="Directional Accuracy",
        value=f"{regime_dir_acc:.1f}%",
        delta=f"{edge:+.1f}% vs Naive ML"
    )

with col5:
    var95 = sim_results["var_95"]
    st.metric(
        label="95% Value-at-Risk (VaR)",
        value=f"{var95:.1f}%",
        delta="Maximum Expected Loss",
        delta_color="inverse"
    )

st.write("")

# Main Tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🎯 Stochastic Forecast Fan",
    "🔄 Markov Chain Engine",
    "📊 Regime-Partitioned Price Action",
    "🧠 ML Architecture & Validation",
    "🎓 Faculty Viva Defense Guide"
])

# ----------------- TAB 1: MONTE CARLO STOCHASTIC FAN -----------------
with tab1:
    st.plotly_chart(
        create_monte_carlo_fan_chart(df.index, df["Close"], sim_results, ticker=ticker),
        use_container_width=True
    )
    
    col_a, col_b = st.columns([1.2, 0.8])
    with col_a:
        st.plotly_chart(create_terminal_distribution_chart(sim_results), use_container_width=True)
    with col_b:
        st.markdown(f"""
        <div style="background: #161B22; border: 1px solid #30363D; border-radius: 12px; padding: 20px; height: 380px;">
            <h4 style="color: #00E5FF; margin-top: 0;">🎲 Monte Carlo Risk Breakdown</h4>
            <p style="color: #8B949E; font-size: 0.95rem;">
                Based on <b>{n_simulations} simulated stochastic trajectories</b> across <b>{forecast_days} forward trading days</b>, integrating Markov state switching with ML regression residuals.
            </p>
            <hr style="border-color: #30363D;">
            <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
                <span style="color: #E6EDF3;">Probability of Positive Return:</span>
                <span style="color: #00E676; font-weight: bold;">{sim_results['prob_positive']:.1f}%</span>
            </div>
            <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
                <span style="color: #E6EDF3;">Best-Case 90th Percentile:</span>
                <span style="color: #00E5FF; font-weight: bold;">${sim_results['p90'][-1]:.2f}</span>
            </div>
            <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
                <span style="color: #E6EDF3;">Worst-Case 10th Percentile:</span>
                <span style="color: #FF1744; font-weight: bold;">${sim_results['p10'][-1]:.2f}</span>
            </div>
            <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
                <span style="color: #E6EDF3;">Simulated Volatility Multiplier:</span>
                <span style="color: #FFD600; font-weight: bold;">{vol_multiplier}x</span>
            </div>
            <div style="margin-top: 15px; background: rgba(0, 229, 255, 0.08); padding: 10px; border-radius: 8px; font-size: 0.85rem; color: #8B949E;">
                💡 <i>Tip for Demo:</i> Use the sidebar <b>"Simulate Shock"</b> slider to trigger a Black Swan crash in real-time.
            </div>
        </div>
        """, unsafe_allow_html=True)

# ----------------- TAB 2: MARKOV CHAIN ENGINE -----------------
with tab2:
    col_m1, col_m2 = st.columns([1.1, 0.9])
    with col_m1:
        st.plotly_chart(
            create_markov_network_diagram(markov.transition_matrix, markov.stationary_distribution),
            use_container_width=True
        )
    with col_m2:
        st.markdown("#### 📐 Empirical Transition Matrix $P$")
        st.caption(r"Rows sum to 1.0; each cell $P_{ij} = P(S_{t+1}=j \mid S_t=i)$")
        st.dataframe(markov.get_transition_dataframe().style.format("{:.3f}").background_gradient(cmap="Blues", axis=1), use_container_width=True)
        
        st.markdown("#### ⚖️ DTMC Ergodic & Equilibrium Properties")
        st.dataframe(markov.get_theoretical_summary(), use_container_width=True)

    with st.expander("📚 Faculty Explainer: Mathematical Formulation of Discrete Markov Chains"):
        st.markdown(r"""
        ### 1. The Markov Property
        A stochastic process $\{X_t, t \ge 0\}$ satisfies the First-Order Markov Property if the conditional probability distribution of future states depends solely upon the present state:
        $$P(X_{t+1} = s_{t+1} \mid X_t = s_t, X_{t-1} = s_{t-1}, \dots, X_0 = s_0) = P(X_{t+1} = s_{t+1} \mid X_t = s_t)$$
        
        ### 2. Maximum Likelihood Estimation of $P_{ij}$
        The transition probabilities are calculated via empirical frequencies:
        $$p_{ij} = \frac{N_{ij}}{\sum_{k=1}^m N_{ik}}$$
        where $N_{ij}$ is the observed count of transitions from state $i$ to state $j$.
        
        ### 3. Stationary Distribution ($\pi$)
        The long-run equilibrium vector $\boldsymbol{\pi} = [\pi_0, \pi_1, \pi_2]$ satisfies:
        $$\boldsymbol{\pi} P = \boldsymbol{\pi} \quad \text{subject to} \quad \sum_{i=1}^3 \pi_i = 1$$
        
        ### 4. Expected Sojourn (Holding) Time
        The expected number of consecutive days the market lingers in state $i$ before switching:
        $$\mathbb{E}[T_i] = \sum_{k=1}^\infty k \cdot p_{ii}^{k-1}(1 - p_{ii}) = \frac{1}{1 - p_{ii}}$$
        """)

# ----------------- TAB 3: REGIME-PARTITIONED PRICE ACTION -----------------
with tab3:
    st.plotly_chart(
        create_candlestick_regime_chart(df, ticker=ticker),
        use_container_width=True
    )
    
    st.markdown("#### 📋 Historical Regime Performance Breakdown")
    st.dataframe(pipeline["regime_stats"], use_container_width=True)

# ----------------- TAB 4: ML ARCHITECTURE & VALIDATION -----------------
with tab4:
    col_v1, col_v2 = st.columns([1, 1])
    with col_v1:
        st.markdown("#### ⚔️ Model Performance Benchmark")
        st.dataframe(eval_res["comparison_df"], use_container_width=True)
        
        st.markdown(r"""
        **Why Markov-Conditioned ML outperforms Naive ML:**
        1. **Regime Heterogeneity:** Market returns exhibit structural breaks. A single global linear/polynomial model assumes constant slope coefficients $\boldsymbol{\beta}$, resulting in severe bias during market downturns.
        2. **Piecewise Stationarity:** Financial time-series are non-stationary overall, but approximately stationary *within* each Markov sentiment regime.
        3. **Conditioned Residuals:** Sampling stochastic shocks from the active regime's empirical residual variance ($\sigma^2_{S_t}$) preserves realistic fat-tailed skewness in Monte Carlo trajectories.
        """)
        
    with col_v2:
        st.plotly_chart(create_model_comparison_bar(eval_res["comparison_df"]), use_container_width=True)

# ----------------- TAB 5: FACULTY VIVA DEFENSE GUIDE -----------------
with tab5:
    st.markdown("""
    ### 🎓 Complete Viva Voce Defense Guide
    *Keep this tab handy during your project presentation or oral examination!*
    """)
    
    q1, q2 = st.columns(2)
    with q1:
        with st.container(border=True):
            st.markdown("##### Q1: Why not just use LSTM or Deep Learning?")
            st.markdown(r"""
            **Strong Answer:**  
            LSTMs are notoriously prone to overfitting on financial time series due to the low signal-to-noise ratio. They behave as 'black boxes' and cannot quantify discrete market regime shifts.  
            Our **Markov-ML hybrid model** delivers:
            - **Formal Mathematical Interpretability** (Transition Matrix $P$, stationary distributions $\pi$).
            - **No Overfitting** on small regimes with explicit regularized ML.
            - **Direct probabilistic stress-testing** (simulating crashes by forcing regime transitions).
            """)
            
        with st.container(border=True):
            st.markdown("##### Q2: How do you address Non-Stationarity in Asset Prices?")
            st.markdown(r"""
            **Strong Answer:**  
            Raw asset prices $P_t$ are non-stationary (unit root / $I(1)$ process). We transform prices into log-differenced returns $r_t = \ln(P_t/P_{t-1})$ which are covariance-stationary ($I(0)$).  
            Furthermore, the **Markov Chain explicitly captures structural regime shifts** (volatility clustering), solving the classic regime-switching breakdown of classical econometric models.
            """)
            
    with q2:
        with st.container(border=True):
            st.markdown("##### Q3: How are the Markov states defined and trained?")
            st.markdown(r"""
            **Strong Answer:**  
            We use **Gaussian Mixture Models (GMM)**, an unsupervised Expectation-Maximization (EM) algorithm, over multi-dimensional feature space (Daily Returns, 20-Day Realized Volatility, and Trend Spread).  
            The clusters are sorted deterministically into:
            1. **Bull Regime:** High drift, low annualized volatility.
            2. **Neutral Regime:** Near-zero drift, moderate consolidation.
            3. **Bear Regime:** Negative drift, elevated volatility spikes.
            """)
            
        with st.container(border=True):
            st.markdown("##### Q4: How does the Monte Carlo engine link with ML?")
            st.markdown(r"""
            **Strong Answer:**  
            At each forward time-step $t+1$:
            1. The Markov transition row $P(S_{t+1} \mid S_t)$ determines the next market state.
            2. The ML model trained specifically on that regime predicts the drift $\mathbb{E}[r_{t+1}]$.
            3. A stochastic shock is sampled from that regime's empirical residual distribution $\epsilon \sim \text{Resid}(S_{t+1})$.  
            This preserves volatility clustering and asymmetric downside tails without assuming a naive Gaussian distribution!
            """)

    st.markdown("---")
    st.markdown("#### 📄 Publication-Grade Academic Figure (Matplotlib 300-DPI)")
    st.caption("Generate and export a publication-quality 4-panel figure designed specifically for academic semester project reports, PowerPoint presentations, and LaTeX thesis submissions.")
    
    with st.expander("👁️ View & Export Matplotlib Academic Figure", expanded=False):
        with st.spinner("Rendering 300-DPI academic report figure..."):
            mpl_fig = generate_matplotlib_report_figure(
                df=df,
                transition_matrix=markov.transition_matrix,
                stationary_dist=markov.stationary_distribution,
                sim_results=sim_results,
                ticker=ticker
            )
            st.pyplot(mpl_fig)
            
            buf = io.BytesIO()
            mpl_fig.savefig(buf, format="png", dpi=300, bbox_inches="tight")
            st.download_button(
                label=f"📥 Download High-Res {ticker} Figure (300 DPI PNG)",
                data=buf.getvalue(),
                file_name=f"{ticker}_markov_ml_report_figure.png",
                mime="image/png"
            )
