import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from typing import Dict, Any, List

# Aesthetic Dark Fintech Theme Palette
PALETTE = {
    "bg": "#0E1117",
    "card_bg": "#161B22",
    "text": "#E6EDF3",
    "text_muted": "#8B949E",
    "bull": "#00E676",      # Bright neon green
    "neutral": "#FFD600",   # Electric amber
    "bear": "#FF1744",      # High-vis red
    "accent_cyan": "#00E5FF",
    "accent_purple": "#B388FF",
    "grid": "#21262D"
}

def create_candlestick_regime_chart(df: pd.DataFrame, ticker: str = "ASSET") -> go.Figure:
    """
    Creates an interactive financial chart showing price action
    color-coded by the detected Markov regime.
    """
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.04,
        row_heights=[0.75, 0.25],
        subplot_titles=[f"<b>{ticker}</b> Price Action & Detected Markov Regimes", "Trading Volume & Regime Intensity"]
    )

    # 1. Price Candlesticks / Close line
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df["Open"],
            high=df["High"],
            low=df["Low"],
            close=df["Close"],
            name="OHLC Price",
            increasing_line_color="#26A69A",
            decreasing_line_color="#EF5350"
        ),
        row=1, col=1
    )

    # Add 20-day and 50-day SMA if present
    if "Rolling_Vol_20" in df.columns:
        sma20 = df["Close"].rolling(20).mean()
        fig.add_trace(
            go.Scatter(
                x=df.index, y=sma20,
                name="20 SMA",
                line=dict(color="#29B6F6", width=1.5, dash="dot")
            ),
            row=1, col=1
        )

    # 2. Volume Bar Chart
    colors = [
        PALETTE["bull"] if r == 0 else (PALETTE["neutral"] if r == 1 else PALETTE["bear"])
        for r in df["Regime"]
    ]
    fig.add_trace(
        go.Bar(
            x=df.index,
            y=df["Volume"],
            marker_color=colors,
            opacity=0.7,
            name="Regime Volume"
        ),
        row=2, col=1
    )

    # 3. Add background color spans for regimes (consecutive blocks)
    regimes = df["Regime"].values
    dates = df.index
    n = len(df)
    
    start_idx = 0
    while start_idx < n:
        curr_r = regimes[start_idx]
        end_idx = start_idx
        while end_idx + 1 < n and regimes[end_idx + 1] == curr_r:
            end_idx += 1
            
        color = "rgba(0, 230, 118, 0.12)" if curr_r == 0 else (
            "rgba(255, 214, 0, 0.10)" if curr_r == 1 else "rgba(255, 23, 68, 0.15)"
        )
        fig.add_vrect(
            x0=dates[start_idx],
            x1=dates[end_idx],
            fillcolor=color,
            layer="below",
            line_width=0,
            row=1, col=1
        )
        start_idx = end_idx + 1

    fig.update_layout(
        template="plotly_dark",
        plot_bgcolor=PALETTE["bg"],
        paper_bgcolor=PALETTE["bg"],
        xaxis_rangeslider_visible=False,
        height=580,
        margin=dict(l=40, r=40, t=50, b=30),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    fig.update_xaxes(showgrid=True, gridcolor=PALETTE["grid"])
    fig.update_yaxes(showgrid=True, gridcolor=PALETTE["grid"])
    return fig


def create_markov_network_diagram(transition_matrix: np.ndarray, stationary_dist: np.ndarray) -> go.Figure:
    """
    Creates an interactive graphical state transition network diagram
    where nodes represent Bull, Neutral, Bear states and directed arrows
    represent transition probabilities.
    """
    fig = go.Figure()

    # Fixed triangle geometry for the 3 states
    coords = {
        0: (0.20, 0.75),   # Bull (top left)
        1: (0.80, 0.75),   # Neutral (top right)
        2: (0.50, 0.20)    # Bear (bottom center)
    }
    state_names = ["Bull (Expansion)", "Neutral (Consolidation)", "Bear (Correction)"]
    node_colors = [PALETTE["bull"], PALETTE["neutral"], PALETTE["bear"]]

    # 1. Draw Transition Arrows / Edges
    for i in range(3):
        for j in range(3):
            prob = transition_matrix[i, j]
            if prob < 0.02:
                continue

            x0, y0 = coords[i]
            x1, y1 = coords[j]

            if i == j:
                # Self-loop indicator above/below node
                offset_y = 0.11 if y0 > 0.5 else -0.11
                fig.add_annotation(
                    x=x0, y=y0 + offset_y,
                    text=f"<b>P({i}→{i})<br>{prob*100:.1f}%</b>",
                    showarrow=False,
                    font=dict(color=node_colors[i], size=11),
                    bgcolor="rgba(22, 27, 34, 0.8)",
                    bordercolor=node_colors[i],
                    borderwidth=1,
                    borderpad=3
                )
            else:
                # Directed edge with midpoint probability label
                # Slightly curve the midpoints so opposing arrows don't collide
                mx = (x0 + x1) / 2.0
                my = (y0 + y1) / 2.0
                
                # Perpendicular offset for curve
                dx = x1 - x0
                dy = y1 - y0
                curve_strength = 0.08
                cx = mx - dy * curve_strength
                cy = my + dx * curve_strength

                # Curved path
                path_str = f"M {x0},{y0} Q {cx},{cy} {x1},{y1}"
                edge_color = node_colors[i]
                
                fig.add_shape(
                    type="path",
                    path=path_str,
                    line=dict(color=edge_color, width=max(1.5, prob * 6)),
                    opacity=0.65
                )

                # Midpoint arrow label
                fig.add_annotation(
                    x=cx, y=cy,
                    text=f"<b>{prob*100:.1f}%</b>",
                    showarrow=False,
                    font=dict(color=PALETTE["text"], size=10),
                    bgcolor="rgba(22, 27, 34, 0.9)",
                    bordercolor=edge_color,
                    borderwidth=1,
                    borderpad=2
                )

    # 2. Draw State Nodes (sized by stationary distribution)
    node_x = [coords[i][0] for i in range(3)]
    node_y = [coords[i][1] for i in range(3)]
    node_sizes = [max(45, stationary_dist[i] * 120) for i in range(3)]
    hover_texts = [
        f"<b>{state_names[i]}</b><br>Equilibrium Share (π): {stationary_dist[i]*100:.1f}%<br>Self-Persistence: {transition_matrix[i,i]*100:.1f}%"
        for i in range(3)
    ]

    fig.add_trace(
        go.Scatter(
            x=node_x, y=node_y,
            mode="markers+text",
            marker=dict(
                size=node_sizes,
                color=node_colors,
                line=dict(color="#FFFFFF", width=2),
                opacity=0.95
            ),
            text=[f"<b>{state_names[i].split()[0]}</b><br>π={stationary_dist[i]*100:.1f}%" for i in range(3)],
            textposition="middle center",
            textfont=dict(color="#000000", size=11, family="Arial Black"),
            hoverinfo="text",
            hovertext=hover_texts,
            name="Regime Nodes"
        )
    )

    fig.update_layout(
        title="<b>Markov State Transition Graph (Self-Loops & Equilibrium π)</b>",
        template="plotly_dark",
        plot_bgcolor=PALETTE["card_bg"],
        paper_bgcolor=PALETTE["bg"],
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[0.05, 0.95]),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[0.05, 0.95]),
        height=420,
        margin=dict(l=20, r=20, t=50, b=20),
        showlegend=False
    )
    return fig


