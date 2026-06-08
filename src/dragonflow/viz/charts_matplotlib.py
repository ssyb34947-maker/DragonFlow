"""Matplotlib 图表函数（静态统计图）。

风格：白色背景 · 干净利落 · 青绿品红活力色系
"""
from __future__ import annotations

from typing import Optional

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# 全局样式
# ---------------------------------------------------------------------------
plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "PingFang SC", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

# 活力色板
C_TEAL    = "#06b6d4"
C_PINK    = "#ec4899"
C_EMERALD = "#10b981"
C_ROSE    = "#f43f5e"
C_ORANGE  = "#f97316"
C_PURPLE  = "#8b5cf6"
C_SKY     = "#38bdf8"
C_AMBER   = "#f59e0b"
C_SLATE   = "#94a3b8"

PALETTE = [C_TEAL, C_PINK, C_EMERALD, C_ORANGE, C_PURPLE, C_SKY, C_AMBER, C_ROSE]


def _rounded_barh(ax, y_positions, widths, *, height=0.6, color="#06b6d4",
                   pad=0.02, rounding=0.12):
    """画水平圆角柱状图。"""
    for y, w in zip(y_positions, widths):
        if w == 0:
            continue
        x0 = min(0, w)
        box_w = abs(w)
        fancy = mpatches.FancyBboxPatch(
            (x0, y - height / 2), box_w, height,
            boxstyle=mpatches.BoxStyle.Round(pad=pad, rounding_size=rounding),
            facecolor=color, edgecolor="white", linewidth=0.5, alpha=0.85,
        )
        ax.add_patch(fancy)
    ax.autoscale()


def _clean_style(ax: plt.Axes) -> None:
    """白底 + 去掉上右边框 + 淡网格。"""
    ax.set_facecolor("white")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#cbd5e1")
    ax.spines["bottom"].set_color("#cbd5e1")
    ax.tick_params(colors="#64748b", labelsize=9)
    ax.grid(axis="y", color="#f1f5f9", linewidth=0.8)
    ax.set_axisbelow(True)


# ===================================================================
# Chapter 1  大盘全景
# ===================================================================

def plot_monthly_return_violin(daily_df: pd.DataFrame) -> plt.Figure:
    """图3: 月度收益率分布小提琴图。"""
    df = daily_df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df["month"] = df["date"].dt.to_period("M").astype(str)

    monthly = (
        df.groupby(["stock_code", "month"])
        .agg(month_return=("pct_change", "sum"))
        .reset_index()
    )
    months = sorted(monthly["month"].unique())
    data = [monthly[monthly["month"] == m]["month_return"].dropna().values for m in months]

    fig, ax = plt.subplots(figsize=(12, 5), facecolor="white")
    parts = ax.violinplot(data, positions=range(len(months)), showmeans=True, showmedians=True)
    for idx, pc in enumerate(parts["bodies"]):
        pc.set_facecolor(PALETTE[idx % len(PALETTE)])
        pc.set_edgecolor("white")
        pc.set_alpha(0.65)
    for key in ("cmeans", "cmedians", "cmins", "cmaxes", "cbars"):
        if key in parts:
            parts[key].set_color(C_SLATE)
            parts[key].set_linewidth(0.8)
    ax.set_xticks(range(len(months)))
    ax.set_xticklabels(months, rotation=30)
    ax.set_ylabel("月度累计涨跌幅 (%)")
    ax.set_title("中证2000成分股 月度收益率分布", fontsize=13, fontweight="bold", color="#334155")
    ax.axhline(0, color=C_SLATE, linewidth=0.5, linestyle="--")
    _clean_style(ax)
    fig.tight_layout()
    return fig


