import numpy as np
import pandas as pd
from sklearn.mixture import GaussianMixture
from sklearn.preprocessing import StandardScaler
from typing import Tuple, Dict

STATE_LABELS = {
    0: "Bull (Expansion)",
    1: "Neutral (Consolidation)",
    2: "Bear (Correction/High Vol)"
}

STATE_COLORS = {
    0: "#00E676",  # Bright Green
    1: "#FFD600",  # Amber/Yellow
    2: "#FF1744"   # Crimson Red
}

class RegimeDetector:
    """
    Detects financial market regimes (Bull, Neutral, Bear) using
    unsupervised statistical clustering (Gaussian Mixture Model / K-Means)
    or statistical quantile thresholds.
    """
    def __init__(self, n_regimes: int = 3, method: str = "gmm"):
        self.n_regimes = n_regimes
        self.method = method
        self.scaler = StandardScaler()
        self.model = None
        self.cluster_mapping = {}  # Maps raw cluster id to sorted regime [0=Bull, 1=Neutral, 2=Bear]
        
    def compute_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Enriches price data with statistical regime features:
        - Log Returns
        - 20-day Rolling Volatility (Annualized)
        - Moving Average Spread (SMA20 / SMA50 - 1)
        - RSI (Relative Strength Index)
        """
        data = df.copy()
        data["Log_Return"] = np.log(data["Close"] / data["Close"].shift(1))
        data["Rolling_Vol_20"] = data["Log_Return"].rolling(window=20).std() * np.sqrt(252)
        
        sma20 = data["Close"].rolling(window=20).mean()
        sma50 = data["Close"].rolling(window=50).mean()
        data["Trend_Spread"] = (sma20 / sma50) - 1.0
        
        # Simple RSI calculation
        delta = data["Close"].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / (loss + 1e-9)
        data["RSI"] = 100 - (100 / (1 + rs))
        
        # Momentum
        data["Mom_10"] = data["Close"].pct_change(10)
        
        data = data.dropna().copy()
        return data

    def fit_predict(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Fits unsupervised GMM on returns and volatility to discover market regimes.
        Clusters are sorted such that:
        State 0: Highest mean return (Bull)
        State 1: Intermediate / Low-drift return (Neutral)
        State 2: Lowest / Negative mean return with elevated vol (Bear)
        """
        featured_df = self.compute_indicators(df)
        
        feature_cols = ["Log_Return", "Rolling_Vol_20", "Trend_Spread"]
        X = featured_df[feature_cols].values
        X_scaled = self.scaler.fit_transform(X)
        
        if self.method == "gmm":
            self.model = GaussianMixture(
                n_components=self.n_regimes,
                covariance_type="full",
                random_state=42,
                n_init=5
            )
            raw_labels = self.model.fit_predict(X_scaled)
        else:
            # Fallback quantile rule
            vol_thresh = featured_df["Rolling_Vol_20"].quantile(0.65)
            ret_thresh = featured_df["Log_Return"].quantile(0.45)
            raw_labels = np.where(
                featured_df["Log_Return"] > ret_thresh,
                0,
                np.where(featured_df["Rolling_Vol_20"] > vol_thresh, 2, 1)
            )
            
        # Re-map clusters deterministically by average return:
        # 0 = highest return, 2 = lowest return
        cluster_means = []
        for c in range(self.n_regimes):
            mask = (raw_labels == c)
            mean_ret = featured_df.loc[mask, "Log_Return"].mean() if np.any(mask) else -999.0
            cluster_means.append((c, mean_ret))
            
        cluster_means.sort(key=lambda x: x[1], reverse=True)
        self.cluster_mapping = {original: sorted_idx for sorted_idx, (original, _) in enumerate(cluster_means)}
        
        regime_series = np.array([self.cluster_mapping[c] for c in raw_labels])
        featured_df["Regime"] = regime_series
        featured_df["Regime_Name"] = featured_df["Regime"].map(STATE_LABELS)
        featured_df["Regime_Color"] = featured_df["Regime"].map(STATE_COLORS)
        
        return featured_df

    def get_regime_statistics(self, df: pd.DataFrame) -> pd.DataFrame:
        """Computes summary statistics for each detected regime."""
        stats = []
        for r_id in range(self.n_regimes):
            sub = df[df["Regime"] == r_id]
            if len(sub) == 0:
                continue
            ann_ret = (np.exp(sub["Log_Return"].mean() * 252) - 1) * 100
            ann_vol = sub["Log_Return"].std() * np.sqrt(252) * 100
            sharpe = (ann_ret - 3.0) / (ann_vol + 1e-6)  # assuming 3% risk-free rate
            stats.append({
                "Regime ID": r_id,
                "Regime Name": STATE_LABELS[r_id],
                "Count (Days)": len(sub),
                "Share (%)": f"{(len(sub) / len(df)) * 100:.1f}%",
                "Ann. Return (%)": f"{ann_ret:+.2f}%",
                "Ann. Volatility (%)": f"{ann_vol:.2f}%",
                "Sharpe Ratio": f"{sharpe:.2f}"
            })
        return pd.DataFrame(stats)
