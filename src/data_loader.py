import numpy as np
import pandas as pd
from typing import Tuple, Optional
import datetime

def generate_synthetic_market_data(
    ticker: str = "SYNTH_SPY",
    n_days: int = 750,
    start_price: float = 150.0
) -> pd.DataFrame:
    """
    Generates realistic multi-regime financial price series using
    Geometric Brownian Motion with regime shifts.
    Guarantees the dashboard works seamlessly offline or without API access.
    """
    np.random.seed(42)
    # Roll weekends back to the last business day: pd.date_range(end=<Sat/Sun>, freq="B")
    # can return n_days - 1 dates on recent pandas, which breaks the DataFrame build.
    end_date = pd.offsets.BDay().rollback(pd.Timestamp(datetime.date.today()))
    dates = pd.date_range(end=end_date, periods=n_days, freq="B")
    
    # 3 regimes: 0: Bull (high drift, low vol), 1: Neutral (low drift, med vol), 2: Bear (neg drift, high vol)
    regime_params = [
        {"mu": 0.0010, "sigma": 0.009},  # Bull
        {"mu": 0.0002, "sigma": 0.013},  # Neutral
        {"mu": -0.0012, "sigma": 0.024}  # Bear
    ]
    # Synthetic regime transition matrix
    trans_matrix = np.array([
        [0.88, 0.09, 0.03],
        [0.10, 0.80, 0.10],
        [0.05, 0.15, 0.80]
    ])
    
    regimes = [0]
    for _ in range(1, n_days):
        current_state = regimes[-1]
        next_state = np.random.choice([0, 1, 2], p=trans_matrix[current_state])
        regimes.append(next_state)
        
    prices = [start_price]
    highs, lows, opens, volumes = [], [], [], []
    
    for i in range(n_days):
        state = regimes[i]
        mu = regime_params[state]["mu"]
        sigma = regime_params[state]["sigma"]
        ret = np.random.normal(mu, sigma)
        
        p_close = prices[-1] * np.exp(ret)
        prices.append(p_close)
        
        # Approximate OHLCV
        intra_spread = abs(np.random.normal(0, sigma * 0.7))
        p_open = prices[-2] if i > 0 else start_price
        p_high = max(p_open, p_close) * (1 + intra_spread)
        p_low = min(p_open, p_close) * (1 - intra_spread)
        volume = int(np.random.lognormal(16.5, 0.4) * (1.5 if state == 2 else 1.0))
        
        opens.append(p_open)
        highs.append(p_high)
        lows.append(p_low)
        volumes.append(volume)
        
    df = pd.DataFrame({
        "Date": dates,
        "Open": opens,
        "High": highs,
        "Low": lows,
        "Close": prices[1:],
        "Volume": volumes
    }).set_index("Date")
    
    df["Adj Close"] = df["Close"]
    return df

def fetch_market_data(
    ticker: str = "AAPL",
    period: str = "2y",
    fallback_if_offline: bool = True
) -> Tuple[pd.DataFrame, bool]:
    """
    Fetches real-time market data from Yahoo Finance.
    Falls back cleanly to synthetic data if internet is unavailable.
    Returns: (df, is_real_data)
    """
    try:
        import yfinance as yf
        data = yf.download(ticker, period=period, progress=False)
        if data is not None and len(data) >= 60:
            if isinstance(data.columns, pd.MultiIndex):
                data.columns = [col[0] for col in data.columns]
            data = data.dropna()
            # Standardize column names
            data = data[["Open", "High", "Low", "Close", "Volume"]]
            data["Adj Close"] = data["Close"]
            return data, True
    except Exception as e:
        pass
        
    if fallback_if_offline:
        return generate_synthetic_market_data(ticker=ticker), False
    raise RuntimeError(f"Could not retrieve market data for {ticker}")