def plot_top_bottom_returns(features_df: pd.DataFrame, n: int = 20) -> plt.Figure:
    """图4: 累计收益率 Top/Bottom 柱状图。"""
    df = features_df[["stock_code", "cum_return"]].dropna().copy()
    if "stock_name" in features_df.columns:
        df["stock_name"] = features_df["stock_name"]
        df["label"] = df["stock_code"] + " " + df["stock_name"].fillna("")
    else:
        df["label"] = df["stock_code"]

    top = df.nlargest(n, "cum_return")
    bottom = df.nsmallest(n, "cum_return")
    combined = pd.concat([top.iloc[::-1], bottom])

    colors = [C_PINK if v >= 0 else C_TEAL for v in combined["cum_return"]]

    fig, ax = plt.subplots(figsize=(10, 12), facecolor="white")
    for i, (_, row) in enumerate(combined.iterrows()):
        _rounded_barh(ax, [i], [row["cum_return"]], height=0.65, color=colors[i])
    ax.set_yticks(range(len(combined)))
    ax.set_yticklabels(combined["label"], fontsize=7)
    ax.set_xlabel("累计收益率 (%)")
    ax.set_title(f"收益率 Top{n} & Bottom{n}", fontsize=13, fontweight="bold", color="#334155")
    ax.axvline(0, color=C_SLATE, linewidth=0.5)
    _clean_style(ax)
    ax.grid(axis="x", color="#f1f5f9", linewidth=0.8)
    fig.tight_layout()
    return fig


# ===================================================================
# Chapter 2  行业轮动
# ===================================================================

def plot_industry_return_bar(features_df: pd.DataFrame) -> plt.Figure:
    """图7: 行业累计收益率排行柱状图。"""
    if "industry" not in features_df.columns:
        fig, ax = plt.subplots(facecolor="white")
        ax.text(0.5, 0.5, "缺少行业数据", ha="center", va="center", color=C_SLATE)
        return fig

    ind_ret = features_df.groupby("industry")["cum_return"].mean().sort_values(ascending=True)
    colors = [C_PINK if v >= 0 else C_TEAL for v in ind_ret]

    fig, ax = plt.subplots(figsize=(10, max(6, len(ind_ret) * 0.3)), facecolor="white")
    for i, (ind, v) in enumerate(ind_ret.items()):
        _rounded_barh(ax, [i], [v], height=0.6, color=colors[i])
    ax.set_yticks(range(len(ind_ret)))
    ax.set_yticklabels(ind_ret.index, fontsize=8)
    ax.set_xlabel("平均累计收益率 (%)")
    ax.set_title("各行业平均收益率", fontsize=13, fontweight="bold", color="#334155")
    ax.axvline(0, color=C_SLATE, linewidth=0.5)
    _clean_style(ax)
    ax.grid(axis="x", color="#f1f5f9", linewidth=0.8)
    fig.tight_layout()
    return fig


def plot_industry_risk_return_bubble(features_df: pd.DataFrame) -> plt.Figure:
    """图9: 行业收益-波动气泡图。"""
    if "industry" not in features_df.columns:
        fig, ax = plt.subplots(facecolor="white")
        ax.text(0.5, 0.5, "缺少行业数据", ha="center", va="center", color=C_SLATE)
        return fig

    agg = features_df.groupby("industry").agg(
        avg_return=("cum_return", "mean"),
        avg_vol=("annual_volatility", "mean"),
        count=("stock_code", "count"),
    ).reset_index()

    fig, ax = plt.subplots(figsize=(10, 7), facecolor="white")
    colors = [PALETTE[i % len(PALETTE)] for i in range(len(agg))]
    ax.scatter(
        agg["avg_vol"], agg["avg_return"],
        s=agg["count"] * 3.5,
        c=colors, alpha=0.6, edgecolors="white", linewidth=0.8,
    )
    for _, row in agg.iterrows():
        ax.annotate(row["industry"], (row["avg_vol"], row["avg_return"]),
                     fontsize=7, ha="center", va="bottom", color="#475569")
    ax.set_xlabel("平均年化波动率 (%)")
    ax.set_ylabel("平均累计收益率 (%)")
    ax.set_title("行业 风险-收益 气泡图", fontsize=13, fontweight="bold", color="#334155")
    ax.axhline(0, color=C_SLATE, linewidth=0.5, linestyle="--")
    _clean_style(ax)
    fig.tight_layout()
    return fig


# ===================================================================
# Chapter 3  风险与收益
# ===================================================================

