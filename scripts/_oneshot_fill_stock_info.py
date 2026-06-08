#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""One-shot: 补刷 stock_info 中缺失的成分股。

读已有的 stock_info CSV，识别成分股中尚未拿到 info 的代码，
只对这些代码调 EM 接口，最后追加合并并刷新 parquet。
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "src"))

import pandas as pd

from dragonflow.data.download import download_stock_info_batch  # noqa: E402
from dragonflow.utils.io import (  # noqa: E402
    append_error_row,
    resolve_path,
    save_csv,
    save_parquet,
    today_str,
)
from dragonflow.utils.logger import get_logger  # noqa: E402

log = get_logger("dragonflow.fill_info")


def main() -> int:
    cons_path = resolve_path("data", "raw", "csi2000", "constituents_932000_latest.csv")
    cons = pd.read_csv(cons_path, dtype={"stock_code": str}, encoding="utf-8-sig")
    cons["stock_code"] = cons["stock_code"].astype(str).str.zfill(6)
    name_map = dict(zip(cons["stock_code"], cons.get("stock_name", "")))

    today = today_str()
    info_csv = resolve_path("data", "raw", "fundamental", f"stock_info_csi2000_{today}.csv")
    pq_path = resolve_path("data", "processed", "stock_info_csi2000_latest.parquet")

    existing = pd.DataFrame()
    if info_csv.exists():
        existing = pd.read_csv(info_csv, dtype={"stock_code": str}, encoding="utf-8-sig")
        existing["stock_code"] = existing["stock_code"].astype(str).str.zfill(6)
    else:
        # try yesterday's file
        for p in sorted(info_csv.parent.glob("stock_info_csi2000_*.csv"), reverse=True):
            existing = pd.read_csv(p, dtype={"stock_code": str}, encoding="utf-8-sig")
            existing["stock_code"] = existing["stock_code"].astype(str).str.zfill(6)
            log.info(f"使用前一版 {p.name} 作为 existing 基础")
            break

    have = set(existing["stock_code"]) if not existing.empty else set()
    missing = [c for c in cons["stock_code"] if c not in have]
    log.info(f"成分股 {len(cons)}, 已有 info {len(have)}, 缺失 {len(missing)}")
    if not missing:
        log.info("没有缺失，直接退出")
        return 0

    err_path = resolve_path("data", "processed", "download_errors.csv")

    new_df, errs = download_stock_info_batch(
        stock_codes=missing,
        stock_names=name_map,
        sleep=0.25,
    )
    log.info(f"本轮成功 {len(new_df)} / {len(missing)}, 失败 {len(errs)}")

    for e in errs:
        append_error_row(err_path, {**e.to_dict(), "stage": "stock_info_fill"})

    merged = pd.concat([existing, new_df], ignore_index=True).drop_duplicates(
        subset=["stock_code"], keep="last"
    )
    save_csv(merged, info_csv)
    save_parquet(merged, pq_path)
    log.info(f"汇总 stock_info: {len(merged)} 行 -> {info_csv}, {pq_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
