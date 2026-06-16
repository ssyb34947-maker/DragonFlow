import { motion } from 'framer-motion'
import {
  Network,
  CandlestickChart,
  BrainCircuit,
  ArrowUpRight,
  ShieldCheck,
  FileText,
  Cpu,
  Database,
  Layers3,
  Microscope,
  FlaskConical,
  Activity,
  LineChart,
  Gauge,
  TableProperties,
} from 'lucide-react'

type Module = {
  id: string
  resultId: string
  icon: typeof Database
  label: string
  title: string
  thesis: string
  contribution: string
}

const metrics = [
  ['股票池', '中证2000'],
  ['样本量', '189,811 行'],
  ['预测周期', '未来5个交易日'],
  ['输出', '收益分位数'],
]

const modules: Module[] = [
  {
    id: 'panel-construction',
    resultId: 'result-data',
    icon: Database,
    label: '数据协议',
    title: '时点一致的截面面板',
    thesis: '按交易日对齐个股行情、市场状态、形态特征和未来收益标签，形成可复现实验面板。',
    contribution: '保留A股截面结构，避免把问题退化成单股票曲线拟合，也为后续图关系建模和组合回测提供统一入口。',
  },
  {
    id: 'kline-representation',
    resultId: 'result-kline',
    icon: CandlestickChart,
    label: 'K线表征',
    title: 'Kronos启发的K线分词器',
    thesis: '将连续开高低收量序列切分为价格形态 token，再映射为可学习的K线状态表征。',
    contribution: '把形态、波动、量价关系转成序列 token 与低维嵌入，作为TFT的历史价格语义输入。',
  },
  {
    id: 'graph-conditioning',
    resultId: 'result-graph',
    icon: Network,
    label: '股票关系图',
    title: '滚动谱聚类图嵌入',
    thesis: '基于滚动收益相关性构建股票关系图，提取谱嵌入、簇标签和同簇上下文。',
    contribution: '让模型感知个股在市场结构中的位置，补足纯时间序列模型缺少横截面关系的问题。',
  },
  {
    id: 'temporal-fusion',
    resultId: 'result-tft',
    icon: BrainCircuit,
    label: '时序融合',
    title: 'KS-TFT分位数预测头',
    thesis: '在TFT主干中融合静态特征、历史序列、K线token表征和谱聚类嵌入，输出未来5日超额收益的多分位数预测。',
    contribution: '中位数用于收益排序，低分位用于风险过滤，分位差用于不确定性控制，使KS-TFT可以直接对接组合构建。',
  },
]

const workflow = [
  ['01', '构建面板', '生成特征、标签与时间切分'],
  ['02', '图嵌入', '滚动构图、谱聚类、同簇上下文'],
  ['03', 'K线分词', '训练形态token与辅助任务'],
  ['04', 'TFT训练', '训练分位数预测模型'],
  ['05', '组合回测', '打分、持仓、成本后绩效评估'],
]

const evaluationSlots = [
  {
    id: 'result-data',
    icon: TableProperties,
    title: '数据覆盖与时间切分',
    desc: '训练/验证/测试区间、缺失率、标签覆盖率、截面样本分布。',
    pending: '等待服务器导出 coverage_report 与 split_audit 图表。',
  },
  {
    id: 'result-kline',
    icon: Activity,
    title: 'K线分词器诊断',
    desc: '辅助任务 loss、token嵌入分布、典型形态聚类和稳定性检查。',
    pending: '预留 kline_encoder_eval.png / embedding_umap.png。',
  },
  {
    id: 'result-graph',
    icon: Network,
    title: '谱聚类结构检验',
    desc: '簇数量选择、同簇相关性、行业/风格一致性与消融对比。',
    pending: '预留 spectral_embedding.png / peer_context_ablation.png。',
  },
  {
    id: 'result-tft',
    icon: LineChart,
    title: '预测与组合回测',
    desc: 'IC、RankIC、分位数组合、净值曲线、回撤、换手和交易成本。',
    pending: '预留 prediction_calibration.png / equity_curve.png / metrics_table.csv。',
  },
]