def plot_volatility_vs_return(
    features_df: pd.DataFrame,
    color_col: Optional[str] = None,
) -> plt.Figure:
    """图10: 波动率 vs 收益率散点图。"""
    fig, ax = plt.subplots(figsize=(10, 7), facecolor="white")

    if color_col and color_col in features_df.columns:
        groups = sorted(features_df[color_col].unique())
        for i, g in enumerate(groups):
            mask = features_df[color_col] == g
            ax.scatter(
                features_df.loc[mask, "annual_volatility"],
                features_df.loc[mask, "cum_return"],
                s=12, alpha=0.5, label=str(g),
                color=PALETTE[i % len(PALETTE)], edgecolors="none",
            )
        ax.legend(fontsize=8, loc="upper left", ncol=2, framealpha=0.9, edgecolor="#e2e8f0")
    else:
        ax.scatter(
            features_df["annual_volatility"],
            features_df["cum_return"],
            s=12, alpha=0.45, c=C_TEAL, edgecolors="none",
        )

    ax.set_xlabel("年化波动率 (%)")
    ax.set_ylabel("累计收益率 (%)")
    ax.set_title("风险-收益 散点图", fontsize=13, fontweight="bold", color="#334155")
    ax.axhline(0, color=C_SLATE, linewidth=0.5, linestyle="--")
    _clean_style(ax)
    fig.tight_layout()
    return fig


def plot_max_drawdown_hist(features_df: pd.DataFrame) -> plt.Figure:
    """图11: 最大回撤分布直方图+KDE。"""
    dd = features_df["max_drawdown"].dropna()

    fig, ax = plt.subplots(figsize=(10, 5), facecolor="white")
    ax.hist(dd, bins=50, density=True, alpha=0.55, color=C_TEAL, edgecolor="white", linewidth=0.5)
    try:
        from scipy.stats import gaussian_kde
        x = np.linspace(dd.min(), dd.max(), 200)
        kde = gaussian_kde(dd)
        ax.plot(x, kde(x), color=C_PINK, linewidth=2)
    except ImportError:
        pass
    ax.set_xlabel("最大回撤 (%)")
    ax.set_ylabel("密度")
    ax.set_title("最大回撤分布", fontsize=13, fontweight="bold", color="#334155")
    _clean_style(ax)
    fig.tight_layout()
    return fig


def plot_skew_kurtosis(features_df: pd.DataFrame) -> plt.Figure:
    """图12: 收益偏度 vs 峰度散点图。"""
    fig, ax = plt.subplots(figsize=(9, 6), facecolor="white")
    ax.scatter(
        features_df["return_skew"],
        features_df["return_kurtosis"],
        s=12, alpha=0.45, c=C_PURPLE, edgecolors="none",
    )
    ax.set_xlabel("收益率偏度")
    ax.set_ylabel("收益率峰度")
    ax.set_title("偏度-峰度 散点图", fontsize=13, fontweight="bold", color="#334155")
    ax.axvline(0, color=C_SLATE, linewidth=0.5, linestyle="--")
    _clean_style(ax)
    fig.tight_layout()
    return fig


def plot_monthly_drawdown_top(daily_df: pd.DataFrame, n: int = 10) -> plt.Figure:
    """图13: 月度最大回撤 Top N。"""
    df = daily_df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df["month"] = df["date"].dt.to_period("M").astype(str)

    def _month_drawdown(g):
        cum = (1 + g["pct_change"] / 100).cumprod()
        running_max = cum.cummax()
        dd = ((cum - running_max) / running_max * 100).min()
        return dd

    mdd = (
        df.groupby(["stock_code", "month"])
        .apply(_month_drawdown, include_groups=False)
        .reset_index(name="drawdown")
    )
    worst = mdd.nsmallest(n, "drawdown")
    worst["label"] = worst["stock_code"] + " (" + worst["month"] + ")"

    fig, ax = plt.subplots(figsize=(10, 5), facecolor="white")
    for i, (_, row) in enumerate(worst.iterrows()):
        _rounded_barh(ax, [i], [row["drawdown"]], height=0.55, color=C_ROSE)
    ax.set_yticks(range(len(worst)))
    ax.set_yticklabels(worst["label"], fontsize=8)
    ax.set_xlabel("最大回撤 (%)")
    ax.set_title(f"月度最大回撤 Top{n}", fontsize=13, fontweight="bold", color="#334155")
    _clean_style(ax)
    ax.grid(axis="x", color="#f1f5f9", linewidth=0.8)
    fig.tight_layout()
    return fig


# ===================================================================
# Chapter 4  量价与异动
# ===================================================================

