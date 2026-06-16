#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""第七步：构建 DragonFlow-KronosGraph V1 建模面板。

示例：

    uv run python scripts/07_build_model_dataset.py
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

from dragonflow.modeling.dataset import build_model_panel
from dragonflow.utils.io import resolve_path, save_json, save_parquet
from dragonflow.utils.logger import get_logger

logger = get_logger(__name__)

DEFAULT_DAILY = "data/processed/stock_daily_csi2000_qfq_20260101_20260531.parquet"
DEFAULT_INDEX = "data/processed/index_daily_932000_proxy_equal_weight_20260101_20260531.parquet"
DEFAULT_INFO = "data/processed/stock_info_csi2000_latest.parquet"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="构建 DragonFlow-KronosGraph V1 建模面板")
    p.add_argument("--daily", default=DEFAULT_DAILY, help="个股日线 Parquet/CSV")
    p.add_argument("--index", default=DEFAULT_INDEX, help="指数日线 Parquet/CSV，可选")
    p.add_argument("--info", default=DEFAULT_INFO, help="个股基础信息 Parquet/CSV，可选")
    p.add_argument("--output-dir", default="data/processed", help="输出目录")
    p.add_argument("--horizon", type=int, default=5, help="前瞻收益 horizon")
    return p.parse_args()


def _read_table(path_str: str, required: bool = True) -> pd.DataFrame | None:
    path = resolve_path(path_str)
    if not path.exists():
        if required:
            raise FileNotFoundError(f"输入文件不存在：{path}")
        logger.warning(f"可选输入不存在，跳过：{path}")
        return None
    if path.suffix.lower() == ".parquet":
        return pd.read_parquet(path)
    return pd.read_csv(path, dtype={"stock_code": str}, encoding="utf-8-sig")


def main() -> None:
    args = parse_args()

    daily_df = _read_table(args.daily, required=True)
    index_df = _read_table(args.index, required=False)
    stock_info = _read_table(args.info, required=False)

    panel, schema = build_model_panel(
        daily_df=daily_df,
        index_df=index_df,
        stock_info=stock_info,
        horizon=args.horizon,
    )

    out_dir = resolve_path(args.output_dir)
    panel_path = out_dir / "model_panel_base.parquet"
    schema_path = out_dir / "model_feature_schema_v1.json"
    split_path = out_dir / "model_time_split_v1.json"

    save_parquet(panel, panel_path)
    save_json(schema, schema_path)

    split = {
        "warmup_time_idx": [0, 39],
        "train_time_idx": [40, 64],
        "valid_time_idx": [65, 79],
        "test_time_idx": [80, 89],
        "prediction_only_time_idx": [90, 94],
        "horizon": args.horizon,
        "encoder_length": 30,
    }
    save_json(split, split_path)

    print("\n" + "=" * 60)
    print("DragonFlow-KronosGraph V1 建模面板完成")
    print(f"  行数：{len(panel)}")
    print(f"  列数：{panel.shape[1]}")
    print(f"  股票数：{panel['stock_code'].nunique()}")
    print(f"  交易日数：{panel['date'].nunique()}")
    print(f"  输出：{panel_path}")
    print(f"  Schema：{schema_path}")
    print(f"  切分：{split_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()
