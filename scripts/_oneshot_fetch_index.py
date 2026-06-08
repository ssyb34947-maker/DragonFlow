#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""One-shot: retry the official csi2000 index daily until it succeeds."""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "src"))

import akshare as ak
import pandas as pd

from dragonflow.utils.io import resolve_path, save_csv, save_parquet  # noqa: E402

START = "2026-01-01"
END = "2026-05-31"
INDEX = "932000"
MAX_ATTEMPTS = 10


def fetch_once():
    return ak.stock_zh_index_daily_em(symbol=f"csi{INDEX}")


def main() -> int:
    df = None
    for i in range(MAX_ATTEMPTS):
        try:
            df = fetch_once()
            if df is not None and not df.empty:
                print(f"attempt {i + 1}: OK rows={len(df)}")
                break
            raise RuntimeError("empty")
        except Exception as e:
            print(f"attempt {i + 1}: ERR {type(e).__name__}: {str(e)[:80]}")
            time.sleep(1.5)
    if df is None or df.empty:
        print("ALL ATTEMPTS FAILED")
        return 1

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    sub = df[(df["date"] >= START) & (df["date"] <= END)].copy()
    sub["date"] = sub["date"].dt.strftime("%Y-%m-%d")
    sub["index_code"] = INDEX
    sub["source"] = "stock_zh_index_daily_em(csi932000)"
    cols = ["date", "open", "high", "low", "close", "volume", "amount", "index_code", "source"]
    for c in cols:
        if c not in sub.columns:
            sub[c] = None
    sub = sub[cols].reset_index(drop=True)
    print(f"filtered to {len(sub)} rows in [{START}, {END}]")
    print(sub.head(2).to_string())
    print("...")
    print(sub.tail(2).to_string())

    p_csv = resolve_path("data", "raw", "csi2000", f"index_daily_{INDEX}_20260101_20260531.csv")
    p_pq = resolve_path("data", "raw", "csi2000", f"index_daily_{INDEX}_20260101_20260531.parquet")
    save_csv(sub, p_csv)
    save_parquet(sub, p_pq)
    print(f"saved: {p_csv}")

    mfp = resolve_path("data", "processed", "download_manifest.json")
    with open(mfp, "r", encoding="utf-8") as f:
        mf = json.load(f)
    mf["n_index_daily_rows"] = len(sub)
    of = list(mf.get("output_files", []))
    for p in (str(p_csv), str(p_pq)):
        if p not in of:
            of.append(p)
    mf["output_files"] = of
    with open(mfp, "w", encoding="utf-8") as f:
        json.dump(mf, f, ensure_ascii=False, indent=2)
    print("manifest updated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
