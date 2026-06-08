#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""第六步：PCA + KMeans 股票聚类。

示例：

    uv run python scripts/06_clustering.py

    # 指定聚类数
    uv run python scripts/06_clustering.py --k 5

    # 指定输入文件
    uv run python scripts/06_clustering.py \
        --input data/processed/stock_features.csv
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

from dragonflow.analysis.clustering import run_full_pipeline
from dragonflow.utils.io import resolve_path, save_csv
from dragonflow.utils.logger import get_logger

logger = get_logger(__name__)

DEFAULT_INPUT = "data/processed/stock_features.csv"
DEFAULT_OUTPUT_DIR = "data/processed"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="DragonFlow PCA + KMeans 聚类")
    p.add_argument(
        "--input", "-i",
        default=DEFAULT_INPUT,
        help="输入特征 CSV 文件路径（相对项目根目录）",
    )
    p.add_argument(
        "--output-dir", "-o",
        default=DEFAULT_OUTPUT_DIR,
        help="输出目录（相对项目根目录）",
    )
    p.add_argument(
        "--k",
        type=int,
        default=None,
        help="聚类数 k（不指定则自动搜索最优 k）",
    )
    p.add_argument(
        "--variance-ratio",
        type=float,
        default=0.90,
        help="PCA 保留方差比例（默认 0.90）",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()

    # ---- 读取特征数据 ----
    input_path = resolve_path(args.input)
    if not input_path.exists():
        logger.error(f"输入文件不存在：{input_path}")
        sys.exit(1)

    logger.info(f"读取特征数据：{input_path}")
    features_df = pd.read_csv(input_path, dtype={"stock_code": str}, encoding="utf-8-sig")
    if "stock_code" in features_df.columns:
        features_df["stock_code"] = features_df["stock_code"].astype(str).str.zfill(6)
    logger.info(f"读取完成：{len(features_df)} 只股票，{features_df.shape[1]} 列")

    # ---- 运行聚类流水线 ----
    result = run_full_pipeline(
        features_df,
        k=args.k,
        variance_ratio=args.variance_ratio,
    )

    labels = result["labels"]
    cluster_names = result["cluster_names"]
    pca_2d = result["pca_2d"]
    k_search = result["k_search"]

    # ---- 保存 stock_clusters.csv ----
    out_dir = resolve_path(args.output_dir)

    clusters_df = features_df.copy()
    clusters_df["cluster_id"] = labels
    clusters_df["cluster_name"] = [cluster_names.get(int(lbl), f"未分类_{lbl}") for lbl in labels]

    clusters_path = out_dir / "stock_clusters.csv"
    save_csv(clusters_df, clusters_path)
    logger.info(f"聚类结果已保存：{clusters_path}")

    # ---- 保存 pca_2d.csv ----
    pca_2d_df = pd.DataFrame({
        "stock_code": features_df["stock_code"].values if "stock_code" in features_df.columns else range(len(features_df)),
        "pc1": pca_2d[:, 0],
        "pc2": pca_2d[:, 1],
        "cluster_id": labels,
        "cluster_name": [cluster_names.get(int(lbl), f"未分类_{lbl}") for lbl in labels],
    })

    pca_path = out_dir / "pca_2d.csv"
    save_csv(pca_2d_df, pca_path)
    logger.info(f"PCA 2D 坐标已保存：{pca_path}")

    # ---- 保存 k_search.csv ----
    k_search_df = pd.DataFrame({
        "k": k_search["k_range"],
        "inertia": k_search["inertias"],
        "silhouette": k_search["silhouette_scores"],
        "calinski": k_search["calinski_scores"],
    })

    k_search_path = out_dir / "k_search.csv"
    save_csv(k_search_df, k_search_path)
    logger.info(f"K 搜索结果已保存：{k_search_path}")

    # ---- 打印摘要 ----
    final_k = len(cluster_names)
    print("\n" + "=" * 60)
    print("聚类完成")
    print(f"  股票数量：{len(features_df)}")
    print(f"  特征数量：{len(result['feature_cols'])}")
    print(f"  PCA 主成分数：{result['pca_model'].n_components_}")
    print(f"  最终聚类数 k：{final_k}")
    print(f"  最优 k（silhouette）：{k_search['best_k']}")
    print("-" * 60)
    for cid in sorted(cluster_names.keys()):
        count = int((labels == cid).sum())
        name = cluster_names[cid]
        print(f"  簇 {cid}：{name}（{count} 只）")
    print("-" * 60)
    print(f"  输出文件：")
    print(f"    {clusters_path}")
    print(f"    {pca_path}")
    print(f"    {k_search_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()