def plot_turnover_vs_return(features_df: pd.DataFrame) -> plt.Figure:
    """图14: 换手率 vs 收益率散点图。"""
    fig, ax = plt.subplots(figsize=(10, 7), facecolor="white")
    ax.scatter(
        features_df["avg_turnover"],
        features_df["cum_return"],
        s=12, alpha=0.45, c=C_TEAL, edgecolors="none",
    )
    ax.set_xlabel("日均换手率 (%)")
    ax.set_ylabel("累计收益率 (%)")
    ax.set_title("换手率-收益 散点图", fontsize=13, fontweight="bold", color="#334155")
    ax.axhline(0, color=C_SLATE, linewidth=0.5, linestyle="--")
    _clean_style(ax)
    fig.tight_layout()
    return fig


def plot_limit_up_down_top(features_df: pd.DataFrame, n: int = 20) -> plt.Figure:
    """图15: 涨停/跌停次数 Top N。"""
    df = features_df[["stock_code", "limit_up_count", "limit_down_count"]].copy()
    if "stock_name" in features_df.columns:
        df["stock_name"] = features_df["stock_name"]

    df["total"] = df["limit_up_count"] + df["limit_down_count"]
    top = df.nlargest(n, "total").sort_values("total", ascending=True)

    if "stock_name" in top.columns:
        labels = top["stock_code"] + " " + top["stock_name"].fillna("")
    else:
        labels = top["stock_code"]

    fig, ax = plt.subplots(figsize=(10, 8), facecolor="white")
    y = list(range(len(top)))
    for i, (_, row) in enumerate(top.iterrows()):
        _rounded_barh(ax, [i - 0.17], [row["limit_up_count"]], height=0.34, color=C_PINK, rounding=0.08)
        _rounded_barh(ax, [i + 0.17], [-row["limit_down_count"]], height=0.34, color=C_TEAL, rounding=0.08)
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=7)
    ax.set_xlabel("次数")
    ax.set_title(f"涨停/跌停次数 Top{n}", fontsize=13, fontweight="bold", color="#334155")
    legend_patches = [
        mpatches.Patch(facecolor=C_PINK, label="涨停", alpha=0.85),
        mpatches.Patch(facecolor=C_TEAL, label="跌停", alpha=0.85),
    ]
    ax.legend(handles=legend_patches, fontsize=9, framealpha=0.9, edgecolor="#e2e8f0")
    ax.axvline(0, color=C_SLATE, linewidth=0.5)
    _clean_style(ax)
    ax.grid(axis="x", color="#f1f5f9", linewidth=0.8)
    fig.tight_layout()
    return fig


def plot_price_volume_corr_hist(features_df: pd.DataFrame) -> plt.Figure:
    """图16: 价量相关系数分布。"""
    pv = features_df["price_volume_corr"].dropna()

    fig, ax = plt.subplots(figsize=(10, 5), facecolor="white")
    ax.hist(pv, bins=50, density=True, alpha=0.55, color=C_SKY, edgecolor="white", linewidth=0.5)
    try:
        from scipy.stats import gaussian_kde
        x = np.linspace(pv.min(), pv.max(), 200)
        kde = gaussian_kde(pv)
        ax.plot(x, kde(x), color=C_PINK, linewidth=2)
    except ImportError:
        pass
    ax.axvline(0, color=C_SLATE, linewidth=0.5, linestyle="--")
    ax.set_xlabel("价量相关系数")
    ax.set_ylabel("密度")
    ax.set_title("价量相关系数分布", fontsize=13, fontweight="bold", color="#334155")
    _clean_style(ax)
    fig.tight_layout()
    return fig


# ===================================================================
# Chapter 5  聚类画像
# ===================================================================

def plot_pca_scatter(pca_df: pd.DataFrame) -> plt.Figure:
    """图18: PCA 二维散点图。"""
    fig, ax = plt.subplots(figsize=(10, 8), facecolor="white")

    if "cluster_name" in pca_df.columns:
        groups = sorted(pca_df["cluster_name"].unique())
        for i, g in enumerate(groups):
            mask = pca_df["cluster_name"] == g
            ax.scatter(
                pca_df.loc[mask, "pc1"],
                pca_df.loc[mask, "pc2"],
                s=14, alpha=0.55, label=g,
                color=PALETTE[i % len(PALETTE)], edgecolors="white", linewidth=0.3,
            )
        ax.legend(fontsize=8, loc="best", framealpha=0.9, edgecolor="#e2e8f0")
    else:
        ax.scatter(pca_df["pc1"], pca_df["pc2"], s=12, alpha=0.4, c=C_TEAL, edgecolors="none")

    ax.set_xlabel("PC1")
    ax.set_ylabel("PC2")
    ax.set_title("PCA 聚类散点图", fontsize=13, fontweight="bold", color="#334155")
    _clean_style(ax)
    fig.tight_layout()
    return fig


