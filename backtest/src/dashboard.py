import streamlit as st
import pandas as pd
import plotly.graph_objects as go


def load_backtest_data():
    """Load all CSV files generated by the backtest"""
    results_dir = "./results"

    # Load performance summary
    summary_df = pd.read_csv(f"{results_dir}/performance_summary.csv")
    summary_df["start_date"] = pd.to_datetime(summary_df["start_date"])
    summary_df["end_date"] = pd.to_datetime(summary_df["end_date"])

    # Load timeline data for each period
    timelines = {}
    for period in ["last_month", "full_3mo", "prior_2mo"]:
        df = pd.read_csv(
            f"{results_dir}/timeline_{period}.csv", index_col=0, parse_dates=True
        )

        # Find first non-zero equity value
        first_equity_idx = (df["equity"] > 0).idxmax()
        if first_equity_idx:
            # Start from the first non-zero equity row
            df = df.loc[first_equity_idx:]

        timelines[period] = df

    return summary_df, timelines


# Streamlit App
st.set_page_config(layout="wide")
st.title("BTC Momentum Strategy Dashboard")

st.markdown("""
### Strategy Overview
- **Asset:** BTC/USD (1-minute data, 3 months)
- **Position Size:** Fixed 0.03 BTC per trade
- **Strategies:** EMA Crossover Ensemble (5 pairs)
- **Signal:** Median of fast/slow EMA crossovers
- **Volume Filter:** Trade only when volume > 20-period average
- **Execution:** Signal generated with 2-bar lag
- **EMA Pairs:** (6,19), (6,22), (8,21), (4,26), (4,23)
""")
# Load data
summary_df, timelines = load_backtest_data()

# Period selector
period_options = {
    "Last Month": "last_month",
    "Full 3 Months": "full_3mo",
    "Prior 2 Months": "prior_2mo",
}

selected_period_name = st.selectbox("Select Time Period:", list(period_options.keys()))
selected_period = period_options[selected_period_name]

# Get data for selected period
timeline_df = timelines[selected_period]
period_summary = summary_df[summary_df["period"] == selected_period].iloc[0]
initial_capital = period_summary["initial_capital"]

# Calculate derived metrics
equity = timeline_df["equity"].ffill()
cum_pnl = equity - initial_capital

st.markdown("### Backtest Summary")
st.markdown(f"""
- **Period:** {period_summary["start_date"].strftime("%Y-%m-%d")} to {period_summary["end_date"].strftime("%Y-%m-%d")}
- **Data Points:** {period_summary["rows"]} bars  
- **Initial Capital (USD):** {initial_capital:.2f}
""")

# Performance metrics table
metrics_data = {
    "Net PnL (USD)": f"{period_summary['net_pnl']:.2f}",
    "Total Return (%)": f"{period_summary['total_return_pct']:.2f}",
    "Sharpe Ratio": f"{period_summary['sharpe_ratio']:.3f}",
    "Max Drawdown (%)": f"{period_summary['max_drawdown_pct']:.2f}",
    "Win Rate (%)": f"{period_summary['win_rate_pct']:.1f}",
    "Trades Per Year": f"{period_summary['trades_per_year']:.0f}",
    "Avg Hold Time (hrs)": f"{period_summary['avg_hold_hours']:.2f}",
    "Total Volume (USD)": f"{period_summary['total_volume_usd']:,.0f}",
    "Daily Volume (USD)": f"{period_summary['avg_daily_volume']:,.0f}",
    "Hourly Volume (USD)": f"{period_summary['avg_hourly_volume']:,.0f}",
    "Actual Trades": f"{period_summary['actual_trades']:,}",
    "Signal Flips": f"{period_summary['signal_flips']:,}",
}

metrics_df = pd.DataFrame(list(metrics_data.items()), columns=["Metric", "Value"])
st.dataframe(metrics_df, use_container_width=True)

st.markdown("---")
st.markdown("### Equity Curve & Volatility")

# Equity curve
fig_equity = go.Figure()
fig_equity.add_trace(
    go.Scatter(x=timeline_df.index, y=equity, name="Equity", line=dict(color="#1f77b4"))
)
fig_equity.update_layout(
    height=400,
    margin=dict(t=20, b=20),
    xaxis_title="Time",
    yaxis_title="Equity (USD)",
    title="Equity Curve",
)
st.plotly_chart(fig_equity, use_container_width=True)

# Cumulative PnL
fig_pnl = go.Figure()
fig_pnl.add_trace(
    go.Scatter(
        x=timeline_df.index,
        y=cum_pnl,
        name="Cumulative PnL",
        line=dict(color="#EF553B"),
    )
)
fig_pnl.update_layout(
    height=400,
    margin=dict(t=20, b=20),
    xaxis_title="Time",
    yaxis_title="PnL (USD)",
    title="Cumulative PnL",
)
st.plotly_chart(fig_pnl, use_container_width=True)

st.markdown("---")
st.markdown("### Volume Analysis")

# Daily volume chart
daily_volume = timeline_df.groupby(timeline_df.index.date)["volume_usd"].sum()

