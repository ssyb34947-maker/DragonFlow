"""Dataset assembly for DragonFlow-KronosGraph V1."""
from __future__ import annotations

import numpy as np
import pandas as pd

from dragonflow.modeling.market_features import (
    build_cross_sectional_market_features,
    build_index_features,
)
from dragonflow.modeling.schema import V1_SCHEMA
from dragonflow.modeling.targets import add_forward_return_targets
from dragonflow.modeling.technical_features import (
    add_kline_shape_features,
    add_technical_features,
)
from dragonflow.utils.logger import get_logger

logger = get_logger(__name__)


def _normalize_daily(daily_df: pd.DataFrame) -> pd.DataFrame:
    out = daily_df.copy()
    out["stock_code"] = out["stock_code"].astype(str).str.zfill(6)
    out["date"] = pd.to_datetime(out["date"])
    out = out.sort_values(["stock_code", "date"]).reset_index(drop=True)
    numeric_cols = [
        "open", "close", "high", "low", "volume", "amount", "amplitude",
        "pct_change", "change_amount", "turnover_rate",
    ]
    for col in numeric_cols:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")
    return out


def _add_time_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    dates = pd.Series(sorted(out["date"].dropna().unique()))
    time_map = {date: idx for idx, date in enumerate(dates)}
    out["time_idx"] = out["date"].map(time_map).astype("int64")
    out["day_of_week"] = out["date"].dt.dayofweek.astype("int64")
    out["month"] = out["date"].dt.month.astype("int64")
    out["is_month_end"] = out["date"].dt.is_month_end.astype("float64")
    return out


def _prepare_static_info(stock_info: pd.DataFrame | None) -> pd.DataFrame:
    if stock_info is None or stock_info.empty:
        return pd.DataFrame(columns=[
            "stock_code",
            "industry",
            "log_total_market_value",
            "log_float_market_value",
            "listing_years",
            "total_market_value_missing",
            "float_market_value_missing",
            "listing_years_missing",
        ])

    info = stock_info.copy()
    info["stock_code"] = info["stock_code"].astype(str).str.zfill(6)
    keep_cols = [
        "stock_code", "industry", "total_market_value", "float_market_value",
        "listing_date",
    ]
    keep_cols = [c for c in keep_cols if c in info.columns]
    info = info[keep_cols].drop_duplicates("stock_code", keep="last")

    if "industry" not in info.columns:
        info["industry"] = "UNKNOWN"
    info["industry"] = info["industry"].fillna("UNKNOWN").astype(str)

    for col in ("total_market_value", "float_market_value"):
        if col not in info.columns:
            info[col] = np.nan
        info[col] = pd.to_numeric(info[col], errors="coerce")
        info[f"{col}_missing"] = info[col].isna().astype("float64")
        info[f"log_{col}"] = np.log1p(info[col].clip(lower=0))

    if "listing_date" in info.columns:
        listing = pd.to_datetime(info["listing_date"], errors="coerce", format="%Y%m%d")
    else:
        listing = pd.Series(pd.NaT, index=info.index)
    anchor_date = pd.Timestamp.today().normalize()
    info["listing_years"] = (anchor_date - listing).dt.days / 365.25
    info["listing_years_missing"] = info["listing_years"].isna().astype("float64")

    return info[[
        "stock_code",
        "industry",
        "log_total_market_value",
        "log_float_market_value",
        "listing_years",
        "total_market_value_missing",
        "float_market_value_missing",
        "listing_years_missing",
    ]]


def _fill_feature_missing_values(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["industry"] = out.get("industry", "UNKNOWN")
    out["industry"] = out["industry"].fillna("UNKNOWN").astype(str)

    feature_cols = (
        list(V1_SCHEMA.static_reals)
        + list(V1_SCHEMA.time_varying_known_reals)
        + list(V1_SCHEMA.time_varying_observed_reals)
    )
    for col in feature_cols:
        if col not in out.columns:
            out[col] = np.nan
        if out[col].isna().any():
            median = out[col].median(skipna=True)
            if pd.isna(median):
                median = 0.0
            out[col] = out[col].fillna(float(median))
    return out


def build_model_panel(
    daily_df: pd.DataFrame,
    index_df: pd.DataFrame | None = None,
    stock_info: pd.DataFrame | None = None,
    horizon: int = 5,
) -> tuple[pd.DataFrame, dict[str, list[str]]]:
    """Build the V1 supervised modeling panel."""
    logger.info("开始构建 DragonFlow-KronosGraph V1 建模面板")
    panel = _normalize_daily(daily_df)
    panel = _add_time_features(panel)
    panel = add_technical_features(panel)
    panel = add_kline_shape_features(panel)

    index_features = build_index_features(index_df)
    if not index_features.empty:
        panel = panel.merge(index_features, on="date", how="left")

    market_features = build_cross_sectional_market_features(panel)
    panel = panel.merge(market_features, on="date", how="left")

    static_info = _prepare_static_info(stock_info)
    if not static_info.empty:
        panel = panel.merge(static_info, on="stock_code", how="left")

    panel = add_forward_return_targets(panel, index_df=index_df, horizon=horizon)
    panel = _fill_feature_missing_values(panel)

    schema = V1_SCHEMA.to_dict()
    ordered_cols: list[str] = []
    for cols in schema.values():
        for col in cols:
            if col in panel.columns and col not in ordered_cols:
                ordered_cols.append(col)
    passthrough = [c for c in ("open", "high", "low", "close", "volume", "amount") if c in panel.columns]
    ordered_cols.extend([c for c in passthrough if c not in ordered_cols])
    panel = panel[ordered_cols]

    logger.info(
        "建模面板完成：{} 行，{} 列，{} 只股票，{} 个交易日",
        len(panel),
        panel.shape[1],
        panel["stock_code"].nunique(),
        panel["date"].nunique(),
    )
    return panel, schema
