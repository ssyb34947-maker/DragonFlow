"""Per-stock feature extraction from daily OHLCV data.

Each ``compute_*`` helper accepts a DataFrame that represents a single stock's
trading history (typically 95 trading days) and returns a dict (or scalar) of
derived feature values.  The public entry-point is :func:`extract_all_features`,
which orchestrates grouping, computation and optional merging of auxiliary data.
"""
from __future__ import annotations

import datetime as _dt
from typing import Any

import numpy as np
import pandas as pd

from dragonflow.utils.logger import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_MIN_DAYS = 5  # ignore stocks with fewer trading days


def _safe_div(numerator: float, denominator: float, default: float = np.nan) -> float:
    """Return *numerator / denominator*, or *default* when denominator is zero/NaN."""
    if denominator == 0 or np.isnan(denominator):
        return default
    return numerator / denominator


# ---------------------------------------------------------------------------
# Individual feature functions
# ---------------------------------------------------------------------------


def compute_return_features(g: pd.DataFrame) -> dict[str, float]:
    """Compute cumulative-return, monthly-return-std, up-day ratio, skew and kurtosis.

    Returns
    -------
    dict with keys:
        cum_return, monthly_return_std, up_day_ratio, return_skew, return_kurtosis
    """
    close = g["close"].values
    pct = g["pct_change"].dropna()

    # cum_return
    first_close = close[0]
    last_close = close[-1]
    cum_return = _safe_div(last_close - first_close, first_close, 0.0) * 100.0

    # monthly_return_std – group by year-month, take last/first close per month
    g_sorted = g.sort_values("date")
    g_sorted = g_sorted.assign(_ym=g_sorted["date"].dt.to_period("M"))
    monthly_close = g_sorted.groupby("_ym")["close"].agg(["first", "last"])
    if len(monthly_close) >= 2:
        monthly_ret = (monthly_close["last"] / monthly_close["first"] - 1) * 100.0
        monthly_return_std = float(monthly_ret.std(ddof=1))
    else:
        monthly_return_std = np.nan

    # up_day_ratio
    total = len(pct)
    up_day_ratio = _safe_div(float((pct > 0).sum()), float(total), np.nan)

    # skew & kurtosis
    return_skew = float(pct.skew()) if total >= 3 else np.nan
    return_kurtosis = float(pct.kurtosis()) if total >= 4 else np.nan

    return {
        "cum_return": cum_return,
        "monthly_return_std": monthly_return_std,
        "up_day_ratio": up_day_ratio,
        "return_skew": return_skew,
        "return_kurtosis": return_kurtosis,
    }


def compute_excess_return(g: pd.DataFrame, index_daily: pd.DataFrame) -> float:
    """Excess return = stock cumulative return minus index cumulative return over
    the same calendar period.

    Parameters
    ----------
    g : pd.DataFrame
        Single-stock group (must contain *date* and *close*).
    index_daily : pd.DataFrame
        Index daily data with at least *date* and *close* columns.
    """
    g_sorted = g.sort_values("date")
    start_date = g_sorted["date"].iloc[0]
    end_date = g_sorted["date"].iloc[-1]

    stock_first = g_sorted["close"].iloc[0]
    stock_last = g_sorted["close"].iloc[-1]
    stock_cum = _safe_div(stock_last - stock_first, stock_first, 0.0) * 100.0

    idx = index_daily.loc[
        (index_daily["date"] >= start_date) & (index_daily["date"] <= end_date)
    ].sort_values("date")

    if idx.empty or len(idx) < 2:
        return np.nan

    idx_first = idx["close"].iloc[0]
    idx_last = idx["close"].iloc[-1]
    idx_cum = _safe_div(idx_last - idx_first, idx_first, 0.0) * 100.0

    return stock_cum - idx_cum