def create_monte_carlo_fan_chart(
    historical_dates: pd.DatetimeIndex,
    historical_prices: pd.Series,
    sim_results: Dict[str, Any],
    ticker: str = "ASSET"
) -> go.Figure:
    """
    Creates the showstopper 150-path Monte Carlo probability fan chart
    with glowing median trajectory and 50% & 80% confidence bands.
    """
    fig = go.Figure()

    # Lookback history (last 60 trading days)
    hist_sub = historical_prices.iloc[-60:]
    last_date = hist_sub.index[-1]
    
    # Future dates
    forecast_days = sim_results["paths"].shape[1] - 1
    future_dates = pd.date_range(start=last_date, periods=forecast_days + 1, freq="B")

    # 1. Historical actual price line
    fig.add_trace(
        go.Scatter(
            x=hist_sub.index,
            y=hist_sub.values,
            mode="lines",
            name="Historical Actual",
            line=dict(color="#FFFFFF", width=2.5)
        )
    )

    # 2. Individual Simulated Stochastic Paths (translucent neon lines)
    sample_indices = np.random.choice(sim_results["paths"].shape[0], size=min(60, sim_results["paths"].shape[0]), replace=False)
    for idx in sample_indices:
        fig.add_trace(
            go.Scatter(
                x=future_dates,
                y=sim_results["paths"][idx],
                mode="lines",
                line=dict(color="rgba(0, 229, 255, 0.08)", width=1),
                showlegend=False,
                hoverinfo="skip"
            )
        )

    # 3. 80% Confidence Interval Band (10th to 90th percentile)
    fig.add_trace(
        go.Scatter(
            x=future_dates,
            y=sim_results["p90"],
            mode="lines",
            line=dict(width=0),
            showlegend=False,
            hoverinfo="skip"
        )
    )
    fig.add_trace(
        go.Scatter(
            x=future_dates,
            y=sim_results["p10"],
            mode="lines",
            line=dict(width=0),
            fill="tonexty",
            fillcolor="rgba(0, 229, 255, 0.12)",
            name="80% Probability Interval",
            hoverinfo="skip"
        )
    )

    # 4. 50% Confidence Interval Band (25th to 75th percentile)
    fig.add_trace(
        go.Scatter(
            x=future_dates,
            y=sim_results["p75"],
            mode="lines",
            line=dict(width=0),
            showlegend=False,
            hoverinfo="skip"
        )
    )
    fig.add_trace(
        go.Scatter(
            x=future_dates,
            y=sim_results["p25"],
            mode="lines",
            line=dict(width=0),
            fill="tonexty",
            fillcolor="rgba(179, 136, 255, 0.22)",
            name="50% Interquartile Range",
            hoverinfo="skip"
        )
    )

    # 5. Median Trajectory (Glowing gold)
    fig.add_trace(
        go.Scatter(
            x=future_dates,
            y=sim_results["median"],
            mode="lines+markers",
            marker=dict(size=4),
            name="Median Forecast (Markov + ML)",
            line=dict(color="#FFD600", width=3, dash="solid")
        )
    )

    # Vertical split line
    fig.add_vline(
        x=last_date.timestamp() * 1000,
        line_width=1.5,
        line_dash="dash",
        line_color="#8B949E",
        annotation_text="Today (Forecast Start)",
        annotation_position="top left",
        annotation_font=dict(color="#8B949E", size=10)
    )

    fig.update_layout(
        title=f"<b>Monte Carlo Multi-Regime Prediction Cone ({forecast_days} Trading Days Forward)</b>",
        template="plotly_dark",
        plot_bgcolor=PALETTE["bg"],
        paper_bgcolor=PALETTE["bg"],
        height=520,
        margin=dict(l=40, r=40, t=60, b=30),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    fig.update_xaxes(showgrid=True, gridcolor=PALETTE["grid"])
    fig.update_yaxes(showgrid=True, gridcolor=PALETTE["grid"])
    return fig


def create_terminal_distribution_chart(sim_results: Dict[str, Any]) -> go.Figure:
    """Creates a histogram of terminal simulated returns with VaR and median metrics."""
    rets = sim_results["terminal_returns"]
    median_ret = sim_results["expected_terminal_return"]
    var_95 = sim_results["var_95"]

    fig = go.Figure()
    fig.add_trace(
        go.Histogram(
            x=rets,
            nbinsx=35,
            marker_color=PALETTE["accent_cyan"],
            opacity=0.75,
            name="Simulated Return Density"
        )
    )

    # Median line
    fig.add_vline(
        x=median_ret,
        line_color=PALETTE["bull"],
        line_width=2.5,
        line_dash="dash",
        annotation_text=f"Median: {median_ret:+.1f}%",
        annotation_position="top right"
    )

    # 95% VaR line
    fig.add_vline(
        x=var_95,
        line_color=PALETTE["bear"],
        line_width=2.5,
        line_dash="dot",
        annotation_text=f"95% VaR: {var_95:+.1f}%",
        annotation_position="top left"
    )

    fig.update_layout(
        title="<b>Distribution of Terminal Returns Across 150 Stochastic Paths</b>",
        template="plotly_dark",
        plot_bgcolor=PALETTE["card_bg"],
        paper_bgcolor=PALETTE["bg"],
        xaxis_title="Forward Cumulative Return (%)",
        yaxis_title="Path Frequency",
        height=380,
        margin=dict(l=40, r=40, t=50, b=30),
        showlegend=False
    )
    fig.update_xaxes(showgrid=True, gridcolor=PALETTE["grid"])
    fig.update_yaxes(showgrid=True, gridcolor=PALETTE["grid"])
    return fig


def create_model_comparison_bar(comparison_df: pd.DataFrame) -> go.Figure:
    """Creates side-by-side metric comparison bar chart between baseline and Markov-ML."""
    fig = go.Figure()
    
    models = comparison_df["Model Architecture"].tolist()
    r2_vals = [float(x) for x in comparison_df["R² Score"]]
    dir_acc = [float(x.replace("%", "")) for x in comparison_df["Directional Accuracy"]]

    fig.add_trace(
        go.Bar(
            x=models,
            y=dir_acc,
            name="Directional Accuracy (%)",
            marker_color=[PALETTE["accent_purple"], PALETTE["bull"]],
            text=[f"{v:.1f}%" for v in dir_acc],
            textposition="auto"
        )
    )

    fig.update_layout(
        title="<b>Predictive Edge: Baseline ML vs Markov-Conditioned Model</b>",
        template="plotly_dark",
        plot_bgcolor=PALETTE["card_bg"],
        paper_bgcolor=PALETTE["bg"],
        yaxis=dict(title="Directional Sign Accuracy (%)", range=[35, 75]),
        height=380,
        margin=dict(l=40, r=40, t=50, b=30),
        showlegend=False
    )
    return fig


def generate_matplotlib_report_figure(
    df: pd.DataFrame,
    transition_matrix: np.ndarray,
    stationary_dist: np.ndarray,
    sim_results: Dict[str, Any],
    ticker: str = "ASSET"
):
    """
    Generates a publication-grade, 4-panel 300-DPI Matplotlib figure
    ideal for thesis reports, presentation slides, or LaTeX paper exports.
    """
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates

    fig, axes = plt.subplots(2, 2, figsize=(14, 9), dpi=300)
    fig.patch.set_facecolor("#FFFFFF")
    plt.subplots_adjust(hspace=0.32, wspace=0.25)

    # 1. Price Action with Regime Color-Coding
    ax1 = axes[0, 0]
    ax1.plot(df.index, df["Close"], color="#1A237E", linewidth=1.5, label="Close Price")
    if "Rolling_Vol_20" in df.columns:
        sma20 = df["Close"].rolling(20).mean()
        ax1.plot(df.index, sma20, color="#00838F", linestyle="--", linewidth=1.0, label="20 SMA")

    regimes = df["Regime"].values
    dates = df.index
    for i in range(len(df) - 1):
        c = "#C8E6C9" if regimes[i] == 0 else ("#FFF9C4" if regimes[i] == 1 else "#FFCDD2")
        ax1.axvspan(dates[i], dates[i+1], color=c, alpha=0.35, linewidth=0)

    ax1.set_title(f"{ticker} Historical Trajectory & Classified Regimes", fontsize=11, fontweight="bold")
    ax1.set_ylabel("Price ($)", fontsize=10)
    ax1.grid(True, linestyle=":", alpha=0.6)
    ax1.legend(loc="upper left", fontsize=8)

    # 2. Transition Matrix Heatmap
    ax2 = axes[0, 1]
    cax = ax2.imshow(transition_matrix, cmap="Blues", vmin=0, vmax=1)
    labels = ["Bull", "Neutral", "Bear"]
    ax2.set_xticks(range(3))
    ax2.set_yticks(range(3))
    ax2.set_xticklabels([f"To {l}" for l in labels], fontsize=9)
    ax2.set_yticklabels([f"From {l}" for l in labels], fontsize=9)
    ax2.set_title(r"DTMC Transition Probability Matrix $P_{ij}$", fontsize=11, fontweight="bold")

    for i in range(3):
        for j in range(3):
            val = transition_matrix[i, j]
            color = "white" if val > 0.5 else "black"
            ax2.text(j, i, f"{val:.3f}", ha="center", va="center", color=color, fontweight="bold", fontsize=10)
    fig.colorbar(cax, ax=ax2, shrink=0.75)

    # 3. Forward Monte Carlo Fan Cone
    ax3 = axes[1, 0]
    hist_sub = df["Close"].iloc[-45:]
    forecast_days = sim_results["paths"].shape[1] - 1
    future_x = np.arange(len(hist_sub), len(hist_sub) + forecast_days + 1)
    past_x = np.arange(len(hist_sub))

    ax3.plot(past_x, hist_sub.values, color="black", linewidth=1.5, label="Observed Price")
    
    # 80% and 50% bands
    ax3.fill_between(future_x, sim_results["p10"], sim_results["p90"], color="#80DEEA", alpha=0.4, label="80% Probability Interval")
    ax3.fill_between(future_x, sim_results["p25"], sim_results["p75"], color="#B39DDB", alpha=0.5, label="50% Interquartile Range")
    ax3.plot(future_x, sim_results["median"], color="#FF6F00", linewidth=2.0, label="Median Forecast")
    
    # A few random individual trajectories
    sample_indices = np.random.choice(sim_results["paths"].shape[0], size=min(15, sim_results["paths"].shape[0]), replace=False)
    for s_idx in sample_indices:
        ax3.plot(future_x, sim_results["paths"][s_idx], color="#00ACC1", alpha=0.15, linewidth=0.8)

    ax3.set_title(f"Monte Carlo Stochastic Fan ({forecast_days} Trading Days Forward)", fontsize=11, fontweight="bold")
    ax3.set_ylabel("Price ($)", fontsize=10)
    ax3.set_xlabel("Relative Trading Days", fontsize=10)
    ax3.grid(True, linestyle=":", alpha=0.6)
    ax3.legend(loc="upper left", fontsize=8)

    # 4. Long-Run Stationary Equilibrium π
    ax4 = axes[1, 1]
    bar_colors = ["#43A047", "#FBC02D", "#E53935"]
    bars = ax4.bar(labels, stationary_dist * 100, color=bar_colors, width=0.55, edgecolor="black", linewidth=0.8)
    ax4.set_title(r"Long-Run Stationary Equilibrium ($\boldsymbol{\pi}$)", fontsize=11, fontweight="bold")
    ax4.set_ylabel("Equilibrium Time Share (%)", fontsize=10)
    ax4.grid(axis="y", linestyle=":", alpha=0.6)
    for bar in bars:
        h = bar.get_height()
        ax4.text(bar.get_x() + bar.get_width()/2., h + 1.0, f"{h:.1f}%", ha="center", va="bottom", fontsize=10, fontweight="bold")
    ax4.set_ylim(0, max(stationary_dist * 100) + 15)

    return fig

