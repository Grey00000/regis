# 📈 QuantRegime AI: Markov Chain & Machine Learning Asset Forecaster

> **End-of-Semester Applied Data Science & Financial Engineering Project**  
> *A hybrid predictive architecture combining First-Order Discrete Markov Chains (DTMC), Regime-Conditioned ML Regressors, and Stochastic Monte Carlo Simulations.*

---

## 🌟 Executive Summary

Traditional financial machine learning models make a fatal assumption: **stationarity**. They train a single global regressor across historical data, ignoring the fact that asset dynamics change drastically when a market shifts from an exuberant **Bull** market to a stagnant **Consolidation** or a volatile **Bear** crash.

**QuantRegime AI** solves this by decomposing non-stationary market time series into discrete latent states:
1. **Unsupervised Regime Detection:** Gaussian Mixture Models (GMM) cluster historical market states based on returns, 20-day annualized realized volatility, and trend spreads.
2. **First-Order Markov Transition Engine:** Computes empirical transition matrices ($P$), long-run ergodic equilibrium distributions ($\boldsymbol{\pi}$), and expected regime holding times ($\mathbb{E}[T]$).
3. **Regime-Conditioned ML Regression:** Fits specialized predictive models (Ridge, Polynomial, or Random Forest) for each distinct market state, drastically improving directional sign accuracy.
4. **Stochastic Monte Carlo Prediction Cone:** Simulates 150+ forward price trajectories by chaining Markov transition probabilities with regime-specific empirical residual shocks.

---

## 📐 Mathematical Formulation

### 1. Discrete-Time Markov Chain (DTMC)
A stochastic process $\{X_t, t \ge 0\}$ defined on the state space $S = \{0: \text{Bull}, 1: \text{Neutral}, 2: \text{Bear}\}$ obeys the **Markov Property**:
$$P(X_{t+1} = j \mid X_t = i, X_{t-1} = i_{t-1}, \dots, X_0 = i_0) = P(X_{t+1} = j \mid X_t = i) = p_{ij}$$

The **Empirical Transition Matrix** $\mathbf{P} \in \mathbb{R}^{3 \times 3}$ is estimated via Maximum Likelihood:
$$p_{ij} = \frac{N_{ij}}{\sum_{k=0}^{2} N_{ik}}, \quad \text{where } \sum_{j=0}^{2} p_{ij} = 1$$

### 2. Stationary Distribution ($\boldsymbol{\pi}$)
The ergodic equilibrium distribution $\boldsymbol{\pi} = [\pi_0, \pi_1, \pi_2]$ represents the long-term percentage of trading days spent in each regime:
$$\boldsymbol{\pi} \mathbf{P} = \boldsymbol{\pi} \quad \text{subject to} \quad \sum_{i=0}^2 \pi_i = 1$$

### 3. Expected Holding Time (Sojourn Time)
The expected duration (in trading days) before the market exits state $i$:
$$\mathbb{E}[T_i] = \frac{1}{1 - p_{ii}}$$

### 4. Regime-Conditioned ML Regression
Instead of optimizing a global objective:
$$\min_{\boldsymbol{\beta}} \sum_{t=1}^T \left( y_t - \mathbf{x}_t^T \boldsymbol{\beta} \right)^2 + \alpha \|\boldsymbol{\beta}\|_2^2$$

We condition parameter vectors on the active Markov state $S_t \in \{0, 1, 2\}$:
$$y_t = \mathbf{x}_t^T \boldsymbol{\beta}_{S_t} + \epsilon_{S_t}, \quad \text{where } \epsilon_{S_t} \sim \mathcal{D}(0, \sigma^2_{S_t})$$

### 5. Monte Carlo Stochastic Simulation
For each forward day $t \in [1, \tau]$:
1. State transition: $S_{t+1} \sim \text{Categorical}(\mathbf{P}_{S_t, :})$
2. ML Expected Drift: $\hat{r}_{t+1} = f_{S_{t+1}}(\mathbf{x}_t)$
3. Residual Shock: $\epsilon \sim \text{Empirical}(\text{Residuals}_{S_{t+1}})$
4. Price Evolution: $P_{t+1} = P_t \cdot \exp(\hat{r}_{t+1} + \epsilon \cdot \lambda_{\text{vol}})$

