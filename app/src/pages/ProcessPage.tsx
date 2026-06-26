import { useState } from 'react'
import { motion } from 'framer-motion'
import type { LucideIcon } from 'lucide-react'
import {
  GitMerge,
  BarChart3,
  FileCheck,
  Play,
  CheckCircle2,
  Database,
  ArrowRight,
  Layers,
  TrendingUp,
  Table2,
  RotateCcw,
} from 'lucide-react'

interface ProcessTask {
  id: string
  name: string
  description: string
  script: string
  status: 'pending' | 'running' | 'success' | 'error'
  inputs: string[]
  outputs: string[]
}

interface FlowStep {
  label: string
  icon: LucideIcon
}

const tasks: ProcessTask[] = [
  {
    id: 'finalize',
    name: '合并长表',
    description: '将个股前复权日线合并为统一长表，并生成覆盖率报告。',
    script: 'scripts/02_finalize_partial.py',
    status: 'pending',
    inputs: ['data/raw/stock_daily/qfq/*.csv', 'data/raw/csi2000/constituents_932000_latest.csv'],
    outputs: [
      'data/processed/stock_daily_csi2000_qfq_*.csv',
      'data/processed/stock_daily_csi2000_qfq_*.parquet',
      'data/processed/data_coverage_report.csv',
    ],
  },
  {
    id: 'synthesize-index',
    name: '合成代理指数',
    description: '基于成分股等权收益合成中证2000代理指数。',
    script: 'scripts/03_synthesize_index_proxy.py',
    status: 'pending',
    inputs: ['data/processed/stock_daily_csi2000_qfq_*.parquet'],
    outputs: [
      'data/processed/index_daily_932000_proxy_equal_weight_*.csv',
      'data/processed/index_daily_932000_proxy_equal_weight_*.parquet',
    ],
  },
  {
    id: 'synthesize-spot',
    name: '合成截面快照',
    description: '取每只股票最后一个交易日的数据作为截面快照。',
    script: 'scripts/04_synthesize_spot_snapshot.py',
    status: 'pending',
    inputs: ['data/processed/stock_daily_csi2000_qfq_*.parquet'],
    outputs: [
      'data/processed/stock_spot_snapshot_csi2000_latest.csv',
      'data/processed/stock_spot_snapshot_csi2000_latest.parquet',
    ],
  },
]

const flowSteps: FlowStep[] = [
  { label: '原始CSV', icon: Database },
  { label: '合并长表', icon: Table2 },
  { label: '代理指数', icon: TrendingUp },
  { label: '截面快照', icon: Layers },
]

const qualityMetrics = [
  { label: '成分股数量', value: '2000', target: '2000' },
  { label: '日线覆盖率', value: '100%', target: '>95%' },
  { label: '指数行情', value: '95行', target: '>90' },
  { label: '失败比例', value: '0%', target: '<20%' },
]

function statusText(status: ProcessTask['status']) {
  if (status === 'running') return '处理中'
  if (status === 'success') return '完成'
  if (status === 'error') return '失败'
  return '待执行'
}

function statusClass(status: ProcessTask['status']) {
  if (status === 'running') return 'border-primary/40 bg-primary/10 text-primary'
  if (status === 'success') return 'border-success/30 bg-success/10 text-success'
  if (status === 'error') return 'border-danger/30 bg-danger/10 text-danger'
  return 'border-border bg-white/[0.03] text-fg-muted'
}

