"""Pyecharts 图表函数（交互式图表）。

每个函数返回一个 pyecharts Chart 对象，可调用 .render() 生成 HTML，
也可在 Jupyter / Streamlit 中展示。
"""
from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd

from pyecharts import options as opts
from pyecharts.charts import (
    Bar,
    Kline,
    Line,
    HeatMap,
    Radar,
    Sankey,
    ThemeRiver,
)
from pyecharts.commons.utils import JsCode

from pathlib import Path


def show_chart(chart, width: int = 1020, height: int = 520) -> None:
    """渲染 pyecharts 图表并在 Jupyter 中内嵌显示。

    使用 base64 data-URI iframe 方式嵌入完整 HTML，
    兼容 VS Code / JupyterLab / 经典 Notebook。
    """
    from IPython.display import display, HTML
    import base64, tempfile, os

    # 渲染到临时文件，获取完整独立 HTML
    tmp = tempfile.NamedTemporaryFile(suffix=".html", delete=False)
    tmp.close()
    chart.render(tmp.name)
    with open(tmp.name, "r", encoding="utf-8") as f:
        html_content = f.read()
    os.unlink(tmp.name)

    # base64 编码后通过 data URI 嵌入 iframe
    b64 = base64.b64encode(html_content.encode("utf-8")).decode("ascii")
    iframe = (
        f'<iframe src="data:text/html;base64,{b64}" '
        f'width="{width}" height="{height}" '
        f'frameborder="0" style="border:none;"></iframe>'
    )
    display(HTML(iframe))


# ===================================================================
# Chapter 1  大盘全景
# ===================================================================

def chart_index_line(index_daily: pd.DataFrame) -> Line:
    """图1: 中证2000指数走势 + MA5/MA20均线。"""
    df = index_daily.sort_values("date").copy()
    df["close"] = pd.to_numeric(df["close"], errors="coerce")
    df["ma5"] = df["close"].rolling(5).mean().round(2)
    df["ma20"] = df["close"].rolling(20).mean().round(2)

    dates = df["date"].tolist()
    close = df["close"].round(2).tolist()
    ma5 = df["ma5"].tolist()
    ma20 = df["ma20"].tolist()

    c = (
        Line(init_opts=opts.InitOpts(width="1000px", height="450px"))
        .add_xaxis(dates)
        .add_yaxis("收盘价", close, is_smooth=True,
                    linestyle_opts=opts.LineStyleOpts(width=2),
                    label_opts=opts.LabelOpts(is_show=False))
        .add_yaxis("MA5", ma5, is_smooth=True,
                    linestyle_opts=opts.LineStyleOpts(width=1, type_="dashed"),
                    label_opts=opts.LabelOpts(is_show=False))
        .add_yaxis("MA20", ma20, is_smooth=True,
                    linestyle_opts=opts.LineStyleOpts(width=1, type_="dashed"),
                    label_opts=opts.LabelOpts(is_show=False))
        .set_global_opts(
            title_opts=opts.TitleOpts(title="中证2000指数走势"),
            tooltip_opts=opts.TooltipOpts(trigger="axis"),
            datazoom_opts=[opts.DataZoomOpts(range_start=0, range_end=100)],
            yaxis_opts=opts.AxisOpts(is_scale=True),
            xaxis_opts=opts.AxisOpts(type_="category"),
        )
    )
    return c


def chart_daily_up_down_bar(daily_df: pd.DataFrame) -> Bar:
    """图2: 全市场每日涨跌家数堆叠柱状图。"""
    df = daily_df.copy()
    stats = df.groupby("date")["pct_change"].agg(
        up=lambda x: (x > 0).sum(),
        flat=lambda x: (x == 0).sum(),
        down=lambda x: (x < 0).sum(),
    ).reset_index().sort_values("date")

    dates = stats["date"].tolist()

    c = (
        Bar(init_opts=opts.InitOpts(width="1000px", height="400px"))
        .add_xaxis(dates)
        .add_yaxis("上涨", stats["up"].tolist(), stack="total",
                    itemstyle_opts=opts.ItemStyleOpts(color="#d62728"),
                    label_opts=opts.LabelOpts(is_show=False))
        .add_yaxis("平盘", stats["flat"].tolist(), stack="total",
                    itemstyle_opts=opts.ItemStyleOpts(color="#cccccc"),
                    label_opts=opts.LabelOpts(is_show=False))
        .add_yaxis("下跌", stats["down"].tolist(), stack="total",
                    itemstyle_opts=opts.ItemStyleOpts(color="#2ca02c"),
                    label_opts=opts.LabelOpts(is_show=False))
        .set_global_opts(
            title_opts=opts.TitleOpts(title="每日涨跌家数"),
            tooltip_opts=opts.TooltipOpts(trigger="axis"),
            datazoom_opts=[opts.DataZoomOpts(range_start=0, range_end=100)],
            yaxis_opts=opts.AxisOpts(name="家数"),
        )
    )
    return c