def compute_risk_features(g: pd.DataFrame) -> dict[str, float]:
    """Compute annual volatility, max drawdown, downside volatility and max single drop.

    Returns
    -------
    dict with keys:
        annual_volatility, max_drawdown, downside_volatility, max_single_drop
    """
    pct = g["pct_change"].dropna().values.astype(np.float64)

    # annual_volatility
    if len(pct) >= 2:
        annual_volatility = float(np.std(pct, ddof=1) * np.sqrt(252))
    else:
        annual_volatility = np.nan

    # max_drawdown – based on cumulative wealth curve
    close = g.sort_values("date")["close"].values.astype(np.float64)
    if len(close) >= 2:
        running_max = np.maximum.accumulate(close)
        drawdowns = (close - running_max) / running_max * 100.0
        max_drawdown = float(np.min(drawdowns))  # most negative value
    else:
        max_drawdown = np.nan

    # downside_volatility (annualised)
    neg_pct = pct[pct < 0]
    if len(neg_pct) >= 2:
        downside_volatility = float(np.std(neg_pct, ddof=1) * np.sqrt(252))
    else:
        downside_volatility = np.nan

    # max_single_drop
    max_single_drop = float(np.min(pct)) if len(pct) > 0 else np.nan

    return {
        "annual_volatility": annual_volatility,
        "max_drawdown": max_drawdown,
        "downside_volatility": downside_volatility,
        "max_single_drop": max_single_drop,
    }


def compute_trend_features(g: pd.DataFrame) -> dict[str, float]:
    """Compute momentum indicators and moving-average signals.

    Returns
    -------
    dict with keys:
        momentum_20d, momentum_60d, ma5_above_ma20_ratio, price_position
    """
    g_sorted = g.sort_values("date")
    close = g_sorted["close"].values.astype(np.float64)
    n = len(close)

    # momentum_20d
    if n >= 20:
        momentum_20d = (close[-1] / close[-20] - 1) * 100.0
    else:
        momentum_20d = np.nan

    # momentum_60d
    if n >= 60:
        momentum_60d = (close[-1] / close[-60] - 1) * 100.0
    else:
        momentum_60d = np.nan

    # ma5_above_ma20_ratio – need at least 20 data points for MA20
    if n >= 20:
        ma5 = pd.Series(close).rolling(5, min_periods=5).mean().values
        ma20 = pd.Series(close).rolling(20, min_periods=20).mean().values
        valid = ~(np.isnan(ma5) | np.isnan(ma20))
        if valid.sum() > 0:
            ma5_above_ma20_ratio = float(np.sum((ma5 > ma20) & valid)) / float(valid.sum())
        else:
            ma5_above_ma20_ratio = np.nan
    else:
        ma5_above_ma20_ratio = np.nan

    # price_position
    period_high = float(np.max(close))
    period_low = float(np.min(close))
    price_range = period_high - period_low
    if price_range > 0:
        price_position = (close[-1] - period_low) / price_range
    else:
        price_position = np.nan

    return {
        "momentum_20d": float(momentum_20d) if not np.isnan(momentum_20d) else np.nan,
        "momentum_60d": float(momentum_60d) if not np.isnan(momentum_60d) else np.nan,
        "ma5_above_ma20_ratio": float(ma5_above_ma20_ratio) if not np.isnan(ma5_above_ma20_ratio) else np.nan,
        "price_position": float(price_position) if not np.isnan(price_position) else np.nan,
    }


def compute_trade_features(g: pd.DataFrame) -> dict[str, float]:
    """Compute liquidity / trading-activity features.

    Returns
    -------
    dict with keys:
        avg_amount, avg_turnover, amount_cv, turnover_cv, low_trade_ratio
    """
    amount = g["amount"].dropna().values.astype(np.float64)
    turnover = g["turnover_rate"].dropna().values.astype(np.float64)

    avg_amount = float(np.mean(amount)) if len(amount) > 0 else np.nan
    avg_turnover = float(np.mean(turnover)) if len(turnover) > 0 else np.nan

    # coefficient of variation
    if len(amount) >= 2 and np.mean(amount) != 0:
        amount_cv = float(np.std(amount, ddof=1) / np.mean(amount))
    else:
        amount_cv = np.nan

    if len(turnover) >= 2 and np.mean(turnover) != 0:
        turnover_cv = float(np.std(turnover, ddof=1) / np.mean(turnover))
    else:
        turnover_cv = np.nan

    # low_trade_ratio
    if len(amount) > 0:
        median_amount = float(np.median(amount))
        threshold = median_amount * 0.3
        low_trade_ratio = float(np.sum(amount < threshold)) / float(len(amount))
    else:
        low_trade_ratio = np.nan

    return {
        "avg_amount": avg_amount,
        "avg_turnover": avg_turnover,
        "amount_cv": amount_cv,
        "turnover_cv": turnover_cv,
        "low_trade_ratio": low_trade_ratio,
    }