fig_daily_vol = go.Figure()
fig_daily_vol.add_trace(
    go.Bar(
        x=daily_volume.index,
        y=daily_volume.values,
        name="Daily Volume",
        marker=dict(color="#00CC96"),
    )
)
fig_daily_vol.update_layout(
    height=300,
    title="Daily Trading Volume",
    xaxis_title="Date",
    yaxis_title="Volume (USD)",
    margin=dict(t=20, b=20),
)
st.plotly_chart(fig_daily_vol, use_container_width=True)

# Volatility analysis
pct_change = equity.pct_change().fillna(0)
vol_rolling = pct_change.rolling(30).std()

fig_vol = go.Figure()
fig_vol.add_trace(
    go.Scatter(
        x=timeline_df.index,
        y=100 * pct_change,
        name="% Change",
        line=dict(color="#FFA15A"),
    )
)
fig_vol.add_trace(
    go.Scatter(
        x=timeline_df.index,
        y=100 * vol_rolling,
        name="30-Bar Rolling Vol",
        line=dict(color="#FF6692", dash="dot"),
    )
)
fig_vol.update_layout(
    height=300, xaxis_title="Time", yaxis_title="Volatility (%)", yaxis_tickformat=".2f"
)
st.plotly_chart(fig_vol, use_container_width=True)

st.markdown("---")
st.markdown("### Signals & Positions")

# Signal visualization
fig_signals = go.Figure()

# Add equity as background
fig_signals.add_trace(
    go.Scatter(
        x=timeline_df.index,
        y=timeline_df["equity"],
        name="Equity",
        line=dict(color="#1f77b4", width=1),
        yaxis="y2",
    )
)

# Add signals
signals = timeline_df["signal"].fillna(0)
fig_signals.add_trace(
    go.Scatter(
        x=timeline_df.index,
        y=signals,
        name="Signal",
        line=dict(color="#EF553B", width=2),
        mode="lines",
    )
)

fig_signals.update_layout(
    height=300,
    margin=dict(t=20),
    yaxis=dict(title="Signal", range=[-1.5, 1.5]),
    yaxis2=dict(title="Equity (USD)", overlaying="y", side="right"),
)
st.plotly_chart(fig_signals, use_container_width=True)

# Entry/Exit markers
entries_exits = timeline_df[timeline_df["is_entry"] | timeline_df["is_exit"]].copy()
if not entries_exits.empty:
    fig_trades = go.Figure()
    fig_trades.add_trace(
        go.Scatter(
            x=timeline_df.index, y=equity, name="Equity", line=dict(color="#1f77b4")
        )
    )

    entries = entries_exits[entries_exits["is_entry"]]
    exits = entries_exits[entries_exits["is_exit"]]

    if not entries.empty:
        fig_trades.add_trace(
            go.Scatter(
                x=entries.index,
                y=entries["equity"],
                mode="markers",
                name="Entries",
                marker=dict(color="green", size=10, symbol="triangle-up"),
            )
        )

    if not exits.empty:
        fig_trades.add_trace(
            go.Scatter(
                x=exits.index,
                y=exits["equity"],
                mode="markers",
                name="Exits",
                marker=dict(color="red", size=10, symbol="triangle-down"),
            )
        )

    fig_trades.update_layout(height=300, margin=dict(t=20), yaxis_title="USD")
    st.plotly_chart(fig_trades, use_container_width=True)

st.markdown("---")
st.markdown("### Trade Log & Distribution")

trade_log = timeline_df[timeline_df["is_exit"] | timeline_df["is_entry"]].copy()

if not trade_log.empty:
    # Display trade log
    display_cols = [
        "signal",
        "price",
        "qty",
        "pnl",
        "equity",
        "volume_usd",
        "is_entry",
        "is_exit",
    ]
    available_cols = [col for col in display_cols if col in trade_log.columns]
    st.dataframe(trade_log[available_cols], use_container_width=True, height=400)

    # Signal distribution
    if "signal" in trade_log.columns:
        signal_counts = trade_log["signal"].value_counts()
        summary = signal_counts.rename(
            {1: "Long Signals", -1: "Short Signals", 0: "Neutral"}
        ).to_frame("Count")

        st.markdown("**Signal Distribution**")
        st.dataframe(summary, use_container_width=True)
else:
    st.info("No trades found for this period.")

st.markdown("---")
st.markdown("### Performance Comparison Across Periods")

# Create comparison table
comparison_data = []
period_names = {
    "last_month": "Last Month",
    "full_3mo": "Full 3 Months",
    "prior_2mo": "Prior 2 Months",
}

for _, row in summary_df.iterrows():
    comparison_data.append(
        {
            "Period": period_names[row["period"]],
            "Return (%)": f"{row['total_return_pct']:.2f}",
            "Sharpe": f"{row['sharpe_ratio']:.3f}",
            "Max DD (%)": f"{row['max_drawdown_pct']:.2f}",
            "Win Rate (%)": f"{row['win_rate_pct']:.1f}",
            "Trades/Year": f"{row['trades_per_year']:.0f}",
        }
    )

comparison_df = pd.DataFrame(comparison_data)
st.dataframe(comparison_df, use_container_width=True)

st.markdown("""
---
**Backtest Engine:** Custom Python with EMA Ensemble  
**Data Source:** BTC 1-minute OHLC (3 months)  
**Strategy Details:** 5 EMA pairs with median signal aggregation  
""")
