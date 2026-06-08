#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""从已下载的成分股日线合成"截面快照"。

当 EM 的 stock_zh_a_spot_em 因代理掐流不可用时，
用每只股票合并长表里**最后一个交易日**的行情数据近似充当快照：

    latest_price = 最后一日 close
    pct_change   = 最后一日 pct_change（若来自新浪源会缺失）
    turnover_rate = 最后一日 turnover_rate
    volume / amount / amplitude  同上

输出：
    data/processed/stock_spot_snapshot_csi2000_latest.csv/.parquet
    （source = derived_from_last_daily_row）
"""
from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "src"))

import pandas as pd

from dragonflow.utils.io import resolve_path, save_csv, save_parquet, today_str  # noqa: E402
from dragonflow.utils.logger import get_logger  # noqa: E402

log = get_logger("dragonflow.synth_spot")


def main() -> int:
    sd_path = resolve_path(
        "data", "processed", "stock_daily_csi2000_qfq_20260101_20260531.parquet"
    )
    if not sd_path.exists():
        log.error(f"找不到合并长表 {sd_path}")
        return 2

    df = pd.read_parquet(sd_path)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date", "stock_code"]).copy()

    # 每只股票的最后一行
    last_idx = df.sort_values("date").groupby("stock_code", as_index=False).tail(1)

    cons = pd.read_csv(
        resolve_path("data", "raw", "csi2000", "constituents_932000_latest.csv"),
        dtype={"stock_code": str},
        encoding="utf-8-sig",
    )
    cons["stock_code"] = cons["stock_code"].astype(str).str.zfill(6)
    code_to_name = dict(zip(cons["stock_code"], cons.get("stock_name", "")))

    snap = pd.DataFrame({
        "stock_code": last_idx["stock_code"].astype(str).str.zfill(6),
        "stock_name": last_idx["stock_code"].astype(str).str.zfill(6).map(code_to_name).fillna(""),
        "latest_price": pd.to_numeric(last_idx["close"], errors="coerce"),
        "pct_change": pd.to_numeric(last_idx.get("pct_change"), errors="coerce"),
        "turnover_rate": pd.to_numeric(last_idx.get("turnover_rate"), errors="coerce"),
        "volume": pd.to_numeric(last_idx.get("volume"), errors="coerce"),
        "amount": pd.to_numeric(last_idx.get("amount"), errors="coerce"),
        "amplitude": pd.to_numeric(last_idx.get("amplitude"), errors="coerce"),
        "pe_dynamic": None,
        "pb": None,
        "total_market_value": None,
        "float_market_value": None,
        "snapshot_date": last_idx["date"].dt.strftime("%Y-%m-%d"),
        "source": "derived_from_last_daily_row",
        "synthesized_at": today_str(),
    }).reset_index(drop=True)

    out_csv = resolve_path("data", "processed", "stock_spot_snapshot_csi2000_latest.csv")
    out_pq = out_csv.with_suffix(".parquet")
    save_csv(snap, out_csv)
    try:
        save_parquet(snap, out_pq)
    except Exception as e:  # noqa: BLE001
        log.warning(f"parquet 失败: {e}")
    log.info(
        f"合成快照: {len(snap)} 行, 快照日 {snap['snapshot_date'].min()} ~ {snap['snapshot_date'].max()}"
    )
    log.info(f"写入: {out_csv}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
