#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""合成中证2000等权重代理指数。

当 EM 的历史 K 线接口 push2his.eastmoney.com 无法触达、
新浪 csi2000 接口又有 akshare 内部 KeyError 时，
我们利用已经下好的 2000 只成分股 qfq 日线，
按"日等权重"做一个 csi2000 代理指数：

    每日代理收益 = 当日所有成分股 (close / prev_close - 1) 的算术平均
    代理 close   = base * 累乘(1 + 日收益)，base 默认 1000

它**不等于**官方中证2000指数（官方是自由流通市值加权），
但保留了整体涨跌方向、相关性结构、波动率级别，
足够用作"市场基准"用于个股相对强弱、Beta、Alpha 估计。

输出：
    data/processed/index_daily_932000_proxy_equal_weight_*.csv/.parquet
"""
from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "src"))

import pandas as pd

from dragonflow.utils.io import resolve_path, save_csv, save_parquet, to_yyyymmdd  # noqa: E402
from dragonflow.utils.logger import get_logger  # noqa: E402

log = get_logger("dragonflow.synth_index")


def synthesize(
    stock_daily: pd.DataFrame,
    index_code: str = "932000",
    base: float = 1000.0,
) -> pd.DataFrame:
    if stock_daily.empty:
        return pd.DataFrame()
    df = stock_daily[["date", "stock_code", "close"]].copy()
    df["close"] = pd.to_numeric(df["close"], errors="coerce")
    df = df.dropna(subset=["close"]).sort_values(["stock_code", "date"])
    df["prev_close"] = df.groupby("stock_code")["close"].shift(1)
    df["ret"] = df["close"] / df["prev_close"] - 1.0
    daily = (
        df.dropna(subset=["ret"])
        .groupby("date", as_index=False)
        .agg(
            mean_ret=("ret", "mean"),
            n_stocks=("ret", "count"),
        )
        .sort_values("date")
        .reset_index(drop=True)
    )
    daily["close"] = base * (1.0 + daily["mean_ret"]).cumprod()
    # 用同一天所有成分股的 (open/high/low 平均 vs close 平均) 比例放大代理 OHL
    aux = (
        stock_daily.assign(
            open=lambda x: pd.to_numeric(x["open"], errors="coerce"),
            high=lambda x: pd.to_numeric(x["high"], errors="coerce"),
            low=lambda x: pd.to_numeric(x["low"], errors="coerce"),
            close=lambda x: pd.to_numeric(x["close"], errors="coerce"),
            volume=lambda x: pd.to_numeric(x["volume"], errors="coerce"),
            amount=lambda x: pd.to_numeric(x["amount"], errors="coerce"),
        )
        .groupby("date", as_index=False)
        .agg(
            open_mean=("open", "mean"),
            high_mean=("high", "mean"),
            low_mean=("low", "mean"),
            close_mean=("close", "mean"),
            volume_sum=("volume", "sum"),
            amount_sum=("amount", "sum"),
        )
    )
    out = daily.merge(aux, on="date", how="left")
    # 用 close_mean 作为比例尺，把 open/high/low 缩放到代理 close 的量级
    out["scale"] = out["close"] / out["close_mean"]
    out["open"] = out["open_mean"] * out["scale"]
    out["high"] = out["high_mean"] * out["scale"]
    out["low"] = out["low_mean"] * out["scale"]
    out["volume"] = out["volume_sum"]
    out["amount"] = out["amount_sum"]
    out["index_code"] = index_code
    out["source"] = "computed_local_equal_weight_proxy"

    cols = [
        "date",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "amount",
        "n_stocks",
        "index_code",
        "source",
    ]
    return out[cols]


def main() -> int:
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("--start-date", default="2026-01-01")
    p.add_argument("--end-date", default="2026-05-31")
    p.add_argument("--index-code", default="932000")
    p.add_argument("--adjust", default="qfq")
    p.add_argument("--base", type=float, default=1000.0)
    a = p.parse_args()

    sd = to_yyyymmdd(a.start_date)
    ed = to_yyyymmdd(a.end_date)

    src = resolve_path(
        "data", "processed", f"stock_daily_csi2000_{a.adjust}_{sd}_{ed}.parquet"
    )
    if not src.exists():
        src_csv = src.with_suffix(".csv")
        if not src_csv.exists():
            log.error(f"找不到合并长表: {src} / {src_csv}")
            return 2
        src = src_csv

    log.info(f"读取合并长表: {src}")
    if src.suffix == ".parquet":
        stock_daily = pd.read_parquet(src)
    else:
        stock_daily = pd.read_csv(src, dtype={"stock_code": str}, encoding="utf-8-sig")
    log.info(f"长表 rows={len(stock_daily)}")

    proxy = synthesize(stock_daily, index_code=a.index_code, base=a.base)
    log.info(f"合成代理指数 rows={len(proxy)} (base={a.base})")

    csv_out = resolve_path(
        "data", "processed",
        f"index_daily_{a.index_code}_proxy_equal_weight_{sd}_{ed}.csv",
    )
    pq_out = csv_out.with_suffix(".parquet")
    save_csv(proxy, csv_out)
    try:
        save_parquet(proxy, pq_out)
    except Exception as e:  # noqa: BLE001
        log.warning(f"parquet 失败: {e}")
    log.info(f"已写入: {csv_out}")
    if not proxy.empty:
        log.info(
            f"区间 {proxy['date'].iloc[0]} -> {proxy['date'].iloc[-1]} "
            f"close: {proxy['close'].iloc[0]:.2f} -> {proxy['close'].iloc[-1]:.2f}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