def chart_daily_amount_area(daily_df: pd.DataFrame) -> Line:
    """图5: 全市场日成交额走势面积图。"""
    df = daily_df.copy()
    total = (
        df.groupby("date")["amount"]
        .sum()
        .reset_index()
        .sort_values("date")
    )
    total["amount_yi"] = (total["amount"] / 1e8).round(2)  # 亿元

    c = (
        Line(init_opts=opts.InitOpts(width="1000px", height="400px"))
        .add_xaxis(total["date"].tolist())
        .add_yaxis(
            "成交额（亿元）",
            total["amount_yi"].tolist(),
            is_smooth=True,
            areastyle_opts=opts.AreaStyleOpts(opacity=0.3),
            label_opts=opts.LabelOpts(is_show=False),
        )
        .set_global_opts(
            title_opts=opts.TitleOpts(title="全市场日成交额"),
            tooltip_opts=opts.TooltipOpts(trigger="axis"),
            datazoom_opts=[opts.DataZoomOpts(range_start=0, range_end=100)],
            yaxis_opts=opts.AxisOpts(name="亿元", is_scale=True),
        )
    )
    return c


# ===================================================================
# Chapter 2  行业轮动
# ===================================================================

def chart_industry_monthly_heatmap(
    daily_df: pd.DataFrame,
    features_df: pd.DataFrame,
) -> HeatMap:
    """图6: 行业月度涨跌幅热力图。"""
    if "industry" not in features_df.columns:
        return HeatMap().set_global_opts(title_opts=opts.TitleOpts(title="缺少行业数据"))

    # 合入行业
    ind_map = features_df[["stock_code", "industry"]].drop_duplicates()
    df = daily_df.merge(ind_map, on="stock_code", how="left")
    df["date"] = pd.to_datetime(df["date"])
    df["month"] = df["date"].dt.to_period("M").astype(str)

    # 按行业+月份算平均涨跌幅
    agg = df.groupby(["industry", "month"])["pct_change"].mean().reset_index()
    agg["pct_change"] = agg["pct_change"].round(2)

    months = sorted(agg["month"].unique())
    industries = sorted(agg["industry"].unique())

    heat_data = []
    for _, row in agg.iterrows():
        x = months.index(row["month"])
        y = industries.index(row["industry"])
        heat_data.append([x, y, row["pct_change"]])

    c = (
        HeatMap(init_opts=opts.InitOpts(width="1000px", height=f"{max(400, len(industries) * 22)}px"))
        .add_xaxis(months)
        .add_yaxis(
            "涨跌幅(%)",
            industries,
            heat_data,
            label_opts=opts.LabelOpts(is_show=True, position="inside", font_size=8),
        )
        .set_global_opts(
            title_opts=opts.TitleOpts(title="行业月度涨跌幅热力图"),
            visualmap_opts=opts.VisualMapOpts(
                min_=-3, max_=3, is_calculable=True,
                orient="horizontal", pos_left="center",
                range_color=["#2ca02c", "#ffffff", "#d62728"],
            ),
            tooltip_opts=opts.TooltipOpts(formatter="{c}%"),
        )
    )
    return c