export default function ProcessPage() {
  const [processTasks, setProcessTasks] = useState<ProcessTask[]>(tasks)
  const [isRunning, setIsRunning] = useState(false)

  const runTask = async (taskId: string) => {
    setProcessTasks((prev) => prev.map((t) => (t.id === taskId ? { ...t, status: 'running' } : t)))
    await new Promise((r) => setTimeout(r, 900))
    setProcessTasks((prev) => prev.map((t) => (t.id === taskId ? { ...t, status: 'success' } : t)))
  }

  const runAll = async () => {
    setIsRunning(true)
    for (const task of tasks) {
      await runTask(task.id)
    }
    setIsRunning(false)
  }

  const resetTasks = () => {
    setProcessTasks(tasks)
    setIsRunning(false)
  }

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-3xl font-bold text-fg" style={{ fontFamily: 'var(--font-heading)' }}>
            数据预处理
          </h1>
          <p className="mt-1 text-fg-muted">数据合并、代理指数合成、截面快照与质量检查</p>
        </div>
        <div className="flex flex-wrap gap-3">
          <button onClick={runAll} disabled={isRunning} className="btn-primary inline-flex items-center gap-2 disabled:opacity-50">
            <Play className="h-4 w-4" />
            {isRunning ? '处理中...' : '运行全部'}
          </button>
          <button onClick={resetTasks} disabled={isRunning} className="btn-secondary inline-flex items-center gap-2 disabled:opacity-50">
            <RotateCcw className="h-4 w-4" />
            重置
          </button>
        </div>
      </div>

      <motion.section initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="card-df p-6">
        <h2 className="mb-5 text-lg font-semibold text-fg">数据流向图</h2>
        <div className="grid gap-3 sm:grid-cols-[1fr_auto_1fr_auto_1fr_auto_1fr] sm:items-center">
          {flowSteps.map((item, index) => {
            const Icon = item.icon
            return (
              <div key={item.label} className="contents">
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.06 }}
                  className="flex min-h-14 items-center justify-center gap-2 rounded-xl border border-primary/20 bg-primary/10 px-4 py-3 text-sm font-medium text-primary"
                >
                  <Icon className="h-4 w-4 shrink-0" />
                  <span className="whitespace-nowrap">{item.label}</span>
                </motion.div>
                {index < flowSteps.length - 1 && (
                  <div className="hidden justify-center sm:flex">
                    <ArrowRight className="h-5 w-5 text-fg-dim" />
                  </div>
                )}
              </div>
            )
          })}
        </div>
      </motion.section>

      <div className="space-y-4">
        {processTasks.map((task, index) => (
          <motion.section
            key={task.id}
            initial={{ opacity: 0, x: -16 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: index * 0.08 }}
            className={`card-df p-5 ${task.status === 'running' ? 'border-primary/40 shadow-[0_0_20px_rgba(247,147,26,0.10)]' : ''} ${task.status === 'success' ? 'border-success/30' : ''}`}
          >
            <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
              <div className="flex min-w-0 items-start gap-4">
                <div
                  className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border"
                  style={{
                    background:
                      task.status === 'success'
                        ? 'rgba(16,185,129,0.10)'
                        : task.status === 'running'
                        ? 'rgba(247,147,26,0.12)'
                        : 'rgba(255,255,255,0.03)',
                    borderColor:
                      task.status === 'success'
                        ? 'rgba(16,185,129,0.20)'
                        : task.status === 'running'
                        ? 'rgba(247,147,26,0.25)'
                        : 'rgba(30,41,59,0.6)',
                  }}
                >
                  {task.status === 'success' ? (
                    <CheckCircle2 className="h-5 w-5 text-success" />
                  ) : task.status === 'running' ? (
                    <GitMerge className="h-5 w-5 animate-spin text-primary" />
                  ) : (
                    <GitMerge className="h-5 w-5 text-fg-dim" />
                  )}
                </div>
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <h3 className="text-base font-semibold text-fg">{task.name}</h3>
                    <span className={`rounded-full border px-2.5 py-1 text-xs font-medium ${statusClass(task.status)}`}>{statusText(task.status)}</span>
                  </div>
                  <p className="mt-1 text-sm leading-relaxed text-fg-muted">{task.description}</p>
                  <code className="mt-2 inline-block max-w-full overflow-x-auto rounded bg-white/[0.04] px-2 py-1 font-mono text-xs text-fg-dim">
                    {task.script}
                  </code>
                </div>
              </div>
              <button
                onClick={() => runTask(task.id)}
                disabled={isRunning || task.status === 'running'}
                className="inline-flex shrink-0 cursor-pointer items-center justify-center gap-1.5 rounded-lg border border-primary/20 bg-primary/10 px-3 py-2 text-sm text-primary transition-colors hover:bg-primary/15 disabled:cursor-not-allowed disabled:opacity-50"
              >
                <Play className="h-3.5 w-3.5" />
                运行
              </button>
            </div>

            <div className="mt-4 grid gap-4 border-t border-border pt-4 md:grid-cols-2">
              <div className="min-w-0">
                <div className="mb-2 flex items-center gap-1.5 text-xs font-medium text-fg-muted">
                  <Database className="h-3.5 w-3.5 text-primary" />
                  输入文件
                </div>
                <div className="space-y-1.5">
                  {task.inputs.map((input) => (
                    <div key={input} className="flex min-w-0 items-start gap-1.5 rounded bg-white/[0.03] px-2 py-1.5 font-mono text-xs text-fg-muted">
                      <ArrowRight className="mt-0.5 h-3 w-3 shrink-0 text-primary" />
                      <span className="min-w-0 break-all">{input}</span>
                    </div>
                  ))}
                </div>
              </div>
              <div className="min-w-0">
                <div className="mb-2 flex items-center gap-1.5 text-xs font-medium text-fg-muted">
                  <FileCheck className="h-3.5 w-3.5 text-success" />
                  输出文件
                </div>
                <div className="space-y-1.5">
                  {task.outputs.map((output) => (
                    <div key={output} className="flex min-w-0 items-start gap-1.5 rounded bg-white/[0.03] px-2 py-1.5 font-mono text-xs text-fg-muted">
                      <CheckCircle2 className="mt-0.5 h-3 w-3 shrink-0 text-success" />
                      <span className="min-w-0 break-all">{output}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </motion.section>
        ))}
      </div>

      <motion.section initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.4 }} className="card-df p-6">
        <div className="mb-4 flex items-center gap-2">
          <BarChart3 className="h-5 w-5 text-primary" />
          <h2 className="text-lg font-semibold text-fg">数据质量指标</h2>
        </div>
        <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
          {qualityMetrics.map((metric) => (
            <div key={metric.label} className="rounded-xl border border-border bg-white/[0.03] p-4 text-center">
              <div className="font-mono text-2xl font-bold text-fg">{metric.value}</div>
              <div className="mt-1 text-xs text-fg-muted">{metric.label}</div>
              <div className="mt-0.5 text-[10px] text-fg-dim">目标: {metric.target}</div>
            </div>
          ))}
        </div>
      </motion.section>
    </div>
  )
}
