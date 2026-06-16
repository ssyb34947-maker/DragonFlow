"""Market and cross-sectional context features."""
from __future__ import annotations

import pandas as pd


def build_index_features(index_df: pd.DataFrame | None) -> pd.DataFrame:
    """Build date-level index context features."""
    if index_df is None or index_df.empty:
        return pd.DataFrame(columns=[
            "date",
            "index_ret_1d",
            "index_ret_5d",
            "index_ret_20d",
            "index_vol_10d",
            "index_vol_20d",
        ])

    idx = index_df[["date", "close"]].copy().sort_values("date")
    idx["date"] = pd.to_datetime(idx["date"])
    idx["index_ret_1d"] = idx["close"].pct_change(1)
    idx["index_ret_5d"] = idx["close"].pct_change(5)
    idx["index_ret_20d"] = idx["close"].pct_change(20)
    idx["index_vol_10d"] = idx["index_ret_1d"].rolling(10, min_periods=5).std()
    idx["index_vol_20d"] = idx["index_ret_1d"].rolling(20, min_periods=10).std()
    return idx.drop(columns=["close"])


def build_cross_sectional_market_features(df: pd.DataFrame) -> pd.DataFrame:
    """Build market-wide context from the stock universe by date."""
    daily = (
        df.groupby("date", sort=True)
        .agg(
            market_ret_mean_1d=("ret_1d", "mean"),
            market_ret_std_1d=("ret_1d", "std"),
            market_breadth=("ret_1d", lambda s: float((s > 0).mean())),
            market_amount_sum=("amount", "sum"),
            market_turnover_mean=("turnover_rate", "mean"),
        )
        .reset_index()
    )
    return daily