def compute_volume_price_features(g: pd.DataFrame) -> dict[str, float]:
    """Compute volume-price correlation and volume-spike counts.

    Returns
    -------
    dict with keys:
        price_volume_corr, vol_up_count, vol_down_count
    """
    pct = g["pct_change"].values.astype(np.float64)
    vol = g["volume"].values.astype(np.float64)

    # Mask NaN positions for correlation
    valid = ~(np.isnan(pct) | np.isnan(vol))
    if valid.sum() >= 3:
        price_volume_corr = float(np.corrcoef(pct[valid], vol[valid])[0, 1])
    else:
        price_volume_corr = np.nan

    # volume spike threshold
    vol_valid = vol[~np.isnan(vol)]
    if len(vol_valid) > 0:
        vol_median = float(np.median(vol_valid))
        high_vol = vol > vol_median * 1.5
    else:
        high_vol = np.zeros(len(vol), dtype=bool)

    vol_up_count = float(np.nansum((pct > 0) & high_vol))
    vol_down_count = float(np.nansum((pct < 0) & high_vol))

    return {
        "price_volume_corr": price_volume_corr,
        "vol_up_count": vol_up_count,
        "vol_down_count": vol_down_count,
    }


def compute_anomaly_features(g: pd.DataFrame) -> dict[str, float]:
    """Compute limit-hit counts, big-move counts and average amplitude.

    Returns
    -------
    dict with keys:
        limit_up_count, limit_down_count, big_yang_count, big_yin_count, avg_amplitude
    """
    pct = g["pct_change"].dropna().values.astype(np.float64)
    amplitude = g["amplitude"].dropna().values.astype(np.float64)

    limit_up_count = float(np.sum(pct >= 9.5))
    limit_down_count = float(np.sum(pct <= -9.5))
    big_yang_count = float(np.sum(pct >= 5.0))
    big_yin_count = float(np.sum(pct <= -5.0))
    avg_amplitude = float(np.mean(amplitude)) if len(amplitude) > 0 else np.nan

    return {
        "limit_up_count": limit_up_count,
        "limit_down_count": limit_down_count,
        "big_yang_count": big_yang_count,
        "big_yin_count": big_yin_count,
        "avg_amplitude": avg_amplitude,
    }


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


