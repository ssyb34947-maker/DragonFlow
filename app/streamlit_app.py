"""
DragonFlow - 中证2000成分股画像分析 Streamlit 仪表盘

多页面交互式看板，包含 6 个故事章节、24 张图表。
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # 非交互后端，避免 Streamlit 线程问题
import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

# ------------------------------------------------------------------
# 项目路径设置
# ------------------------------------------------------------------
_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC = _REPO_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from dragonflow.viz.charts_matplotlib import (
    plot_monthly_return_violin,       # fig3
    plot_top_bottom_returns,          # fig4
    plot_industry_return_bar,         # fig7
    plot_industry_risk_return_bubble, # fig9
    plot_volatility_vs_return,        # fig10
    plot_max_drawdown_hist,           # fig11
    plot_skew_kurtosis,               # fig12
    plot_monthly_drawdown_top,        # fig13
    plot_turnover_vs_return,          # fig14
    plot_limit_up_down_top,           # fig15
    plot_price_volume_corr_hist,      # fig16
    plot_pca_scatter,                 # fig18
    plot_elbow_silhouette,            # fig21
    plot_cluster_boxplot,             # fig22
)
from dragonflow.viz.charts_pyecharts import (
    chart_index_line,                 # fig1
    chart_daily_up_down_bar,          # fig2
    chart_daily_amount_area,          # fig5
    chart_industry_monthly_heatmap,   # fig6
    chart_industry_amount_river,      # fig8
    chart_anomaly_industry_heatmap,   # fig17
    chart_cluster_radar,              # fig19
    chart_cluster_industry_sankey,    # fig20
    chart_kline,                      # fig23
    chart_multi_stock_lines,          # fig24
)
from dragonflow.utils.io import resolve_path

# ------------------------------------------------------------------
# 页面基本配置
# ------------------------------------------------------------------
st.set_page_config(
    page_title="DragonFlow - 中证2000画像分析",
    page_icon="🐉",
    layout="wide",
)


# ==================================================================
# 数据加载（全部使用 st.cache_data 缓存）
# ==================================================================

@st.cache_data
def load_daily() -> pd.DataFrame | None:
    path = resolve_path("data/processed/stock_daily_csi2000_qfq_20260101_20260531_clean.csv")
    if not path.exists():
        return None
    return pd.read_csv(path, dtype={"stock_code": str}, encoding="utf-8-sig")


@st.cache_data
def load_index_daily() -> pd.DataFrame | None:
    path = resolve_path("data/processed/index_daily_932000_20260101_20260531.csv")
    if not path.exists():
        return None
    return pd.read_csv(path, encoding="utf-8-sig")


@st.cache_data
def load_features() -> pd.DataFrame | None:
    path = resolve_path("data/processed/stock_features.csv")
    if not path.exists():
        return None
    return pd.read_csv(path, dtype={"stock_code": str}, encoding="utf-8-sig")


@st.cache_data
def load_clusters() -> pd.DataFrame | None:
    path = resolve_path("data/processed/stock_clusters.csv")
    if not path.exists():
        return None
    return pd.read_csv(path, dtype={"stock_code": str}, encoding="utf-8-sig")


@st.cache_data
def load_pca() -> pd.DataFrame | None:
    path = resolve_path("data/processed/pca_2d.csv")
    if not path.exists():
        return None
    return pd.read_csv(path, dtype={"stock_code": str}, encoding="utf-8-sig")


@st.cache_data
def load_k_search() -> pd.DataFrame | None:
    path = resolve_path("data/processed/k_search.csv")
    if not path.exists():
        return None
    return pd.read_csv(path, encoding="utf-8-sig")


# ==================================================================
# 工具函数
# ==================================================================

def render_pyecharts(chart, height: int = 500) -> None:
    """将 Pyecharts 图表对象渲染为内嵌 HTML 展示。"""
    html = chart.render_embed()
    components.html(html, height=height, scrolling=True)


def show_matplotlib(fig: plt.Figure) -> None:
    """展示 Matplotlib 图并立即关闭，释放内存。"""
    st.pyplot(fig)
    plt.close(fig)


# ==================================================================
# Chapter 1: 大盘全景
# ==================================================================

def chapter_market_overview() -> None:
    st.header("第一章 大盘全景")
    st.markdown(
        "本章从指数走势、涨跌家数、月度收益分布、个股涨跌排行和成交额走势五个维度，"
        "勾勒 2026 年 1-5 月中证 2000 市场的整体面貌。"
    )

    daily = load_daily()
    index_daily = load_index_daily()
    features = load_features()

    # --- 图1: 指数走势 ---
    st.subheader("图1: 中证2000指数走势")
    st.markdown("展示指数收盘价及 MA5/MA20 均线，快速判断趋势方向与阶段。")
    if index_daily is not None:
        render_pyecharts(chart_index_line(index_daily), height=500)
    else:
        st.warning("缺少指数日线数据 (index_daily_932000_20260101_20260531.csv)")

    # --- 图2: 涨跌家数 ---
    st.subheader("图2: 每日涨跌家数")
    st.markdown("堆叠柱状图展示每日上涨、平盘、下跌的股票数量，反映市场情绪强弱。")
    if daily is not None:
        render_pyecharts(chart_daily_up_down_bar(daily), height=450)
    else:
        st.warning("缺少日线行情数据")

    # --- 图3: 月度收益率小提琴图 ---
    st.subheader("图3: 月度收益率分布")
    st.markdown("小提琴图直观展示各月成分股收益率的分布形态和离散程度。")
    if daily is not None:
        fig = plot_monthly_return_violin(daily)
        show_matplotlib(fig)
    else:
        st.warning("缺少日线行情数据")

    # --- 图4: 累计收益 Top/Bottom ---
    st.subheader("图4: 累计收益率 Top/Bottom 20")
    st.markdown("双向柱状图展示表现最好与最差的个股，一览极端表现。")
    if features is not None:
        fig = plot_top_bottom_returns(features, n=20)
        show_matplotlib(fig)
    else:
        st.warning("缺少特征数据 (stock_features.csv)")

    # --- 图5: 全市场日成交额 ---
    st.subheader("图5: 全市场日成交额走势")
    st.markdown("面积图展示全部成分股日成交额合计，反映资金活跃度变化。")
    if daily is not None:
        render_pyecharts(chart_daily_amount_area(daily), height=450)
    else:
        st.warning("缺少日线行情数据")


# ==================================================================
# Chapter 2: 行业轮动
# ==================================================================

def chapter_industry_rotation() -> None:
    st.header("第二章 行业轮动")
    st.markdown(
        "本章聚焦行业层面的收益、成交和风险差异，揭示行业间的强弱切换与资金迁移。"
    )

    daily = load_daily()
    features = load_features()

    # --- 图6: 行业月度涨跌幅热力图 ---
    st.subheader("图6: 行业月度涨跌幅热力图")
    st.markdown("热力图直观展示各行业每月平均涨跌幅，颜色越红涨幅越大，越绿跌幅越深。")
    if daily is not None and features is not None:
        render_pyecharts(chart_industry_monthly_heatmap(daily, features), height=650)
    else:
        st.warning("缺少日线或特征数据")

    # --- 图7: 行业收益排行 ---
    st.subheader("图7: 行业累计收益率排行")
    st.markdown("柱状图排列各行业的平均累计收益率，快速识别强/弱势行业。")
    if features is not None:
        fig = plot_industry_return_bar(features)
        show_matplotlib(fig)
    else:
        st.warning("缺少特征数据 (stock_features.csv)")

    # --- 图8: 行业成交额河流图 ---
    st.subheader("图8: Top10 行业成交额河流图")
    st.markdown("河流图展示前 10 大行业的日成交额演变，观察资金在行业间的流转。")
    if daily is not None and features is not None:
        render_pyecharts(chart_industry_amount_river(daily, features, top_n=10), height=550)
    else:
        st.warning("缺少日线或特征数据")

    # --- 图9: 行业风险-收益气泡图 ---
    st.subheader("图9: 行业风险-收益气泡图")
    st.markdown("气泡大小代表行业内股票数量，横轴为波动率，纵轴为收益率，综合衡量行业性价比。")
    if features is not None:
        fig = plot_industry_risk_return_bubble(features)
        show_matplotlib(fig)
    else:
        st.warning("缺少特征数据 (stock_features.csv)")


# ==================================================================
# Chapter 3: 风险与收益
# ==================================================================

def chapter_risk_return() -> None:
    st.header("第三章 风险与收益")
    st.markdown(
        "本章从全局视角审视个股的风险收益关系，包括波动率、最大回撤、"
        "收益分布形态（偏度峰度）以及月度极端回撤事件。"
    )

    daily = load_daily()
    features = load_features()

    # --- 图10: 波动率 vs 收益率 ---
    st.subheader("图10: 波动率 vs 收益率散点图")
    st.markdown("每个点代表一只股票，揭示风险与回报之间是否存在正向补偿关系。")
    if features is not None:
        fig = plot_volatility_vs_return(features)
        show_matplotlib(fig)
    else:
        st.warning("缺少特征数据 (stock_features.csv)")

    # --- 图11: 最大回撤分布 ---
    st.subheader("图11: 最大回撤分布")
    st.markdown("直方图 + KDE 密度曲线展示全市场最大回撤的分布，关注尾部风险。")
    if features is not None:
        fig = plot_max_drawdown_hist(features)
        show_matplotlib(fig)
    else:
        st.warning("缺少特征数据 (stock_features.csv)")

    # --- 图12: 偏度-峰度散点图 ---
    st.subheader("图12: 偏度-峰度散点图")
    st.markdown("散点图展示各股票的收益率偏度与峰度，判断收益分布是否存在厚尾或不对称特征。")
    if features is not None:
        fig = plot_skew_kurtosis(features)
        show_matplotlib(fig)
    else:
        st.warning("缺少特征数据 (stock_features.csv)")

    # --- 图13: 月度最大回撤 Top10 ---
    st.subheader("图13: 月度最大回撤 Top 10")
    st.markdown("筛选出月度维度回撤最惨烈的股票-月份组合，定位极端风险事件。")
    if daily is not None:
        fig = plot_monthly_drawdown_top(daily, n=10)
        show_matplotlib(fig)
    else:
        st.warning("缺少日线行情数据")


# ==================================================================
# Chapter 4: 量价与异动
# ==================================================================

def chapter_volume_price_anomaly() -> None:
    st.header("第四章 量价与异动")
    st.markdown(
        "本章探索换手率、涨跌停、价量相关性等量价特征，并从行业层面汇总异动信号。"
    )

    features = load_features()

    # --- 图14: 换手率 vs 收益率 ---
    st.subheader("图14: 换手率 vs 收益率散点图")
    st.markdown("观察日均换手率与累计收益率之间的关联，高换手是否意味着高回报？")
    if features is not None:
        fig = plot_turnover_vs_return(features)
        show_matplotlib(fig)
    else:
        st.warning("缺少特征数据 (stock_features.csv)")

    # --- 图15: 涨停/跌停 Top20 ---
    st.subheader("图15: 涨停/跌停次数 Top 20")
    st.markdown("双向柱状图展示涨停和跌停次数最多的个股，识别高波动或题材活跃标的。")
    if features is not None:
        fig = plot_limit_up_down_top(features, n=20)
        show_matplotlib(fig)
    else:
        st.warning("缺少特征数据 (stock_features.csv)")

    # --- 图16: 价量相关系数分布 ---
    st.subheader("图16: 价量相关系数分布")
    st.markdown("分布图展示各股票价格与成交量的相关系数，正值代表放量上涨模式。")
    if features is not None:
        fig = plot_price_volume_corr_hist(features)
        show_matplotlib(fig)
    else:
        st.warning("缺少特征数据 (stock_features.csv)")

    # --- 图17: 异动特征行业热力图 ---
    st.subheader("图17: 各行业异动特征热力图")
    st.markdown("从大阳线、大阴线、涨停、跌停四个维度比较各行业的异动频率。")
    if features is not None:
        render_pyecharts(chart_anomaly_industry_heatmap(features), height=650)
    else:
        st.warning("缺少特征数据 (stock_features.csv)")


# ==================================================================
# Chapter 5: 聚类画像
# ==================================================================

def chapter_cluster_profile() -> None:
    st.header("第五章 聚类画像")
    st.markdown(
        "本章利用 K-Means 聚类对全部成分股进行分群，从 PCA 降维散点、雷达图、"
        "桑基图、肘部法则和箱线图等角度全方位解读聚类结果。"
    )

    features = load_features()
    clusters = load_clusters()
    pca_df = load_pca()
    k_search = load_k_search()

    # --- 图18: PCA 散点图 ---
    st.subheader("图18: PCA 二维散点图")
    st.markdown("将高维特征降至二维，用不同颜色标注聚类簇，直观展示分群效果。")
    if pca_df is not None:
        fig = plot_pca_scatter(pca_df)
        show_matplotlib(fig)
    else:
        st.warning("缺少 PCA 数据 (pca_2d.csv)")

    # --- 图19: 聚类雷达图 ---
    st.subheader("图19: 聚类特征雷达图")
    st.markdown("雷达图叠加各聚类簇在关键特征上的标准化均值，快速对比簇间差异。")
    if clusters is not None:
        render_pyecharts(chart_cluster_radar(clusters), height=650)
    else:
        st.warning("缺少聚类数据 (stock_clusters.csv)")

    # --- 图20: 聚类 × 行业桑基图 ---
    st.subheader("图20: 聚类 x 行业桑基图")
    st.markdown("桑基图展示各聚类簇与行业之间的对应关系，揭示行业是否与聚类高度相关。")
    if clusters is not None:
        render_pyecharts(chart_cluster_industry_sankey(clusters), height=750)
    else:
        st.warning("缺少聚类数据 (stock_clusters.csv)")

    # --- 图21: 肘部法则 + 轮廓系数 ---
    st.subheader("图21: 肘部法则 & 轮廓系数")
    st.markdown("双 Y 轴图展示不同 K 值下的 Inertia 和轮廓系数，辅助选择最佳聚类数。")
    if k_search is not None:
        fig = plot_elbow_silhouette(k_search)
        show_matplotlib(fig)
    else:
        st.warning("缺少 K 值搜索数据 (k_search.csv)")

    # --- 图22: 聚类特征箱线图 ---
    st.subheader("图22: 聚类关键特征分组箱线图")
    st.markdown("分聚类展示各关键特征的箱线图，对比簇间分布差异和离群值。")
    if clusters is not None:
        fig = plot_cluster_boxplot(clusters)
        show_matplotlib(fig)
    else:
        st.warning("缺少聚类数据 (stock_clusters.csv)")


# ==================================================================
# Chapter 6: 典型个股
# ==================================================================

def chapter_representative_stocks() -> None:
    st.header("第六章 典型个股")
    st.markdown(
        "本章选取各聚类簇的代表个股，展示 K 线走势和多股归一化对比，"
        "帮助理解不同类型股票的实际行情表现。"
    )

    daily = load_daily()
    clusters = load_clusters()
    features = load_features()

    if daily is None:
        st.warning("缺少日线行情数据")
        return
    if clusters is None and features is None:
        st.warning("缺少聚类或特征数据")
        return

    # 使用聚类数据（如有），否则降级到特征数据
    ref_df = clusters if clusters is not None else features

    # 确定聚类标签列
    if "cluster_name" in ref_df.columns:
        cluster_col = "cluster_name"
    elif "cluster_id" in ref_df.columns:
        cluster_col = "cluster_id"
    else:
        st.warning("数据中不包含聚类标签列")
        return

    cluster_labels = sorted(ref_df[cluster_col].unique(), key=str)

    # 为每个聚类选取一个代表股（取累计收益率最接近簇均值的股票）
    representatives: dict[str, tuple[str, str]] = {}  # cluster -> (stock_code, stock_name)
    for cl in cluster_labels:
        sub = ref_df[ref_df[cluster_col] == cl].copy()
        if sub.empty:
            continue
        if "cum_return" in sub.columns:
            mean_ret = sub["cum_return"].mean()
            idx = (sub["cum_return"] - mean_ret).abs().idxmin()
        else:
            idx = sub.index[0]
        code = sub.loc[idx, "stock_code"]
        name = sub.loc[idx, "stock_name"] if "stock_name" in sub.columns else ""
        representatives[str(cl)] = (str(code), str(name) if pd.notna(name) else "")

    # --- 图23: K 线图（交互选择聚类） ---
    st.subheader("图23: 代表股 K 线图")
    st.markdown("从下拉框选择一个聚类簇，查看该簇代表股的 K 线走势。")

    selected_cluster = st.selectbox(
        "选择聚类",
        options=list(representatives.keys()),
        format_func=lambda x: f"{x}  ({representatives[x][0]} {representatives[x][1]})",
    )

    if selected_cluster and selected_cluster in representatives:
        code, name = representatives[selected_cluster]
        render_pyecharts(chart_kline(daily, code, name), height=550)

    # --- 图24: 多股归一化走势对比 ---
    st.subheader("图24: 各聚类代表股走势对比")
    st.markdown("将各簇代表股价格归一化至首日 = 100 进行叠加对比，揭示不同类型股票的走势分化。")

    all_codes = [v[0] for v in representatives.values()]
    name_map = {v[0]: v[1] for v in representatives.values()}

    if all_codes:
        render_pyecharts(chart_multi_stock_lines(daily, all_codes, stock_names=name_map), height=550)
    else:
        st.warning("未找到代表股数据")


# ==================================================================
# 主入口 & 侧边栏导航
# ==================================================================

def main() -> None:
    st.title("DragonFlow - 中证2000成分股画像分析")
    st.caption("数据区间: 2026-01-01 至 2026-05-31 | 前复权日线行情")

    chapters = {
        "大盘全景": chapter_market_overview,
        "行业轮动": chapter_industry_rotation,
        "风险与收益": chapter_risk_return,
        "量价与异动": chapter_volume_price_anomaly,
        "聚类画像": chapter_cluster_profile,
        "典型个股": chapter_representative_stocks,
    }

    st.sidebar.title("章节导航")
    choice = st.sidebar.radio("选择章节", list(chapters.keys()))

    # 调用选中章节的渲染函数
    chapters[choice]()

    # 侧边栏底部信息
    st.sidebar.markdown("---")
    st.sidebar.info("DragonFlow v0.1\n\n共 24 张图表，6 个故事章节。")


if __name__ == "__main__":
    main()