def chart_industry_amount_river(
    daily_df: pd.DataFrame,
    features_df: pd.DataFrame,
    top_n: int = 10,
) -> ThemeRiver:
    """图8: 行业成交额占比河流图（取Top N行业）。"""
    if "industry" not in features_df.columns:
        return ThemeRiver().set_global_opts(title_opts=opts.TitleOpts(title="缺少行业数据"))

    ind_map = features_df[["stock_code", "industry"]].drop_duplicates()
    df = daily_df.merge(ind_map, on="stock_code", how="left")

    # Top N 行业
    top_ind = df.groupby("industry")["amount"].sum().nlargest(top_n).index.tolist()
    df = df[df["industry"].isin(top_ind)]

    agg = df.groupby(["date", "industry"])["amount"].sum().reset_index()
    agg["amount_yi"] = (agg["amount"] / 1e8).round(2)

    data = [[row["date"], row["amount_yi"], row["industry"]] for _, row in agg.iterrows()]

    c = (
        ThemeRiver(init_opts=opts.InitOpts(width="1000px", height="500px"))
        .add(
            series_name=top_ind,
            data=data,
            singleaxis_opts=opts.SingleAxisOpts(type_="time", pos_bottom="10%"),
        )
        .set_global_opts(
            title_opts=opts.TitleOpts(title=f"Top{top_n}行业 成交额河流图"),
            tooltip_opts=opts.TooltipOpts(trigger="axis"),
        )
    )
    return c


# ===================================================================
# Chapter 4  量价与异动
# ===================================================================

def chart_anomaly_industry_heatmap(features_df: pd.DataFrame) -> HeatMap:
    """图17: 大阳线/大阴线次数 行业热力图。"""
    if "industry" not in features_df.columns:
        return HeatMap().set_global_opts(title_opts=opts.TitleOpts(title="缺少行业数据"))

    agg = features_df.groupby("industry").agg(
        big_yang=("big_yang_count", "mean"),
        big_yin=("big_yin_count", "mean"),
        limit_up=("limit_up_count", "mean"),
        limit_down=("limit_down_count", "mean"),
    ).round(2).reset_index()

    metrics = ["big_yang", "big_yin", "limit_up", "limit_down"]
    metric_labels = ["大阳线", "大阴线", "涨停", "跌停"]
    industries = agg["industry"].tolist()

    heat_data = []
    for _, row in agg.iterrows():
        y = industries.index(row["industry"])
        for j, m in enumerate(metrics):
            heat_data.append([j, y, float(row[m])])

    c = (
        HeatMap(init_opts=opts.InitOpts(width="800px", height=f"{max(400, len(industries) * 22)}px"))
        .add_xaxis(metric_labels)
        .add_yaxis(
            "平均次数",
            industries,
            heat_data,
            label_opts=opts.LabelOpts(is_show=True, position="inside", font_size=8),
        )
        .set_global_opts(
            title_opts=opts.TitleOpts(title="各行业异动特征"),
            visualmap_opts=opts.VisualMapOpts(
                min_=0, max_=5, is_calculable=True,
                orient="horizontal", pos_left="center",
            ),
        )
    )
    return c


# ===================================================================
# Chapter 5  聚类画像
# ===================================================================

def chart_cluster_radar(
    features_df: pd.DataFrame,
    radar_cols: Optional[list[str]] = None,
) -> Radar:
    """图19: 聚类雷达图。"""
    if radar_cols is None:
        radar_cols = [
            "cum_return", "annual_volatility", "max_drawdown",
            "avg_turnover", "avg_amplitude", "price_volume_corr",
        ]
    radar_cols = [c for c in radar_cols if c in features_df.columns]

    col_label = "cluster_name" if "cluster_name" in features_df.columns else "cluster_id"
    cluster_means = features_df.groupby(col_label)[radar_cols].mean()

    # 标准化到 0-100 范围便于雷达图展示
    mins = cluster_means.min()
    maxs = cluster_means.max()
    rng = maxs - mins
    rng[rng == 0] = 1
    normalized = ((cluster_means - mins) / rng * 100).round(1)

    schema = [opts.RadarIndicatorItem(name=c, max_=100) for c in radar_cols]

    c = Radar(init_opts=opts.InitOpts(width="800px", height="600px"))
    c.add_schema(schema=schema)

    colors = ["#d62728", "#2ca02c", "#1f77b4", "#ff7f0e", "#9467bd", "#8c564b", "#e377c2", "#7f7f7f"]
    for i, (cluster, row) in enumerate(normalized.iterrows()):
        c.add(
            series_name=str(cluster),
            data=[row.tolist()],
            areastyle_opts=opts.AreaStyleOpts(opacity=0.15),
            linestyle_opts=opts.LineStyleOpts(width=2),
            color=colors[i % len(colors)],
        )

    c.set_global_opts(
        title_opts=opts.TitleOpts(title="聚类特征雷达图"),
        legend_opts=opts.LegendOpts(pos_bottom="0%"),
    )
    return c


