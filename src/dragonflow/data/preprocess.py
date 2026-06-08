"""数据预处理：缺失值填补 + 极端异常值过滤。

只处理"物理上不可能"的脏数据（如价格为负、单日暴涨 300%），
不干预正常的涨跌停波动。
"""
from __future__ import annotations

import pandas as pd
import numpy as np

from dragonflow.utils.logger import get_logger

logger = get_logger(__name__)

# 需要做数值清洗的列
NUMERIC_COLS: list[str] = [
    "open", "close", "high", "low",
    "volume", "amount",
    "amplitude", "pct_change", "change_amount", "turnover_rate",
]

# ---------------------------------------------------------------------------
# 异常值过滤
# ---------------------------------------------------------------------------

# 阈值常量
MAX_PCT_CHANGE = 22.0        # 日涨跌幅绝对值上限（%），A股涨跌停20% + 2%容差
MAX_INTRADAY_SWING = 0.50    # 单日振幅 (high-low)/low 上限
MAX_OVERNIGHT_JUMP = 3.0     # 与前日收盘价对比，|close/prev_close - 1| 上限


def filter_extreme_outliers(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """标记并清除极端异常值，将其设为 NaN。

    Returns:
        (cleaned_df, anomaly_report)
        anomaly_report 包含 stock_code, date, reason 列
    """
    df = df.copy()
    df = df.sort_values(["stock_code", "date"]).reset_index(drop=True)

    anomalies: list[dict] = []

    # ---- 规则 1：价格 <= 0 ----
    mask_neg_price = (df["close"] <= 0) | (df["open"] <= 0)
    for idx in df.index[mask_neg_price]:
        anomalies.append({
            "stock_code": df.at[idx, "stock_code"],
            "date": df.at[idx, "date"],
            "reason": f"价格<=0 (open={df.at[idx, 'open']}, close={df.at[idx, 'close']})",
        })

    # ---- 规则 2：日涨跌幅绝对值 > 22% ----
    mask_pct = df["pct_change"].abs() > MAX_PCT_CHANGE
    for idx in df.index[mask_pct]:
        anomalies.append({
            "stock_code": df.at[idx, "stock_code"],
            "date": df.at[idx, "date"],
            "reason": f"pct_change={df.at[idx, 'pct_change']:.2f}%",
        })

    # ---- 规则 3：单日振幅 > 50% ----
    with np.errstate(divide="ignore", invalid="ignore"):
        intraday_swing = (df["high"] - df["low"]) / df["low"]
    mask_swing = intraday_swing > MAX_INTRADAY_SWING
    for idx in df.index[mask_swing]:
        anomalies.append({
            "stock_code": df.at[idx, "stock_code"],
            "date": df.at[idx, "date"],
            "reason": f"振幅={intraday_swing.at[idx]:.2%}",
        })

    # ---- 规则 4：隔夜价格突变 > 300% ----
    prev_close = df.groupby("stock_code")["close"].shift(1)
    with np.errstate(divide="ignore", invalid="ignore"):
        overnight_jump = (df["close"] / prev_close - 1).abs()
    mask_jump = overnight_jump > MAX_OVERNIGHT_JUMP
    for idx in df.index[mask_jump]:
        anomalies.append({
            "stock_code": df.at[idx, "stock_code"],
            "date": df.at[idx, "date"],
            "reason": f"隔夜突变={overnight_jump.at[idx]:.2%} (prev={prev_close.at[idx]}→{df.at[idx, 'close']})",
        })

    # 合并所有异常 mask
    all_bad = mask_neg_price | mask_pct | mask_swing | mask_jump
    n_bad = all_bad.sum()

    if n_bad > 0:
        logger.info(f"检测到 {n_bad} 行极端异常，将数值列设为 NaN 等待插值填补")
        cols_to_nan = [c for c in NUMERIC_COLS if c in df.columns]
        df.loc[all_bad, cols_to_nan] = np.nan

    anomaly_df = pd.DataFrame(anomalies)
    return df, anomaly_df


# ---------------------------------------------------------------------------
# 缺失值填补
# ---------------------------------------------------------------------------

def fill_missing_by_interpolation(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """按 stock_code 分组，对数值列做线性插值，首尾用 ffill/bfill 兜底。

    Returns:
        (filled_df, total_filled_count)
    """
    df = df.sort_values(["stock_code", "date"]).reset_index(drop=True)
    cols = [c for c in NUMERIC_COLS if c in df.columns]

    before_na = df[cols].isna().sum().sum()

    # 按股票分组插值
    def _interpolate_group(g: pd.DataFrame) -> pd.DataFrame:
        g = g.sort_values("date")
        g[cols] = g[cols].interpolate(method="linear", limit_direction="both")
        # 首尾兜底
        g[cols] = g[cols].ffill().bfill()
        return g

    df = df.groupby("stock_code", group_keys=False).apply(_interpolate_group)

    after_na = df[cols].isna().sum().sum()
    filled = int(before_na - after_na)

    logger.info(f"缺失值填补完成：共填补 {filled} 个单元格，剩余 NaN {after_na} 个")
    return df, filled


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def build_preprocess_report(
    df: pd.DataFrame,
    anomaly_df: pd.DataFrame,
    filled_count: int,
) -> pd.DataFrame:
    """生成每只股票的预处理摘要报告。"""
    # 每只股票的行数
    stock_rows = df.groupby("stock_code").size().rename("total_rows")

    # 每只股票的异常数
    if not anomaly_df.empty:
        anomaly_counts = anomaly_df.groupby("stock_code").size().rename("anomaly_count")
    else:
        anomaly_counts = pd.Series(dtype=int, name="anomaly_count")

    # 每只股票剩余 NaN 数
    cols = [c for c in NUMERIC_COLS if c in df.columns]
    remaining_na = df.groupby("stock_code")[cols].apply(
        lambda g: g.isna().sum().sum()
    ).rename("remaining_na")

    report = pd.concat([stock_rows, anomaly_counts, remaining_na], axis=1).fillna(0)
    report = report.astype({"anomaly_count": int, "remaining_na": int})
    report = report.reset_index()
    report.attrs["total_filled"] = filled_count
    return report


def run_preprocess(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """执行完整预处理流水线。

    Returns:
        (clean_df, report_df)
    """
    n_rows_before = len(df)
    logger.info(f"开始预处理，输入 {n_rows_before} 行")

    # Step 1: 异常值 → NaN
    df, anomaly_df = filter_extreme_outliers(df)

    # Step 2: 统一插值填补
    df, filled_count = fill_missing_by_interpolation(df)

    # Step 3: 生成报告
    report = build_preprocess_report(df, anomaly_df, filled_count)

    n_rows_after = len(df)
    logger.info(
        f"预处理完成：{n_rows_before} → {n_rows_after} 行（不丢行），"
        f"异常标记 {len(anomaly_df)} 条，填补 {filled_count} 个单元格"
    )
    return df, report
