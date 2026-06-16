"""Technical and K-line shape features for daily stock bars."""
from __future__ import annotations

import numpy as np
import pandas as pd


def _safe_div(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    denominator = denominator.replace(0, np.nan)
    return numerator / denominator


def _rolling_zscore(series: pd.Series, window: int) -> pd.Series:
    mean = series.rolling(window, min_periods=max(3, window // 2)).mean()
    std = series.rolling(window, min_periods=max(3, window // 2)).std()
    return (series - mean) / std.replace(0, np.nan)


def add_technical_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add leakage-safe per-stock technical features."""
    out = df.sort_values(["stock_code", "date"]).copy()
    g = out.groupby("stock_code", sort=False)

    out["open_to_close"] = _safe_div(out["close"], out["open"]) - 1.0
    out["high_to_low"] = _safe_div(out["high"], out["low"]) - 1.0
    out["close_to_high"] = _safe_div(out["close"], out["high"]) - 1.0
    out["close_to_low"] = _safe_div(out["close"], out["low"]) - 1.0
    out["log_volume"] = np.log1p(out["volume"].clip(lower=0))
    out["log_amount"] = np.log1p(out["amount"].clip(lower=0))

    for window in (1, 3, 5, 10, 20):
        out[f"ret_{window}d"] = g["close"].pct_change(window)

    ma5 = g["close"].transform(lambda s: s.rolling(5, min_periods=3).mean())
    ma10 = g["close"].transform(lambda s: s.rolling(10, min_periods=5).mean())
    ma20 = g["close"].transform(lambda s: s.rolling(20, min_periods=10).mean())
    out["ma5_gap"] = _safe_div(out["close"], ma5) - 1.0
    out["ma10_gap"] = _safe_div(out["close"], ma10) - 1.0
    out["ma20_gap"] = _safe_div(out["close"], ma20) - 1.0
    out["ma5_ma20_gap"] = _safe_div(ma5, ma20) - 1.0

    for window in (5, 10, 20):
        out[f"vol_{window}d"] = g["ret_1d"].transform(
            lambda s, w=window: s.rolling(w, min_periods=max(3, w // 2)).std()
        )

    out["amount_mean_5d"] = g["amount"].transform(lambda s: s.rolling(5, min_periods=3).mean())
    out["amount_mean_20d"] = g["amount"].transform(lambda s: s.rolling(20, min_periods=10).mean())
    out["amount_zscore_20d"] = g["amount"].transform(lambda s: _rolling_zscore(s, 20))
    out["turnover_mean_5d"] = g["turnover_rate"].transform(lambda s: s.rolling(5, min_periods=3).mean())
    out["turnover_mean_20d"] = g["turnover_rate"].transform(lambda s: s.rolling(20, min_periods=10).mean())
    out["turnover_zscore_20d"] = g["turnover_rate"].transform(lambda s: _rolling_zscore(s, 20))

    rolling_low = g["low"].transform(lambda s: s.rolling(20, min_periods=10).min())
    rolling_high = g["high"].transform(lambda s: s.rolling(20, min_periods=10).max())
    out["price_position_20d"] = _safe_div(out["close"] - rolling_low, rolling_high - rolling_low)

    out["is_big_up"] = (out["pct_change"] >= 5.0).astype("float64")
    out["is_big_down"] = (out["pct_change"] <= -5.0).astype("float64")
    out["is_limit_up_like"] = (out["pct_change"] >= 9.5).astype("float64")
    out["is_limit_down_like"] = (out["pct_change"] <= -9.5).astype("float64")
    return out


def add_kline_shape_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add Kronos-inspired continuous K-line shape features."""
    out = df.sort_values(["stock_code", "date"]).copy()
    g = out.groupby("stock_code", sort=False)

    body_top = pd.concat([out["open"], out["close"]], axis=1).max(axis=1)
    body_bottom = pd.concat([out["open"], out["close"]], axis=1).min(axis=1)
    prev_close = g["close"].shift(1)
    prev_log_volume = g["log_volume"].shift(1) if "log_volume" in out.columns else np.log1p(g["volume"].shift(1))
    prev_log_amount = g["log_amount"].shift(1) if "log_amount" in out.columns else np.log1p(g["amount"].shift(1))

    out["k_body"] = _safe_div(out["close"], out["open"]) - 1.0
    out["k_range"] = _safe_div(out["high"], out["low"]) - 1.0
    out["k_upper_shadow"] = _safe_div(out["high"], body_top) - 1.0
    out["k_lower_shadow"] = _safe_div(body_bottom, out["low"]) - 1.0
    out["k_close_pos"] = _safe_div(out["close"] - out["low"], out["high"] - out["low"])
    out["k_gap"] = _safe_div(out["open"], prev_close) - 1.0
    out["k_volume_chg"] = out["log_volume"] - prev_log_volume
    out["k_amount_chg"] = out["log_amount"] - prev_log_amount

    for col in ("k_body", "k_range"):
        out[f"{col}_mean_5d"] = g[col].transform(lambda s: s.rolling(5, min_periods=3).mean())
        out[f"{col}_std_5d"] = g[col].transform(lambda s: s.rolling(5, min_periods=3).std())

    out["k_upper_shadow_mean_5d"] = g["k_upper_shadow"].transform(
        lambda s: s.rolling(5, min_periods=3).mean()
    )
    out["k_lower_shadow_mean_5d"] = g["k_lower_shadow"].transform(
        lambda s: s.rolling(5, min_periods=3).mean()
    )
    out["k_close_pos_mean_5d"] = g["k_close_pos"].transform(
        lambda s: s.rolling(5, min_periods=3).mean()
    )
    out["k_gap_abs_mean_5d"] = g["k_gap"].transform(
        lambda s: s.abs().rolling(5, min_periods=3).mean()
    )
    return out
