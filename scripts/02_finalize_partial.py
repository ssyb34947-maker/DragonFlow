#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""把 ``data/raw/stock_daily/qfq/*.csv`` 已下载的股票整合成最终产物。

在网络/接口暂时不可用时使用，不再调任何 AkShare 接口，仅做本地汇总：
    - 合并长表 -> data/processed/stock_daily_csi2000_qfq_*.csv/.parquet
    - data_coverage_report.csv
    - download_manifest.json （成功/失败计数基于成分股 vs 现有 CSV 文件）
    - download_errors.csv （把成分股中缺失文件的标记为 MissingLocalFile）
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "src"))

import pandas as pd

from dragonflow.utils.io import (  # noqa: E402
    ensure_dir,
    now_iso,
    project_root,
    resolve_path,
    save_csv,
    save_json,
    save_parquet,
    to_yyyymmdd,
)
from dragonflow.utils.logger import get_logger  # noqa: E402

log = get_logger("dragonflow.finalize")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--start-date", default="2026-01-01")
    p.add_argument("--end-date", default="2026-05-31")
    p.add_argument("--index-code", default="932000")
    p.add_argument("--adjust", default="qfq")
    return p.parse_args()


def main() -> int:
    a = parse_args()
    sd_compact = to_yyyymmdd(a.start_date)
    ed_compact = to_yyyymmdd(a.end_date)

    p_raw_csi = resolve_path("data", "raw", "csi2000")
    p_raw_stock = resolve_path("data", "raw", "stock_daily", a.adjust)
    p_proc = resolve_path("data", "processed")
    ensure_dir(p_proc)

    cons_path = p_raw_csi / f"constituents_{a.index_code}_latest.csv"
    if not cons_path.exists():
        log.error(f"成分股文件不存在: {cons_path}")
        return 2

    constituents = pd.read_csv(cons_path, dtype={"stock_code": str}, encoding="utf-8-sig")
    constituents["stock_code"] = constituents["stock_code"].astype(str).str.zfill(6)
    code_to_name = dict(zip(constituents["stock_code"], constituents.get("stock_name", "")))

    files = sorted(p_raw_stock.glob("*.csv"))
    log.info(f"发现 {len(files)} 个个股 CSV，合并中...")

    frames: list[pd.DataFrame] = []
    have_codes: set[str] = set()
    for f in files:
        try:
            df = pd.read_csv(f, dtype={"stock_code": str}, encoding="utf-8-sig")
            if df.empty:
                continue
            if "stock_code" not in df.columns:
                continue
            df["stock_code"] = df["stock_code"].astype(str).str.zfill(6)
            have_codes.add(df["stock_code"].iloc[0])
            frames.append(df)
        except Exception as e:  # noqa: BLE001
            log.warning(f"{f.name}: {e}")

    if frames:
        merged = pd.concat(frames, ignore_index=True)
        merged = merged.sort_values(["stock_code", "date"]).reset_index(drop=True)
    else:
        merged = pd.DataFrame()

    sd_csv = p_proc / f"stock_daily_csi2000_{a.adjust}_{sd_compact}_{ed_compact}.csv"
    sd_pq = p_proc / f"stock_daily_csi2000_{a.adjust}_{sd_compact}_{ed_compact}.parquet"
    output_files: list[str] = []
    if not merged.empty:
        save_csv(merged, sd_csv)
        try:
            save_parquet(merged, sd_pq)
            output_files.extend([str(sd_csv), str(sd_pq)])
        except Exception as e:  # noqa: BLE001
            log.warning(f"parquet 失败: {e}")
            output_files.append(str(sd_csv))
        log.info(f"合并长表 rows={len(merged)} -> {sd_csv}")

    # 覆盖率
    try:
        expected_n = len(pd.bdate_range(start=a.start_date, end=a.end_date))
    except Exception:
        expected_n = 0
    if not merged.empty:
        gb = merged.groupby("stock_code").agg(
            n_daily_rows=("date", "count"),
            first_date=("date", "min"),
            last_date=("date", "max"),
        )
    else:
        gb = pd.DataFrame()

    rows = []
    for code in constituents["stock_code"]:
        if code in gb.index:
            r = gb.loc[code]
            n = int(r["n_daily_rows"])
            first = r["first_date"]
            last = r["last_date"]
        else:
            n, first, last = 0, "", ""
        missing = 0.0 if expected_n == 0 else max(0.0, 1.0 - n / expected_n)
        rows.append({
            "stock_code": code,
            "stock_name": code_to_name.get(code, ""),
            "n_daily_rows": n,
            "first_date": first,
            "last_date": last,
            "missing_ratio": round(missing, 4),
            "download_success": code in have_codes and n > 0,
        })
    coverage = pd.DataFrame(rows)
    cov_path = p_proc / "data_coverage_report.csv"
    save_csv(coverage, cov_path)
    output_files.append(str(cov_path))

    # errors（针对缺失的成分股标记 MissingLocalFile）
    missing_codes = [c for c in constituents["stock_code"] if c not in have_codes]
    err_rows = [
        {
            "stage": "stock_daily",
            "stock_code": c,
            "stock_name": code_to_name.get(c, ""),
            "error_type": "MissingLocalFile",
            "error_message": "下载阶段网络/代理异常未能拉到该股票数据",
            "time": now_iso(),
        }
        for c in missing_codes
    ]
    err_path = p_proc / "download_errors.csv"
    if err_rows:
        save_csv(pd.DataFrame(err_rows), err_path)
        output_files.append(str(err_path))

    manifest = {
        "run_time": now_iso(),
        "finish_time": now_iso(),
        "start_date": a.start_date,
        "end_date": a.end_date,
        "index_code": a.index_code,
        "adjust": a.adjust,
        "mode": "finalize_partial",
        "n_constituents": int(len(constituents)),
        "n_stock_daily_success": int(len(have_codes)),
        "n_stock_daily_failed": int(len(missing_codes)),
        "n_index_daily_rows": 0,
        "n_stock_daily_rows": int(len(merged)) if not merged.empty else 0,
        "n_stock_info_rows": 0,
        "n_fundamental_rows": 0,
        "warnings": [
            "本次为本地 finalize_partial 模式：未补刷指数行情/基础信息/财报/快照",
            f"成分股下载失败 {len(missing_codes)}/{len(constituents)} ({len(missing_codes)/len(constituents):.1%})，原因记录于 download_errors.csv",
        ],
        "output_files": output_files,
    }
    save_json(manifest, p_proc / "download_manifest.json")
    log.info(
        f"finalize 完成: 成功 {len(have_codes)} 失败 {len(missing_codes)} 总成分股 {len(constituents)} 合并行 {len(merged) if not merged.empty else 0}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