const claims = [
  ['研究问题', '短周期A股截面预测同时受到价格形态非平稳、股票关系迁移和样本窗口有限的约束。'],
  ['核心假设', 'K线分词器提供局部价格语义，谱聚类嵌入提供横截面关系先验，TFT负责融合并输出可交易预测。'],
  ['方法设计', 'KS-TFT 的完整方法名为 K-line Tokenizer and Spectral-enhanced Temporal Fusion Transformer，将K线分词、谱聚类嵌入和TFT融合为一套截面收益预测协议。'],
  ['验证方式', '采用时间外推切分、模块消融和成本后组合回测评估，不用训练集拟合结果替代交易验证。'],
]

const configs = [
  ['spectral', 'graph_window / embedding_dim / k_min-k_max'],
  ['kline_encoder', 'd_model / heads / layers / auxiliary heads'],
  ['fusion_model', 'encoder_length / quantiles / dropout / device'],
  ['backtest', 'top_n / q10_floor / liquidity / transaction cost'],
]

function scrollTo(id: string) {
  document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

export default function ModelPage() {
  return (
    <div className="mx-auto max-w-[1500px] space-y-6">
      <motion.section
        initial={{ opacity: 0, y: 18 }}
        animate={{ opacity: 1, y: 0 }}
        className="relative overflow-hidden rounded-xl border border-border bg-surface shadow-2xl"
      >
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,rgba(247,147,26,0.13),transparent_45%),radial-gradient(ellipse_at_bottom_right,rgba(255,214,0,0.06),transparent_35%)]" />
        <div className="absolute inset-x-0 top-0 h-1 bg-gradient-to-r from-primary via-gold to-primary" />

        <div className="relative grid min-h-[calc(100vh-72px)] gap-6 px-5 py-6 sm:px-7 lg:px-9 xl:px-11">
          <header className="grid gap-5 border-b border-border pb-5 xl:grid-cols-[1fr_380px] xl:items-end">
            <div>
              <div className="mb-4 flex flex-wrap items-center gap-2">
                <span className="badge-df inline-flex items-center gap-2 normal-case">
                  <Layers3 className="h-3.5 w-3.5 text-primary" />
                  DragonFlow-KronosGraph
                </span>
                <span className="rounded-full border border-border bg-white/[0.03] px-3 py-1 text-xs font-medium text-fg-muted">
                  答辩展示 · KS-TFT模型方案
                </span>
              </div>
              <h1 className="max-w-6xl text-[clamp(1.95rem,4.7vw,4.7rem)] font-bold leading-[1.02] tracking-tight text-fg">
                <span className="text-primary">K</span>-line Tokenizer and{' '}
                <span className="text-primary">S</span>pectral-enhanced{' '}
                <span className="text-primary">T</span>emporal{' '}
                <span className="text-primary">F</span>usion{' '}
                <span className="text-primary">T</span>ransformer
              </h1>
              <p className="mt-4 max-w-5xl text-base leading-relaxed text-fg-muted lg:text-lg">
                简称 <span className="font-semibold text-primary">KS-TFT</span>。本方案以 <span className="font-semibold text-primary">DragonFlow-KronosGraph</span> 为项目框架：
                K 对应K线分词器，S 对应谱聚类嵌入增强，TFT 负责时序融合与分位数预测，最终输出未来5日超额收益信号。
              </p>
            </div>

            <div className="grid grid-cols-2 overflow-hidden rounded-lg border border-border bg-black/20">
              {metrics.map(([label, value], index) => (
                <div
                  key={label}
                  className={`border-border px-4 py-4 ${index < 2 ? 'border-b' : ''} ${index % 2 === 0 ? 'border-r' : ''}`}
                >
                  <div className="text-[11px] font-medium uppercase tracking-wider text-fg-dim">{label}</div>
                  <div className="mt-2 font-mono text-lg font-semibold text-primary">{value}</div>
                </div>
              ))}
            </div>
          </header>

          <section className="grid gap-5 xl:grid-cols-[0.92fr_1.55fr]">
            <div className="grid content-start gap-3">
              {claims.map(([title, desc]) => (
                <div key={title} className="rounded-lg border border-border bg-white/[0.035] px-4 py-3">
                  <div className="text-sm font-semibold text-fg">{title}</div>
                  <p className="mt-1.5 text-sm leading-relaxed text-fg-muted">{desc}</p>
                </div>
              ))}
            </div>

            <figure className="relative overflow-hidden rounded-xl border border-border bg-[#0f172a] p-3 shadow-[0_22px_80px_rgba(0,0,0,0.38)]">
              <div className="mb-3 flex flex-col gap-2 border-b border-border pb-3 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <div className="text-xs font-semibold uppercase tracking-wider text-primary">架构总览</div>
                  <h2 className="text-2xl font-bold text-fg">从数据面板到组合回测的闭环</h2>
                </div>
                <div className="font-mono text-xs text-fg-dim">OHLCV / K线分词 / 谱嵌入 / TFT / 回测</div>
              </div>
              <img
                src="/assets/model/kronosgraph-architecture.png"
                alt="DragonFlow-KronosGraph 量化交易模型架构图"
                className="h-[min(50vh,620px)] min-h-[390px] w-full rounded-lg object-contain"
              />
            </figure>
          </section>

          <section className="grid gap-3 lg:grid-cols-4">
            {modules.map((item, index) => {
              const Icon = item.icon
              return (
                <motion.button
                  key={item.id}
                  type="button"
                  onClick={() => scrollTo(item.id)}
                  initial={{ opacity: 0, y: 14 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.08 + index * 0.04 }}
                  className="card-df group cursor-pointer p-5 text-left focus:outline-none focus:ring-2 focus:ring-primary/70"
                >
                  <div className="mb-4 flex items-start justify-between gap-3">
                    <div className="text-xs font-semibold uppercase tracking-wider text-primary">{item.label}</div>
                    <div className="flex h-9 w-9 items-center justify-center rounded-lg border border-border bg-white/[0.04]">
                      <Icon className="h-4.5 w-4.5 text-primary" />
                    </div>
                  </div>
                  <h3 className="text-xl font-bold leading-tight text-fg">{item.title}</h3>
                  <p className="mt-3 text-sm leading-relaxed text-fg-muted">{item.thesis}</p>
                  <div className="mt-4 inline-flex items-center gap-1 text-xs font-semibold text-primary">
                    查看模块
                    <ArrowUpRight className="h-3.5 w-3.5 transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
                  </div>
                </motion.button>
              )
            })}
          </section>

          <section className="grid gap-4 border-t border-border pt-4 xl:grid-cols-[1.2fr_0.8fr]">
            <div className="grid gap-2 md:grid-cols-5">
              {workflow.map(([step, title, desc]) => (
                <div key={step} className="rounded-lg border border-border bg-white/[0.03] p-3">
                  <div className="font-mono text-xl font-semibold text-primary">{step}</div>
                  <div className="mt-1 text-sm font-semibold text-fg">{title}</div>
                  <p className="mt-1 text-xs leading-relaxed text-fg-dim">{desc}</p>
                </div>
              ))}
            </div>

            <div className="rounded-lg border border-primary/25 bg-primary/[0.055] p-4">
              <div className="mb-3 flex items-center gap-2 text-sm font-semibold text-fg">
                <Cpu className="h-4 w-4 text-primary" />
                可复现实验配置
              </div>
              <div className="grid gap-1.5">
                {configs.map(([key, value]) => (
                  <div key={key} className="font-mono text-[11px] leading-relaxed text-fg-dim">
                    <span className="text-primary">{key}</span> / {value}
                  </div>
                ))}
              </div>
            </div>
          </section>
        </div>
      </motion.section>

      <section className="grid gap-4 lg:grid-cols-2">
        {modules.map((item) => {
          const Icon = item.icon
          return (
            <section id={item.id} key={item.id} className="card-df scroll-mt-6 p-6">
              <div className="mb-4 flex items-start justify-between gap-4 border-b border-border pb-4">
                <div>
                  <div className="text-xs font-semibold uppercase tracking-wider text-primary">{item.label}</div>
                  <h2 className="mt-1 text-2xl font-bold text-fg">{item.title}</h2>
                </div>
                <Icon className="h-7 w-7 text-primary" />
              </div>
              <p className="text-sm leading-relaxed text-fg-muted">{item.thesis}</p>
              <div className="mt-4 rounded-lg border border-primary/20 bg-primary/[0.055] px-4 py-3">
                <div className="text-xs font-semibold uppercase tracking-wider text-primary">研究贡献</div>
                <p className="mt-1.5 text-sm leading-relaxed text-fg-muted">{item.contribution}</p>
              </div>
              <button
                type="button"
                onClick={() => scrollTo(item.resultId)}
                className="btn-secondary mt-5 inline-flex items-center gap-2 rounded-lg"
              >
                跳转到测试结果占位
                <ArrowUpRight className="h-4 w-4" />
              </button>
            </section>
          )
        })}
      </section>

      <section className="card-df p-6 lg:p-7">
        <div className="mb-5 flex flex-col gap-3 border-b border-border pb-5 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <div className="text-xs font-semibold uppercase tracking-wider text-primary">结果展示区</div>
            <h2 className="mt-1 text-3xl font-bold text-fg">模型测试结果占位</h2>
            <p className="mt-2 max-w-4xl text-sm leading-relaxed text-fg-muted">
              这里先按真实实验结构预留图表位置。服务器训练完成后，可替换为 IC/RankIC、消融实验、分位校准、净值曲线和交易成本后绩效图。
            </p>
          </div>
          <a
            href="/docs/training_guide_kronosgraph_v1.md"
            target="_blank"
            rel="noreferrer"
            className="btn-secondary inline-flex items-center justify-center gap-2 rounded-lg"
          >
            <FileText className="h-4 w-4" />
            训练文档
            <ArrowUpRight className="h-4 w-4" />
          </a>
        </div>

        <div className="grid gap-4 lg:grid-cols-2">
          {evaluationSlots.map((slot) => {
            const Icon = slot.icon
            return (
              <article id={slot.id} key={slot.id} className="scroll-mt-6 rounded-lg border border-border bg-white/[0.03] p-5">
                <div className="mb-4 flex items-start justify-between gap-4">
                  <div>
                    <div className="text-[11px] font-semibold uppercase tracking-wider text-fg-dim">图表待补充</div>
                    <h3 className="mt-1 text-xl font-bold text-fg">{slot.title}</h3>
                  </div>
                  <Icon className="h-6 w-6 text-primary" />
                </div>
                <div className="flex min-h-[220px] items-center justify-center rounded-lg border border-dashed border-border bg-black/20 p-6 text-center">
                  <div>
                    <Gauge className="mx-auto h-8 w-8 text-fg-dim" />
                    <p className="mt-3 text-sm font-semibold text-fg-muted">{slot.desc}</p>
                    <p className="mt-2 font-mono text-xs leading-relaxed text-fg-dim">{slot.pending}</p>
                  </div>
                </div>
              </article>
            )
          })}
        </div>
      </section>

      <section className="grid gap-4 lg:grid-cols-3">
        <div className="card-df p-5">
          <div className="mb-2 flex items-center gap-2 text-sm font-semibold text-fg">
            <Microscope className="h-4 w-4 text-primary" />
            评估纪律
          </div>
          <p className="text-sm leading-relaxed text-fg-muted">所有指标按时间外推评估，避免同一时期随机切分造成未来信息混入。</p>
        </div>
        <div className="card-df p-5">
          <div className="mb-2 flex items-center gap-2 text-sm font-semibold text-fg">
            <FlaskConical className="h-4 w-4 text-primary" />
            消融协议
          </div>
          <p className="text-sm leading-relaxed text-fg-muted">预留基线、加入K线、加入图嵌入、完整模型四组对比，验证模块边际贡献。</p>
        </div>
        <div className="card-df p-5">
          <div className="mb-2 flex items-center gap-2 text-sm font-semibold text-fg">
            <ShieldCheck className="h-4 w-4 text-primary" />
            研究边界
          </div>
          <p className="text-sm leading-relaxed text-fg-muted">当前1-5月数据用于验证链路和研究范式，不包装为生产级收益承诺。</p>
        </div>
      </section>
    </div>
  )
}