---

## 🚀 Key Dashboard Features

- **🎯 Interactive Monte Carlo Cone:** 150 glowing stochastic paths with $50\%$ interquartile and $80\%$ probability bands, median forecast, and 95% Value-at-Risk (VaR).
- **🔄 Interactive Markov State Graph:** Plotly-rendered state transition network with curved edges, self-loop probabilities, and node sizes proportional to stationary equilibrium $\pi$.
- **📊 Dynamic Candlestick & Regime Timeline:** Interactive candlestick chart with semi-transparent regime color bands (Green = Bull, Amber = Neutral, Red = Bear).
- **🧠 ML Benchmark vs. Global Baseline:** Side-by-side metric comparison ($R^2$, RMSE, MAE, and Directional Accuracy %).
- **⚡ Black Swan Stress Testing:** Interactive sidebar slider allows forcing sudden market crashes or bull runs to observe forward probability cone divergence in real time.
- **📄 High-Res Academic Figure Export (Matplotlib):** 4-panel, publication-quality 300-DPI figure export designed specifically for inclusion in semester project reports, PowerPoint presentations, and LaTeX thesis documents.
- **🛡️ Seamless Offline Fallback:** Includes built-in high-fidelity synthetic market generation using Geometric Brownian Motion with regime shifts. Zero risk of failed API calls during viva presentations.

---

## 🛠️ Quickstart & Installation

### Requirements
- Python 3.10+
- Linux / macOS / Windows

### One-Click Launch (Linux/macOS)
```bash
git clone <repo-url>
cd markov_regime_forecaster
chmod +x run.sh
./run.sh
```

### Manual Setup
```bash
# 1. Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Launch dashboard
streamlit run app.py
```

The application will be accessible at `http://localhost:8501`.

---

## 📁 Repository Structure

```text
markov_regime_forecaster/
├── app.py                  # Main Streamlit interactive dashboard
├── requirements.txt        # Project dependencies
├── run.sh                  # One-click startup script
├── test_pipeline.py        # Headless automated verification script
├── README.md               # Presentation & academic documentation
└── src/
    ├── __init__.py
    ├── data_loader.py      # Yahoo Finance fetcher & synthetic GBM fallback
    ├── regime_detector.py  # Gaussian Mixture Model (GMM) & Quantile classification
    ├── markov_model.py     # DTMC transition matrix, stationary dist, holding times
    ├── ml_regressor.py     # Ridge, Polynomial & Random Forest regime models
    ├── monte_carlo.py      # Multi-path stochastic simulation engine
    └── visualizations.py   # Plotly charts (Network diagram, Candlestick, Cone)
```

---

## 🎓 FAQ

| Question | Evaluation Focus | Model Answer |
| :--- | :--- | :--- |
| **Q1: Why not just use Deep Learning (LSTM / GRU)?** | Model Selection & Overfitting | *LSTMs act as black boxes and easily overfit financial returns due to low signal-to-noise ratios. Markov-ML models offer closed-form interpretability, explicit transition matrices, and fast convergence without massive GPU training.* |
| **Q2: How is non-stationarity handled?** | Econometric Rigor | *Prices $P_t$ are non-stationary ($I(1)$). We log-difference them into returns $r_t = \ln(P_t/P_{t-1})$ ($I(0)$). Furthermore, Markov chains capture structural breaks in volatility, making the series piecewise stationary.* |
| **Q3: What does the Stationary Distribution represent?** | Markov Theory | *The eigenvector $\boldsymbol{\pi}$ corresponding to eigenvalue $\lambda=1$ of $\mathbf{P}^T$. It proves the long-run percentage of time the market will spend in Bull, Neutral, and Bear states regardless of initial conditions.* |
| **Q4: How do Markov states improve Regression?** | Machine Learning Innovation | *Financial feature-return relationships invert during crashes (e.g., momentum breaks). Training conditioned sub-models avoids diluting signals and substantially improves directional sign accuracy.* |

---

## 👥 Contributors & Academic Credits
- **Project Title:** RegimeShift AI (Markov Chains & ML Regression)
- **Domain:** Computational Finance, Stochastic Modeling & Machine Learning
