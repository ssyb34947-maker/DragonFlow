"""PCA 降维 + KMeans 聚类：对股票特征进行标准化、降维、聚类并自动命名。"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score, calinski_harabasz_score

from dragonflow.utils.logger import get_logger

logger = get_logger(__name__)

# Non-numeric / identifier columns to exclude from clustering features
EXCLUDE_COLS = ["stock_code", "industry", "stock_name"]


# ---------------------------------------------------------------------------
# 1. Feature preparation
# ---------------------------------------------------------------------------

def prepare_features(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Select numeric columns, handle NaN/inf, return clean DataFrame and feature names.

    Steps:
        1. Drop columns listed in ``EXCLUDE_COLS``.
        2. Keep only numeric columns.
        3. Replace ``inf`` / ``-inf`` with ``NaN``.
        4. Fill remaining ``NaN`` with per-column median.

    Returns:
        (clean_df, feature_names) where *clean_df* has the same index as *df*.
    """
    cols_to_drop = [c for c in EXCLUDE_COLS if c in df.columns]
    numeric_df = df.drop(columns=cols_to_drop, errors="ignore").select_dtypes(include="number")
    feature_names = list(numeric_df.columns)

    # Replace inf with NaN, then fill NaN with column median
    numeric_df = numeric_df.replace([np.inf, -np.inf], np.nan)
    medians = numeric_df.median()
    numeric_df = numeric_df.fillna(medians)

    # If any column is still entirely NaN (all values were NaN), fill with 0
    numeric_df = numeric_df.fillna(0.0)

    logger.info(f"特征准备完成：{len(feature_names)} 个特征，{len(numeric_df)} 行")
    return numeric_df, feature_names


# ---------------------------------------------------------------------------
# 2. Standardization
# ---------------------------------------------------------------------------

def standardize(df: pd.DataFrame, feature_cols: list[str]) -> tuple[np.ndarray, StandardScaler]:
    """StandardScaler on *feature_cols*. Returns (scaled_array, fitted scaler)."""
    scaler = StandardScaler()
    X = scaler.fit_transform(df[feature_cols].values)
    logger.info("标准化完成")
    return X, scaler


# ---------------------------------------------------------------------------
# 3. PCA
# ---------------------------------------------------------------------------

def run_pca(X: np.ndarray, variance_ratio: float = 0.90) -> tuple[np.ndarray, PCA]:
    """PCA retaining *variance_ratio* of total variance.

    Returns:
        (transformed_array, fitted PCA model)
    """
    pca = PCA(n_components=variance_ratio, svd_solver="full", random_state=42)
    X_pca = pca.fit_transform(X)
    n_components = pca.n_components_
    explained = pca.explained_variance_ratio_.sum()
    logger.info(
        f"PCA 完成：保留 {n_components} 个主成分，"
        f"解释方差 {explained:.2%}"
    )
    return X_pca, pca


# ---------------------------------------------------------------------------
# 4. Optimal K search
# ---------------------------------------------------------------------------

def find_optimal_k(X: np.ndarray, k_range: range = range(3, 11)) -> dict:
    """Run KMeans for each *k* in *k_range* and collect evaluation metrics.

    Returns a dict with:
        - ``inertias``:  list[float]
        - ``silhouette_scores``: list[float]
        - ``calinski_scores``:  list[float]
        - ``best_k``: int  (k with highest silhouette score)
        - ``k_range``: list[int]
    """
    inertias: list[float] = []
    sil_scores: list[float] = []
    ch_scores: list[float] = []

    for k in k_range:
        km = KMeans(n_clusters=k, n_init=10, random_state=42)
        labels = km.fit_predict(X)

        inertias.append(float(km.inertia_))
        sil = float(silhouette_score(X, labels))
        ch = float(calinski_harabasz_score(X, labels))
        sil_scores.append(sil)
        ch_scores.append(ch)
        logger.info(f"  k={k}  inertia={km.inertia_:.1f}  silhouette={sil:.4f}  CH={ch:.1f}")

    best_idx = int(np.argmax(sil_scores))
    best_k = list(k_range)[best_idx]
    logger.info(f"最优 k={best_k}（silhouette={sil_scores[best_idx]:.4f}）")

    return {
        "inertias": inertias,
        "silhouette_scores": sil_scores,
        "calinski_scores": ch_scores,
        "best_k": best_k,
        "k_range": list(k_range),
    }


# ---------------------------------------------------------------------------
# 5. KMeans
# ---------------------------------------------------------------------------

def run_kmeans(X: np.ndarray, k: int, random_state: int = 42) -> tuple[np.ndarray, KMeans]:
    """Run KMeans with *k* clusters. Returns (labels, fitted model)."""
    km = KMeans(n_clusters=k, n_init=10, random_state=random_state)
    labels = km.fit_predict(X)
    logger.info(f"KMeans 聚类完成：k={k}")
    return labels, km


# ---------------------------------------------------------------------------
# 6. Cluster labeling (Chinese)
# ---------------------------------------------------------------------------

_LABEL_RULES: list[tuple[str, callable]] = []  # populated below


def _above(series: pd.Series, global_mean: pd.Series, col: str, factor: float = 1.0) -> bool:
    """True if cluster mean of *col* is above *factor* * global mean."""
    if col not in series.index or col not in global_mean.index:
        return False
    return float(series[col]) > factor * float(global_mean[col])


