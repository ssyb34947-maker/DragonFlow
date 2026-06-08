"""字段映射 / 列名标准化。

把 AkShare 接口返回的中文列名映射成统一的英文列名，方便后续画像计算。
"""
from __future__ import annotations

from typing import Iterable

import pandas as pd


# ---------------------------------------------------------------------------
# 成分股
# ---------------------------------------------------------------------------
# index_stock_cons_csindex 返回的中文字段（不同 AkShare 版本略有差异）
CONSTITUENTS_RENAME: dict[str, str] = {
    "日期": "in_date",
    "指数代码": "index_code",
    "指数名称": "index_name",
    "成分券代码": "stock_code",
    "成分券名称": "stock_name",
    "交易所": "exchange",
    "交易所英文名称": "exchange_en",
    # index_stock_cons / 备用接口
    "品种代码": "stock_code",
    "品种名称": "stock_name",
    "纳入日期": "in_date",
    "代码": "stock_code",
    "名称": "stock_name",
}

CONSTITUENTS_REQUIRED: list[str] = [
    "stock_code",
    "stock_name",
    "index_code",
    "index_name",
    "exchange",
    "in_date",
    "source",
    "download_date",
]


# ---------------------------------------------------------------------------
# 指数日行情
# ---------------------------------------------------------------------------
INDEX_DAILY_RENAME: dict[str, str] = {
    "date": "date",
    "open": "open",
    "high": "high",
    "low": "low",
    "close": "close",
    "volume": "volume",
    "amount": "amount",
    "日期": "date",
    "开盘": "open",
    "最高": "high",
    "最低": "low",
    "收盘": "close",
    "成交量": "volume",
    "成交额": "amount",
}

INDEX_DAILY_COLS: list[str] = [
    "date",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "amount",
    "index_code",
    "source",
]


# ---------------------------------------------------------------------------
# 个股日行情（stock_zh_a_hist）
# ---------------------------------------------------------------------------
STOCK_DAILY_RENAME: dict[str, str] = {
    "日期": "date",
    "股票代码": "stock_code",
    "开盘": "open",
    "收盘": "close",
    "最高": "high",
    "最低": "low",
    "成交量": "volume",
    "成交额": "amount",
    "振幅": "amplitude",
    "涨跌幅": "pct_change",
    "涨跌额": "change_amount",
    "换手率": "turnover_rate",
}

STOCK_DAILY_COLS: list[str] = [
    "date",
    "stock_code",
    "open",
    "close",
    "high",
    "low",
    "volume",
    "amount",
    "amplitude",
    "pct_change",
    "change_amount",
    "turnover_rate",
    "adjust",
    "source",
]


# ---------------------------------------------------------------------------
# 个股基础信息（stock_individual_info_em）—— 该接口返回 item/value 长表
# ---------------------------------------------------------------------------
STOCK_INFO_ITEM_RENAME: dict[str, str] = {
    "股票代码": "stock_code",
    "股票简称": "stock_name",
    "总股本": "total_share",
    "流通股": "float_share",
    "总市值": "total_market_value",
    "流通市值": "float_market_value",
    "行业": "industry",
    "上市时间": "listing_date",
}

STOCK_INFO_COLS: list[str] = [
    "stock_code",
    "stock_name",
    "total_share",
    "float_share",
    "total_market_value",
    "float_market_value",
    "industry",
    "listing_date",
    "source",
    "download_date",
]


# ---------------------------------------------------------------------------
# 实时快照（stock_zh_a_spot_em）
# ---------------------------------------------------------------------------
SPOT_RENAME: dict[str, str] = {
    "代码": "stock_code",
    "名称": "stock_name",
    "最新价": "latest_price",
    "涨跌幅": "pct_change",
    "换手率": "turnover_rate",
    "成交量": "volume",
    "成交额": "amount",
    "振幅": "amplitude",
    "市盈率-动态": "pe_dynamic",
    "市净率": "pb",
    "总市值": "total_market_value",
    "流通市值": "float_market_value",
}