def chart_cluster_industry_sankey(features_df: pd.DataFrame) -> Sankey:
    """图20: 聚类 × 行业桑基图。"""
    col_label = "cluster_name" if "cluster_name" in features_df.columns else "cluster_id"

    if "industry" not in features_df.columns:
        return Sankey().set_global_opts(title_opts=opts.TitleOpts(title="缺少行业数据"))

    cross = (
        features_df.groupby([col_label, "industry"])
        .size()
        .reset_index(name="count")
    )
    # 过滤太少的组合
    cross = cross[cross["count"] >= 3]

    clusters = cross[col_label].unique().tolist()
    industries = cross["industry"].unique().tolist()

    nodes = [{"name": str(c)} for c in clusters] + [{"name": str(i)} for i in industries]
    links = [
        {"source": str(row[col_label]), "target": str(row["industry"]), "value": int(row["count"])}
        for _, row in cross.iterrows()
    ]

    c = (
        Sankey(init_opts=opts.InitOpts(width="1000px", height="700px"))
        .add(
            series_name="聚类→行业",
            nodes=nodes,
            links=links,
            linestyle_opt=opts.LineStyleOpts(opacity=0.3, curve=0.5, color="source"),
            label_opts=opts.LabelOpts(position="right", font_size=9),
        )
        .set_global_opts(
            title_opts=opts.TitleOpts(title="聚类×行业 桑基图"),
        )
    )
    return c


# ===================================================================
# Chapter 6  典型个股
# ===================================================================

def chart_kline(
    daily_df: pd.DataFrame,
    stock_code: str,
    stock_name: str = "",
) -> Kline:
    """图23: 单只股票 K 线图 + 成交量。"""
    df = daily_df[daily_df["stock_code"] == stock_code].sort_values("date").copy()
    if df.empty:
        return Kline().set_global_opts(title_opts=opts.TitleOpts(title=f"{stock_code} 无数据"))

    dates = df["date"].tolist()
    # Kline 数据格式: [open, close, low, high]
    kline_data = df[["open", "close", "low", "high"]].values.tolist()
    volumes = df["volume"].tolist()

    title = f"{stock_code} {stock_name}".strip()

    kline = (
        Kline(init_opts=opts.InitOpts(width="1000px", height="500px"))
        .add_xaxis(dates)
        .add_yaxis(
            title,
            kline_data,
            itemstyle_opts=opts.ItemStyleOpts(
                color="#d62728", color0="#2ca02c",
                border_color="#d62728", border_color0="#2ca02c",
            ),
        )
        .set_global_opts(
            title_opts=opts.TitleOpts(title=title),
            datazoom_opts=[opts.DataZoomOpts(range_start=0, range_end=100)],
            yaxis_opts=opts.AxisOpts(is_scale=True),
            tooltip_opts=opts.TooltipOpts(trigger="axis"),
            xaxis_opts=opts.AxisOpts(type_="category"),
        )
    )
    return kline


def chart_multi_stock_lines(
    daily_df: pd.DataFrame,
    stock_codes: list[str],
    stock_names: Optional[dict[str, str]] = None,
) -> Line:
    """图24: 多只代表股价格走势叠加（归一化到首日=100）。"""
    c = Line(init_opts=opts.InitOpts(width="1000px", height="500px"))

    dates_set: set[str] = set()
    for code in stock_codes:
        sub = daily_df[daily_df["stock_code"] == code].sort_values("date")
        if sub.empty:
            continue
        base = sub["close"].iloc[0]
        if base == 0:
            continue
        normalized = (sub["close"] / base * 100).round(2).tolist()
        dates = sub["date"].tolist()
        dates_set.update(dates)

        name = code
        if stock_names and code in stock_names:
            name = f"{code} {stock_names[code]}"

        c.add_xaxis(dates)
        c.add_yaxis(
            name,
            normalized,
            is_smooth=True,
            label_opts=opts.LabelOpts(is_show=False),
            symbol_size=3,
        )

    c.set_global_opts(
        title_opts=opts.TitleOpts(title="代表股走势对比（归一化）"),
        tooltip_opts=opts.TooltipOpts(trigger="axis"),
        datazoom_opts=[opts.DataZoomOpts(range_start=0, range_end=100)],
        yaxis_opts=opts.AxisOpts(name="归一化价格", is_scale=True),
        legend_opts=opts.LegendOpts(pos_bottom="0%", type_="scroll"),
    )
    return c
