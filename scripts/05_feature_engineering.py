#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""第五步：从清洗后的日线数据中提取股票特征（每只股票一行）。

示例：

    uv run python scripts/05_feature_engineering.py
    python scripts/05_feature_engineering.py
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC = _REPO_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import pandas as pd

from dragonflow.features.engineering import extract_all_features
from dragonflow.utils.io import resolve_path, save_csv, save_parquet
from dragonflow.utils.logger import get_logger

logger = get_logger(__name__)

DEFAULT_DAILY = "data/processed/stock_daily_csi2000_qfq_20260101_20260531_clean.csv"
DEFAULT_INDEX = "data/processed/index_daily_932000_20260101_20260531.csv"
DEFAULT_INFO = "data/processed/stock_info_csi2000_latest.csv"
DEFAULT_SNAP = "data/processed/stock_spot_snapshot_csi2000_latest.csv"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="DragonFlow 特征工程")
    p.add_argument("--daily", default=DEFAULT_DAILY, help="清洗后的日线 CSV")
    p.add_argument("--index", default=DEFAULT_INDEX, help="指数日线 CSV（可选）")
    p.add_argument("--info", default=DEFAULT_INFO, help="个股基础信息 CSV（可选）")
    p.add_argument("--snapshot", default=DEFAULT_SNAP, help="实时快照 CSV（可选）")
    p.add_argument("--output-dir", default="data/processed", help="输出目录")
    return p.parse_args()


def _try_load(path_str: str, name: str) -> pd.DataFrame | None:
    p = resolve_path(path_str)
    if not p.exists():
        logger.warning(f"{name} 文件不存在，跳过：{p}")
        return None
    df = pd.read_csv(p, dtype={"stock_code": str}, encoding="utf-8-sig")
    if "stock_code" in df.columns:
        df["stock_code"] = df["stock_code"].astype(str).str.zfill(6)
    logger.info(f"加载 {name}：{len(df)} 行")
    return df


def main() -> None:
    args = parse_args()

    # 读取日线数据
    daily_path = resolve_path(args.daily)
    if not daily_path.exists():
        logger.error(f"日线数据不存在：{daily_path}")
        sys.exit(1)
    daily_df = pd.read_csv(daily_path, dtype={"stock_code": str}, encoding="utf-8-sig")
    daily_df["stock_code"] = daily_df["stock_code"].astype(str).str.zfill(6)
    daily_df["date"] = pd.to_datetime(daily_df["date"])
    logger.info(f"日线数据：{len(daily_df)} 行，{daily_df['stock_code'].nunique()} 只股票")

    # 可选数据
    index_daily = _try_load(args.index, "指数日线")
    if index_daily is not None and "date" in index_daily.columns:
        index_daily["date"] = pd.to_datetime(index_daily["date"])
        index_daily["close"] = pd.to_numeric(index_daily["close"], errors="coerce")

    stock_info = _try_load(args.info, "个股基础信息")
    spot_snapshot = _try_load(args.snapshot, "实时快照")

    # 提取特征
    features_df = extract_all_features(
        daily_df=daily_df,
        index_daily=index_daily,
        stock_info=stock_info,
        spot_snapshot=spot_snapshot,
    )

    # 合入 stock_name
    constituents_path = resolve_path("data/raw/csi2000/constituents_932000_latest.csv")
    if constituents_path.exists():
        cons = pd.read_csv(constituents_path, dtype={"stock_code": str}, encoding="utf-8-sig")
        cons["stock_code"] = cons["stock_code"].astype(str).str.zfill(6)
        if "stock_name" in cons.columns:
            name_map = cons.set_index("stock_code")["stock_name"]
            features_df.insert(0, "stock_name", features_df.index.map(name_map))

    # 保存
    out_dir = resolve_path(args.output_dir)
    csv_path = out_dir / "stock_features.csv"
    pq_path = out_dir / "stock_features.parquet"
    save_csv(features_df.reset_index(), csv_path)
    save_parquet(features_df.reset_index(), pq_path)

    print("\n" + "=" * 60)
    print("特征工程完成")
    print(f"  股票数：{len(features_df)}")
    print(f"  特征数：{len(features_df.columns)}")
    print(f"  输出：{csv_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()
