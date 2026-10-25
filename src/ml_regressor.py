import numpy as np
import pandas as pd
from typing import Dict, Tuple, Any
from sklearn.linear_model import Ridge
from sklearn.preprocessing import PolynomialFeatures, StandardScaler
from sklearn.ensemble import RandomForestRegressor
from sklearn.pipeline import Pipeline
from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error

class RegimeMLRegressor:
    """
    Regime-Conditioned Machine Learning Regressors.
    Trains specialized sub-models for Bull, Neutral, and Bear market regimes,
    benchmarked against a Global naive regressor.
    """
    def __init__(self, model_type: str = "ridge", alpha: float = 1.0):
        self.model_type = model_type
        self.alpha = alpha
        self.feature_cols = [
            "Log_Return", "Rolling_Vol_20", "Trend_Spread", "RSI", "Mom_10"
        ]
        self.regime_models: Dict[int, Any] = {}
        self.global_model: Any = None
        self.residuals_by_regime: Dict[int, np.ndarray] = {}
        
    def _create_base_pipeline(self) -> Pipeline:
        if self.model_type == "ridge":
            return Pipeline([
                ("scaler", StandardScaler()),
                ("regressor", Ridge(alpha=self.alpha))
            ])
        elif self.model_type == "polynomial":
            return Pipeline([
                ("scaler", StandardScaler()),
                ("poly", PolynomialFeatures(degree=2, include_bias=False)),
                ("regressor", Ridge(alpha=self.alpha))
            ])
        elif self.model_type == "random_forest":
            return Pipeline([
                ("scaler", StandardScaler()),
                ("regressor", RandomForestRegressor(n_estimators=75, max_depth=5, random_state=42))
            ])
        else:
            return Pipeline([
                ("scaler", StandardScaler()),
                ("regressor", Ridge(alpha=self.alpha))
            ])

    def prepare_dataset(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series]:
        """
        Creates feature matrix X and target y (next-day log return: r_{t+1}).
        """
        data = df.copy()
        data["Target_Return"] = data["Log_Return"].shift(-1)
        data = data.dropna(subset=self.feature_cols + ["Target_Return", "Regime"]).copy()
        return data

    def fit(self, df: pd.DataFrame):
        """
        Fits both the Global model and Regime-Specific models.
        """
        data = self.prepare_dataset(df)
        X_all = data[self.feature_cols]
        y_all = data["Target_Return"]
        
        # Fit Global Baseline
        self.global_model = self._create_base_pipeline()
        self.global_model.fit(X_all, y_all)
        
        # Fit Regime-Specific Models
        unique_regimes = data["Regime"].unique()
        for r in unique_regimes:
            mask = (data["Regime"] == r)
            X_r = data.loc[mask, self.feature_cols]
            y_r = data.loc[mask, "Target_Return"]
            
            if len(X_r) > 10:
                model_r = self._create_base_pipeline()
                model_r.fit(X_r, y_r)
                self.regime_models[r] = model_r
                
                # Compute empirical residual distribution for Monte Carlo sampling
                preds_r = model_r.predict(X_r)
                residuals = y_r.values - preds_r
                self.residuals_by_regime[r] = residuals
            else:
                self.regime_models[r] = self.global_model
                self.residuals_by_regime[r] = np.zeros(10)

        return self

    def predict_next(self, current_features: np.ndarray, regime: int) -> float:
        """Predicts expected return given features and active Markov regime."""
        features_2d = pd.DataFrame([current_features], columns=self.feature_cols)
        if regime in self.regime_models:
            return float(self.regime_models[regime].predict(features_2d)[0])
        return float(self.global_model.predict(features_2d)[0])

    def evaluate(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Evaluates Global Model vs Regime-Conditioned Model performance.
        Metrics: R2, RMSE, Directional Accuracy (Sign Accuracy).
        """
        data = self.prepare_dataset(df)
        X = data[self.feature_cols]
        y_true = data["Target_Return"].values
        
        # Global predictions
        y_pred_global = self.global_model.predict(X)
        
        # Regime-conditioned predictions
        y_pred_regime = np.zeros_like(y_true)
        for r, model in self.regime_models.items():
            mask = (data["Regime"] == r).values
            if np.any(mask):
                y_pred_regime[mask] = model.predict(X[mask])
                
        def calc_metrics(y_t, y_p):
            r2 = r2_score(y_t, y_p)
            rmse = np.sqrt(mean_squared_error(y_t, y_p))
            mae = mean_absolute_error(y_t, y_p)
            # Directional accuracy: sign match
            dir_acc = np.mean(np.sign(y_t) == np.sign(y_p)) * 100.0
            return {
                "R2": r2,
                "RMSE": rmse,
                "MAE": mae,
                "Directional_Accuracy": dir_acc
            }

        global_metrics = calc_metrics(y_true, y_pred_global)
        regime_metrics = calc_metrics(y_true, y_pred_regime)
        
        comparison_df = pd.DataFrame([
            {
                "Model Architecture": "Global Baseline (Naive ML)",
                "R² Score": f"{global_metrics['R2']:.4f}",
                "RMSE": f"{global_metrics['RMSE']:.5f}",
                "MAE": f"{global_metrics['MAE']:.5f}",
                "Directional Accuracy": f"{global_metrics['Directional_Accuracy']:.1f}%"
            },
            {
                "Model Architecture": "Markov Regime-Conditioned ML",
                "R² Score": f"{regime_metrics['R2']:.4f}",
                "RMSE": f"{regime_metrics['RMSE']:.5f}",
                "MAE": f"{regime_metrics['MAE']:.5f}",
                "Directional Accuracy": f"{regime_metrics['Directional_Accuracy']:.1f}%"
            }
        ])
        
        return {
            "comparison_df": comparison_df,
            "global_metrics": global_metrics,
            "regime_metrics": regime_metrics,
            "y_true": y_true,
            "y_pred_regime": y_pred_regime,
            "y_pred_global": y_pred_global
        }
