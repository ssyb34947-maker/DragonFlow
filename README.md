## DragonFlow

A Visualization System for Market Leaders and Theme Rotation

本项目为西南财经大学 《数据可视化》 课程项目。

我们团队专注于对热点股、龙头股进行数据可视化分析，帮助用户快速复盘过往市场走势。

基于本项目，我们进行一次Demo Presentation。主题为：**《从夯到拉锐评2026年1至5月热点龙头股》**

## 技术栈

| 模块    | 技术               | 用途          |
| ----- | ---------------- | ----------- |
| 开发语言  | Python           | 主要开发语言     |
| 数据获取  | AkShare          | 获取A股行情/板块数据 |
| 数据处理  | Pandas           | 数据清洗、时间序列处理 |
| 数值计算  | Numpy            | 指标计算        |
| 数据分析  | Scikit-learn     | 机器学习数据分析 |
| 静态可视化 | Matplotlib       | 数据科学统计图表 |
| 高级可视化 | Pyecharts        | K线图/桑基图/热力图 |
| Web展示 | Streamlit        | 可交互分析平台 |
| 数据存储  | CSV / Parquet / SQLite | 存储历史数据      |
| 脚本环境  | Jupyter Notebook | 数据探索分析      |
| 项目管理  | uv + Git         | 版本管理        |

## 项目结构

```
DragonFlow/
├── app/                              # Streamlit 可视化前端
├── public/                           # 静态资源
├── src/
│   └── dragonflow/                   # 业务核心包
│       ├── data/
│       │   ├── download.py           # 各数据源下载器
│       │   └── schema.py             # 字段映射 / 列名标准化
│       └── utils/
│           ├── io.py                 # 路径、CSV/Parquet 读写
│           └── logger.py             # 统一日志
├── scripts/
│   └── 01_download_csi2000_data.py   # 第一步：数据下载入口
├── data/                             # 数据目录（已在 .gitignore 忽略大文件）
│   ├── raw/
│   │   ├── csi2000/                  # 成分股 / 指数日行情
│   │   ├── stock_daily/qfq/          # 单只股票日线 CSV（断点续跑）
│   │   └── fundamental/              # 基础信息 / 快照 / 财报
│   └── processed/                    # 合并后的长表 + 报告
├── config.yaml                       # 默认配置
└── main.py                           # 主程序
```

## 快速开始

```bash
# 安装依赖（推荐 uv）
uv sync

# 或退化到 pip
pip install -e .
```

## 第一步：下载中证2000数据

> 本步骤只做"数据下载与本地落盘"。不会做收益率/波动率/PCA/聚类/可视化等任何加工。

### 数据来源

- **AkShare**（封装东方财富 / 中证指数 / 新浪等接口）
- 成分股：`index_stock_cons_csindex` → `index_stock_cons` → `index_stock_cons_sina` 自动 fallback
- 指数行情：`stock_zh_index_daily_em` 自动尝试 `csi932000 / sh932000 / 932000` 等 symbol
- 个股日线：`stock_zh_a_hist`，默认 **前复权 qfq**
- 个股基础信息：`stock_individual_info_em`
- 截面快照：`stock_zh_a_spot_em` 过滤成分股
- 财报：`stock_lrb_em` / `stock_zcfz_em` / `stock_xjll_em`，优先 `20260331`，自动回退 `20251231 / 20250930 / 20250630`

### 默认时间窗口

- `start_date = 2026-01-01`
- `end_date   = 2026-05-31`

### 运行命令

```bash
# uv 用户
uv run python scripts/01_download_csi2000_data.py \
  --start-date 2026-01-01 \
  --end-date 2026-05-31 \
  --index-code 932000 \
  --adjust qfq

# 或直接 python
python scripts/01_download_csi2000_data.py \
  --start-date 2026-01-01 \
  --end-date 2026-05-31 \
  --index-code 932000 \
  --adjust qfq
```

### 命令行参数

| 参数 | 默认 | 说明 |
| --- | --- | --- |
| `--start-date` | `2026-01-01` | 起始日期 |
| `--end-date` | `2026-05-31` | 结束日期 |
| `--index-code` | `932000` | 指数代码 |
| `--adjust` | `qfq` | 复权方式：`qfq` / `hfq` / `""` |
| `--force` | `False` | 忽略已存在的单只股票 CSV，强制重新下载 |
| `--sleep` | `0.3` | 单只股票请求之间的间隔秒数 |
| `--max-workers` | `1` | 并发数（当前串行；预留） |
| `--skip-fundamental` | `False` | 跳过基础信息/快照/财报（只跑行情） |
| `--limit` | `0` | 仅下载前 N 只成分股（冒烟测试用，0=全部） |

### 输出文件

```
data/raw/csi2000/
  constituents_932000_YYYYMMDD.csv
  constituents_932000_latest.csv
  index_daily_932000_20260101_20260531.csv
  index_daily_932000_20260101_20260531.parquet

data/raw/stock_daily/qfq/
  {stock_code}.csv          # 一只股票一个文件，断点续跑

data/raw/fundamental/
  stock_info_csi2000_YYYYMMDD.csv
  stock_spot_snapshot_YYYYMMDD.csv
  profit_YYYYMMDD.csv
  balance_YYYYMMDD.csv
  cashflow_YYYYMMDD.csv

data/processed/
  stock_daily_csi2000_qfq_20260101_20260531.csv
  stock_daily_csi2000_qfq_20260101_20260531.parquet
  stock_info_csi2000_latest.parquet
  stock_spot_snapshot_csi2000_latest.parquet
  fundamental_csi2000_latest.parquet
  fundamental_csi2000_latest.csv
  data_coverage_report.csv
  download_manifest.json
  download_errors.csv
```

### 常见问题

- **接口失败 / 网络慢**：脚本对成分股、指数行情、财报都配置了多接口 fallback。临时性失败可以直接重跑（默认会跳过已下载文件，断点续跑）。
- **部分股票缺失**：停牌、退市、新上市的个股可能某个时段没数据；脚本会写入 `data/processed/download_errors.csv` 记录原因，且会在 `data_coverage_report.csv` 中体现覆盖率。
- **如何断点续跑**：直接重跑同样的命令即可，`data/raw/stock_daily/qfq/{code}.csv` 已存在的股票会自动跳过。需要刷新某段数据时加 `--force`。
- **AkShare 限流**：可加大 `--sleep`（如 0.5/1.0）减小请求频率。
- **首次冒烟测试**：可以加 `--limit 20 --skip-fundamental` 只下载 20 只成分股的日线，快速验证环境。

### 不要做的事情（本步骤约束）

- 不计算收益率 / 波动率 / 最大回撤 / FFT / PCA / 聚类
- 不修改 Streamlit 前端
- 不把大型原始数据提交到 git（已在 `.gitignore` 排除 `data/raw` 与 `data/processed`）