def plot_elbow_silhouette(k_search_df: pd.DataFrame) -> plt.Figure:
    """图21: 肘部法则 + 轮廓系数双Y轴图。"""
    fig, ax1 = plt.subplots(figsize=(9, 5), facecolor="white")

    ks = k_search_df["k"]
    ax1.plot(ks, k_search_df["inertia"], "o-", color=C_TEAL, linewidth=2,
             markersize=6, markeredgecolor="white", markeredgewidth=1, label="Inertia")
    ax1.set_xlabel("聚类数 K")
    ax1.set_ylabel("Inertia", color=C_TEAL)
    ax1.tick_params(axis="y", labelcolor=C_TEAL)

    ax2 = ax1.twinx()
    ax2.plot(ks, k_search_df["silhouette"], "s-", color=C_PINK, linewidth=2,
             markersize=6, markeredgecolor="white", markeredgewidth=1, label="Silhouette")
    ax2.set_ylabel("轮廓系数", color=C_PINK)
    ax2.tick_params(axis="y", labelcolor=C_PINK)

    ax1.set_title("肘部法则 & 轮廓系数", fontsize=13, fontweight="bold", color="#334155")
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="center right",
               framealpha=0.9, edgecolor="#e2e8f0")
    for sp in ["top", "left", "bottom"]:
        ax1.spines[sp].set_color("#cbd5e1") if sp != "top" else ax1.spines[sp].set_visible(False)
    ax2.spines["top"].set_visible(False)
    ax2.spines["right"].set_color("#cbd5e1")
    ax1.grid(axis="y", color="#f1f5f9", linewidth=0.8)
    fig.tight_layout()
    return fig


def plot_cluster_boxplot(
    features_df: pd.DataFrame,
    feature_cols: Optional[list[str]] = None,
) -> plt.Figure:
    """图22: 聚类特征分组箱线图。"""
    if feature_cols is None:
        feature_cols = [
            "cum_return", "annual_volatility", "max_drawdown",
            "avg_turnover", "avg_amplitude", "price_volume_corr",
        ]
    feature_cols = [c for c in feature_cols if c in features_df.columns]

    if "cluster_name" not in features_df.columns:
        features_df = features_df.copy()
        features_df["cluster_name"] = features_df.get("cluster_id", 0).astype(str)

    n = len(feature_cols)
    ncols = 3
    nrows = (n + ncols - 1) // ncols
    fig, axes = plt.subplots(nrows, ncols, figsize=(14, 4 * nrows), facecolor="white")
    axes = axes.flatten() if n > 1 else [axes]

    clusters = sorted(features_df["cluster_name"].unique())
    for i, col in enumerate(feature_cols):
        ax = axes[i]
        data = [features_df[features_df["cluster_name"] == c][col].dropna() for c in clusters]
        bp = ax.boxplot(
            data, labels=clusters, patch_artist=True,
            boxprops=dict(linewidth=0.8, edgecolor="#cbd5e1"),
            whiskerprops=dict(color=C_SLATE, linewidth=0.8),
            capprops=dict(color=C_SLATE, linewidth=0.8),
            medianprops=dict(color="#334155", linewidth=1.5),
            flierprops=dict(marker="o", markersize=3, alpha=0.4, markerfacecolor=C_SLATE),
        )
        for j, patch in enumerate(bp["boxes"]):
            patch.set_facecolor(PALETTE[j % len(PALETTE)])
            patch.set_alpha(0.6)
        ax.set_title(col, fontsize=10, color="#475569")
        ax.tick_params(axis="x", rotation=30, labelsize=7)
        _clean_style(ax)

    for i in range(len(feature_cols), len(axes)):
        axes[i].set_visible(False)

    fig.suptitle("各聚类关键特征分布", fontsize=13, fontweight="bold", color="#334155")
    fig.tight_layout()
    return fig
