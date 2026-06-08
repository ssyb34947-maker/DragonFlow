#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""第三步：数据预处理（缺失值填补 + 极端异常过滤）。

示例：

    uv run python scripts/03_preprocess_data.py

    # 指定输入文件
    uv run python scripts/03_preprocess_data.py \
        --input data/processed/stock_daily_csi2000_qfq_20260101_20260531.csv
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

from dragonflow.data.preprocess import run_preprocess
from dragonflow.utils.io import (
    resolve_path,
    save_csv,
    save_parquet,
)
from dragonflow.utils.logger import get_logger

logger = get_logger(__name__)

# 默认输入文件
DEFAULT_INPUT = "data/processed/stock_daily_csi2000_qfq_20260101_20260531.csv"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="DragonFlow 数据预处理")
    p.add_argument(
        "--input", "-i",
        default=DEFAULT_INPUT,
        help="输入 CSV 文件路径（相对项目根目录）",
    )
    p.add_argument(
        "--output-dir", "-o",
        default="data/processed",
        help="输出目录（相对项目根目录）",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()

    # ---- 读取数据 ----
    input_path = resolve_path(args.input)
    if not input_path.exists():
        logger.error(f"输入文件不存在：{input_path}")
        sys.exit(1)

    logger.info(f"读取数据：{input_path}")
    df = pd.read_csv(input_path, dtype={"stock_code": str}, encoding="utf-8-sig")
    df["stock_code"] = df["stock_code"].astype(str).str.zfill(6)
    logger.info(f"读取完成：{len(df)} 行，{df['stock_code'].nunique()} 只股票")

    # ---- 预处理 ----
    clean_df, report_df = run_preprocess(df)

    # ---- 输出 ----
    out_dir = resolve_path(args.output_dir)

    # 清洗后的数据
    stem = Path(args.input).stem + "_clean"
    csv_path = out_dir / f"{stem}.csv"
    parquet_path = out_dir / f"{stem}.parquet"
    save_csv(clean_df, csv_path)
    save_parquet(clean_df, parquet_path)
    logger.info(f"清洗数据已保存：{csv_path}")

    # 预处理报告
    report_path = out_dir / "preprocess_report.csv"
    save_csv(report_df, report_path)
    logger.info(f"预处理报告已保存：{report_path}")

    # ---- 摘要 ----
    total_filled = report_df.attrs.get("total_filled", "N/A")
    total_anomaly = int(report_df["anomaly_count"].sum())
    total_remaining_na = int(report_df["remaining_na"].sum())

    print("\n" + "=" * 60)
    print("预处理完成")
    print(f"  输入行数：{len(df)}")
    print(f"  输出行数：{len(clean_df)}（不丢行）")
    print(f"  异常标记：{total_anomaly} 条")
    print(f"  缺失填补：{total_filled} 个单元格")
    print(f"  剩余 NaN：{total_remaining_na}")
    print(f"  输出文件：{csv_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()