def extract_all_features(
    daily_df: pd.DataFrame,
    index_daily: pd.DataFrame | None = None,
    stock_info: pd.DataFrame | None = None,
    spot_snapshot: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Extract all features for every stock in *daily_df*.

    Parameters
    ----------
    daily_df : pd.DataFrame
        Daily OHLCV data.  Must contain columns: date, stock_code, open,
        close, high, low, volume, amount, amplitude, pct_change,
        change_amount, turnover_rate.
    index_daily : pd.DataFrame | None
        Optional index (benchmark) daily data with *date* and *close*.
        Used to compute excess return.
    stock_info : pd.DataFrame | None
        Optional stock metadata.  Expected columns: stock_code,
        total_market_value, industry, listing_date.
    spot_snapshot : pd.DataFrame | None
        Optional real-time snapshot.  Expected columns: stock_code,
        pe_dynamic, pb.

    Returns
    -------
    pd.DataFrame
        One row per stock with stock_code as index and all computed features
        as columns.
    """
    records: list[dict[str, Any]] = []
    grouped = daily_df.groupby("stock_code")
    total_groups = len(grouped)
    logger.info("Extracting features for {} stocks", total_groups)

    for code, g in grouped:
        g = g.sort_values("date").reset_index(drop=True)

        if len(g) < _MIN_DAYS:
            logger.debug("Skipping {} – only {} trading days", code, len(g))
            continue

        row: dict[str, Any] = {"stock_code": code}

        # --- return features ---
        try:
            row.update(compute_return_features(g))
        except Exception:
            logger.warning("Return features failed for {}", code)
            for k in ("cum_return", "monthly_return_std", "up_day_ratio",
                       "return_skew", "return_kurtosis"):
                row.setdefault(k, np.nan)

        # --- excess return ---
        if index_daily is not None:
            try:
                row["excess_return"] = compute_excess_return(g, index_daily)
            except Exception:
                logger.warning("Excess return failed for {}", code)
                row["excess_return"] = np.nan
        else:
            row["excess_return"] = np.nan

        # --- risk features ---
        try:
            row.update(compute_risk_features(g))
        except Exception:
            logger.warning("Risk features failed for {}", code)
            for k in ("annual_volatility", "max_drawdown",
                       "downside_volatility", "max_single_drop"):
                row.setdefault(k, np.nan)

        # --- trend features ---
        try:
            row.update(compute_trend_features(g))
        except Exception:
            logger.warning("Trend features failed for {}", code)
            for k in ("momentum_20d", "momentum_60d",
                       "ma5_above_ma20_ratio", "price_position"):
                row.setdefault(k, np.nan)

        # --- trade features ---
        try:
            row.update(compute_trade_features(g))
        except Exception:
            logger.warning("Trade features failed for {}", code)
            for k in ("avg_amount", "avg_turnover", "amount_cv",
                       "turnover_cv", "low_trade_ratio"):
                row.setdefault(k, np.nan)

        # --- volume-price features ---
        try:
            row.update(compute_volume_price_features(g))
        except Exception:
            logger.warning("Volume-price features failed for {}", code)
            for k in ("price_volume_corr", "vol_up_count", "vol_down_count"):
                row.setdefault(k, np.nan)

        # --- anomaly features ---
        try:
            row.update(compute_anomaly_features(g))
        except Exception:
            logger.warning("Anomaly features failed for {}", code)
            for k in ("limit_up_count", "limit_down_count",
                       "big_yang_count", "big_yin_count", "avg_amplitude"):
                row.setdefault(k, np.nan)

        records.append(row)

    if not records:
        logger.warning("No stocks produced features – returning empty DataFrame")
        return pd.DataFrame()

    features_df = pd.DataFrame(records).set_index("stock_code")

    # ------------------------------------------------------------------
    # Merge optional auxiliary data
    # ------------------------------------------------------------------
    if stock_info is not None:
        try:
            info = stock_info.copy()
            if "stock_code" in info.columns:
                info = info.set_index("stock_code")

            # total_market_value
            if "total_market_value" in info.columns:
                features_df["total_market_value"] = info["total_market_value"].reindex(
                    features_df.index
                ).astype(float)

            # industry (str)
            if "industry" in info.columns:
                features_df["industry"] = info["industry"].reindex(features_df.index)

            # listing_years
            if "listing_date" in info.columns:
                today = pd.Timestamp(_dt.date.today())
                listing_dates = pd.to_datetime(
                    info["listing_date"], errors="coerce"
                ).reindex(features_df.index)
                features_df["listing_years"] = (
                    (today - listing_dates).dt.days / 365.25
                )
        except Exception:
            logger.warning("Merging stock_info failed – skipping auxiliary columns")

    if spot_snapshot is not None:
        try:
            snap = spot_snapshot.copy()
            if "stock_code" in snap.columns:
                snap = snap.set_index("stock_code")

            if "pe_dynamic" in snap.columns:
                features_df["pe"] = (
                    snap["pe_dynamic"]
                    .reindex(features_df.index)
                    .astype(float)
                )
            if "pb" in snap.columns:
                features_df["pb"] = (
                    snap["pb"]
                    .reindex(features_df.index)
                    .astype(float)
                )
        except Exception:
            logger.warning("Merging spot_snapshot failed – skipping pe/pb columns")

    logger.info(
        "Feature extraction complete – {} stocks, {} features",
        len(features_df),
        len(features_df.columns),
    )
    return features_df