def _below(series: pd.Series, global_mean: pd.Series, col: str, factor: float = 1.0) -> bool:
    """True if cluster mean of *col* is below *factor* * global mean."""
    if col not in series.index or col not in global_mean.index:
        return False
    return float(series[col]) < factor * float(global_mean[col])


def label_clusters(
    features_df: pd.DataFrame,
    labels: np.ndarray,
    feature_cols: list[str],
) -> dict[int, str]:
    """Auto-generate human-readable Chinese labels for each cluster.

    The labeling heuristic compares each cluster's feature means against the
    global mean and assigns one of eight archetypes.  If none matches the
    cluster is labeled ``"未分类_k"``.
    """
    tmp = features_df[feature_cols].copy()
    tmp["_cluster"] = labels

    cluster_means = tmp.groupby("_cluster")[feature_cols].mean()
    global_mean = tmp[feature_cols].mean()

    # Ordered rules: first match wins
    rules: list[tuple[str, callable]] = [
        (
            "高弹性反弹型",
            lambda row: (
                _above(row, global_mean, "cum_return")
                and _above(row, global_mean, "annual_volatility")
            ),
        ),
        (
            "题材活跃型",
            lambda row: (
                _above(row, global_mean, "limit_up_count")
                and _above(row, global_mean, "avg_turnover")
            ),
        ),
        (
            "放量突破型",
            lambda row: (
                _above(row, global_mean, "momentum_20d")
                and _above(row, global_mean, "avg_amount")
            ),
        ),
        (
            "超跌修复型",
            lambda row: (
                _below(row, global_mean, "cum_return")
                and _above(row, global_mean, "max_drawdown")
                and _above(row, global_mean, "momentum_20d", factor=0.0)
            ),
        ),
        (
            "稳健低波动型",
            lambda row: (
                _below(row, global_mean, "annual_volatility")
                and not _below(row, global_mean, "cum_return", factor=0.5)
            ),
        ),
        (
            "高波动型",
            lambda row: (
                _above(row, global_mean, "annual_volatility")
                and _above(row, global_mean, "avg_amplitude")
            ),
        ),
        (
            "低流动性型",
            lambda row: (
                _below(row, global_mean, "avg_amount")
                and _below(row, global_mean, "avg_turnover")
            ),
        ),
        (
            "弱势阴跌型",
            lambda row: (
                _below(row, global_mean, "cum_return")
                and _below(row, global_mean, "avg_turnover")
            ),
        ),
    ]

    used_labels: set[str] = set()
    result: dict[int, str] = {}

    for cluster_id in sorted(cluster_means.index):
        row = cluster_means.loc[cluster_id]
        assigned = False
        for label_name, rule_fn in rules:
            if label_name in used_labels:
                continue
            try:
                if rule_fn(row):
                    result[int(cluster_id)] = label_name
                    used_labels.add(label_name)
                    assigned = True
                    break
            except (KeyError, TypeError):
                continue
        if not assigned:
            result[int(cluster_id)] = f"未分类_{cluster_id}"

    logger.info(f"聚类命名完成：{result}")
    return result


# ---------------------------------------------------------------------------
# 7. Full pipeline
# ---------------------------------------------------------------------------

def run_full_pipeline(
    features_df: pd.DataFrame,
    k: int | None = None,
    variance_ratio: float = 0.90,
) -> dict:
    """End-to-end clustering pipeline.

    Parameters:
        features_df: DataFrame with one row per stock. Must contain numeric
            feature columns (and optionally ``stock_code``, ``industry``).
        k: Number of clusters.  If *None*, automatically selected via
            silhouette score search over ``range(3, 11)``.
        variance_ratio: Cumulative variance ratio to retain in PCA.

    Returns a dict with keys:
        - ``labels``: np.ndarray of cluster ids
        - ``cluster_names``: dict[int, str]
        - ``pca_2d``: np.ndarray of shape (n, 2) for plotting
        - ``pca_model``: fitted PCA (variance_ratio)
        - ``scaler``: fitted StandardScaler
        - ``kmeans``: fitted KMeans
        - ``k_search``: dict from :func:`find_optimal_k`
        - ``feature_cols``: list of feature names used
        - ``features_scaled``: standardized feature array
    """
    # 1. Prepare features
    clean_df, feature_cols = prepare_features(features_df)

    # 2. Standardize
    X_scaled, scaler = standardize(clean_df, feature_cols)

    # 3. PCA for clustering (retain variance_ratio)
    X_pca, pca_model = run_pca(X_scaled, variance_ratio=variance_ratio)

    # 4. Search optimal k
    k_search = find_optimal_k(X_pca)

    if k is None:
        k = k_search["best_k"]
        logger.info(f"自动选择 k={k}")

    # 5. Final KMeans
    labels, kmeans_model = run_kmeans(X_pca, k)

    # 6. Cluster labeling
    cluster_names = label_clusters(clean_df, labels, feature_cols)

    # 7. 2D PCA for visualization
    pca_2d_model = PCA(n_components=2, random_state=42)
    pca_2d = pca_2d_model.fit_transform(X_scaled)

    return {
        "labels": labels,
        "cluster_names": cluster_names,
        "pca_2d": pca_2d,
        "pca_model": pca_model,
        "scaler": scaler,
        "kmeans": kmeans_model,
        "k_search": k_search,
        "feature_cols": feature_cols,
        "features_scaled": X_scaled,
    }