SPOT_PREFERRED_COLS: list[str] = [
    "stock_code",
    "stock_name",
    "latest_price",
    "pct_change",
    "turnover_rate",
    "volume",
    "amount",
    "amplitude",
    "pe_dynamic",
    "pb",
    "total_market_value",
    "float_market_value",
]


# ---------------------------------------------------------------------------
# 财务报表
# ---------------------------------------------------------------------------
# 这些接口字段在不同 AkShare 版本里差异较大，下面只列“尽量覆盖”的常见命名。
PROFIT_RENAME: dict[str, str] = {
    "股票代码": "stock_code",
    "股票简称": "stock_name",
    "净利润": "net_profit",
    "净利润-同比增长": "net_profit_yoy",
    "净利润同比": "net_profit_yoy",
    "营业总收入": "revenue",
    "营业收入": "revenue",
    "营业总收入-同比增长": "revenue_yoy",
    "营业收入-同比增长": "revenue_yoy",
    "营业总收入同比": "revenue_yoy",
    "营业利润": "operating_profit",
    "利润总额": "total_profit",
    "公告日期": "announcement_date",
    "最新公告日期": "announcement_date",
    "报告期": "report_date",
    "报告日期": "report_date",
}

BALANCE_RENAME: dict[str, str] = {
    "股票代码": "stock_code",
    "股票简称": "stock_name",
    "资产-总资产": "total_assets",
    "总资产": "total_assets",
    "负债-总负债": "total_liabilities",
    "总负债": "total_liabilities",
    "资产负债率": "asset_liability_ratio",
    "股东权益合计": "equity",
    "所有者权益(或股东权益)合计": "equity",
    "公告日期": "announcement_date",
    "最新公告日期": "announcement_date",
    "报告期": "report_date",
    "报告日期": "report_date",
}

CASHFLOW_RENAME: dict[str, str] = {
    "股票代码": "stock_code",
    "股票简称": "stock_name",
    "净现金流": "net_cash_flow",
    "现金净流量": "net_cash_flow",
    "净现金流-净现金流": "net_cash_flow",
    "经营性现金流-现金流量净额": "operating_cash_flow",
    "经营现金流量净额": "operating_cash_flow",
    "投资性现金流-现金流量净额": "investing_cash_flow",
    "投资现金流量净额": "investing_cash_flow",
    "融资性现金流-现金流量净额": "financing_cash_flow",
    "筹资现金流量净额": "financing_cash_flow",
    "公告日期": "announcement_date",
    "最新公告日期": "announcement_date",
    "报告期": "report_date",
    "报告日期": "report_date",
}


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------
def rename_and_keep(
    df: pd.DataFrame,
    rename_map: dict[str, str],
    keep: Iterable[str] | None = None,
) -> pd.DataFrame:
    """把已知列重命名为英文；如指定 keep，仅保留这些列（缺失列补 None）。"""
    if df is None or df.empty:
        return pd.DataFrame(columns=list(keep) if keep else [])
    df = df.rename(columns=rename_map)
    if keep is not None:
        for col in keep:
            if col not in df.columns:
                df[col] = None
        df = df[list(keep)]
    return df


def ensure_stock_code_str(df: pd.DataFrame, col: str = "stock_code") -> pd.DataFrame:
    """``stock_code`` 一律转为 6 位字符串。"""
    if col in df.columns:
        df[col] = df[col].astype(str).str.extract(r"(\d+)", expand=False).fillna("")
        df[col] = df[col].str.zfill(6)
    return df


def standardize_date_col(df: pd.DataFrame, col: str = "date") -> pd.DataFrame:
    """日期统一为 ``YYYY-MM-DD`` 字符串。"""
    if col in df.columns:
        df[col] = pd.to_datetime(df[col], errors="coerce").dt.strftime("%Y-%m-%d")
    return df
