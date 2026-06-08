import { useState } from 'react'
import { motion } from 'framer-motion'
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

const tasks: ProcessTask[] = [
  {
    id: 'finalize',
    name: '合并长表 (Finalize)',
    description: '将 data/raw/stock_daily/qfq/*.csv 合并为统一长表，生成本地覆盖率报告',
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
    description: '基于成分股等权重合成中证2000代理指数（日收益累乘）',
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
    description: '取每只股票最后一个交易日的数据作为截面快照',
    script: 'scripts/04_synthesize_spot_snapshot.py',
    status: 'pending',
    inputs: ['data/processed/stock_daily_csi2000_qfq_*.parquet'],
    outputs: [
      'data/processed/stock_spot_snapshot_csi2000_latest.csv',
      'data/processed/stock_spot_snapshot_csi2000_latest.parquet',
    ],
  },
]

export default function ProcessPage() {
  const [processTasks, setProcessTasks] = useState<ProcessTask[]>(tasks)
  const [isRunning, setIsRunning] = useState(false)

  const runTask = async (taskId: string) => {
    setProcessTasks((prev) => prev.map((t) => (t.id === taskId ? { ...t, status: 'running' } : t)))
    await new Promise((r) => setTimeout(r, 1500))
    setProcessTasks((prev) => prev.map((t) => (t.id === taskId ? { ...t, status: 'success' } : t)))
  }

  const runAll = async () => {
    setIsRunning(true)
    for (const task of processTasks) {
      if (task.status === 'pending') {
        await runTask(task.id)
      }
    }
    setIsRunning(false)
  }

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-fg" style={{ fontFamily: 'var(--font-heading)' }}>
            数据预处理
          </h1>
          <p className="text-fg-muted mt-1">数据合并、合成与质量检查</p>
        </div>
        <button onClick={runAll} disabled={isRunning} className="btn-primary flex items-center gap-2 disabled:opacity-50">
          <Play className="w-4 h-4" />
          {isRunning ? '处理中...' : '运行全部'}
        </button>
      </div>

      {/* Data Flow Diagram */}
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="card-df p-6">
        <h2 className="text-lg font-semibold text-fg mb-4">数据流向图</h2>
        <div className="flex flex-wrap items-center justify-center gap-3 py-4">
          {[
            { label: '原始CSV', icon: Database },
            { label: '合并长表', icon: Table2 },
            { label: '代理指数', icon: TrendingUp },
            { label: '截面快照', icon: Layers },
          ].map((item, i) => (
            <div key={item.label} className="flex items-center gap-3">
              <motion.div
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: i * 0.1 }}
                className="flex items-center gap-2 px-4 py-2.5 rounded-xl font-medium text-sm"
                style={{
                  background: 'rgba(247,147,26,0.08)',
                  border: '1px solid rgba(247,147,26,0.20)',
                  color: '#F7931A',
                }}
              >
                <item.icon className="w-4 h-4" />
                {item.label}
              </motion.div>
              {i < 3 && (
                <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: i * 0.1 + 0.05 }}>
                  <ArrowRight className="w-5 h-5 text-fg-dim" />
                </motion.div>
              )}
            </div>
          ))}
        </div>
      </motion.div>

      {/* Tasks */}
      <div className="space-y-4">
        {processTasks.map((task, index) => (
          <motion.div
            key={task.id}
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: index * 0.1 }}
            className={`card-df p-5 ${
              task.status === 'running'
                ? 'border-primary/40 shadow-[0_0_20px_rgba(247,147,26,0.10)]'
                : task.status === 'success'
                ? 'border-success/30'
                : ''
            }`}
          >
            <div className="flex items-start justify-between">
              <div className="flex items-start gap-4">
                <div
                  className="p-2.5 rounded-xl flex-shrink-0"
                  style={{
                    background:
                      task.status === 'success'
                        ? 'rgba(16,185,129,0.10)'
                        : task.status === 'running'
                        ? 'rgba(247,147,26,0.12)'
                        : 'rgba(255,255,255,0.03)',
                    border:
                      task.status === 'success'
                        ? '1px solid rgba(16,185,129,0.20)'
                        : task.status === 'running'
                        ? '1px solid rgba(247,147,26,0.25)'
                        : '1px solid rgba(30,41,59,0.6)',
                  }}
                >
                  {task.status === 'success' ? (
                    <CheckCircle2 className="w-5 h-5 text-success" />
                  ) : task.status === 'running' ? (
                    <GitMerge className="w-5 h-5 text-primary animate-spin" />
                  ) : (
                    <GitMerge className="w-5 h-5 text-fg-dim" />
                  )}
                </div>
                <div>
                  <h3 className="text-base font-semibold text-fg">{task.name}</h3>
                  <p className="text-sm text-fg-muted mt-0.5">{task.description}</p>
                  <div className="flex items-center gap-2 mt-2">
                    <span
                      className="text-xs font-mono px-2 py-0.5 rounded"
                      style={{ background: 'rgba(255,255,255,0.04)', color: '#64748B' }}
                    >
                      {task.script}
                    </span>
                  </div>
                </div>
              </div>
              <button
                onClick={() => runTask(task.id)}
                disabled={isRunning || task.status === 'running'}
                className="flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-lg transition-colors disabled:opacity-50"
                style={{
                  background: 'rgba(247,147,26,0.10)',
                  color: '#F7931A',
                  border: '1px solid rgba(247,147,26,0.20)',
                }}
              >
                <Play className="w-3.5 h-3.5" />
                运行
              </button>
            </div>

            {/* Inputs/Outputs */}
            <div className="grid md:grid-cols-2 gap-4 mt-4 pt-4 sep-df">
              <div>
                <div className="flex items-center gap-1.5 text-xs font-medium text-fg-muted mb-2">
                  <Database className="w-3.5 h-3.5 text-primary" />
                  输入文件
                </div>
                <div className="space-y-1">
                  {task.inputs.map((input) => (
                    <div
                      key={input}
                      className="flex items-center gap-1.5 text-xs px-2 py-1 rounded font-mono"
                      style={{ background: 'rgba(255,255,255,0.03)', color: '#94A3B8' }}
                    >
                      <ArrowRight className="w-3 h-3 text-primary" />
                      {input}
                    </div>
                  ))}
                </div>
              </div>
              <div>
                <div className="flex items-center gap-1.5 text-xs font-medium text-fg-muted mb-2">
                  <FileCheck className="w-3.5 h-3.5 text-success" />
                  输出文件
                </div>
                <div className="space-y-1">
                  {task.outputs.map((output) => (
                    <div
                      key={output}
                      className="flex items-center gap-1.5 text-xs px-2 py-1 rounded font-mono"
                      style={{ background: 'rgba(255,255,255,0.03)', color: '#94A3B8' }}
                    >
                      <CheckCircle2 className="w-3 h-3 text-success" />
                      {output}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </motion.div>
        ))}
      </div>

      {/* Quality Check Summary */}
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.4 }} className="card-df p-6">
        <div className="flex items-center gap-2 mb-4">
          <BarChart3 className="w-5 h-5 text-primary" />
          <h2 className="text-lg font-semibold text-fg">数据质量指标</h2>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { label: '成分股数量', value: '2000', target: '2000' },
            { label: '日线覆盖率', value: '100%', target: '>95%' },
            { label: '指数行情', value: '95行', target: '>90' },
            { label: '失败比例', value: '0%', target: '<20%' },
          ].map((metric) => (
            <div
              key={metric.label}
              className="text-center p-4 rounded-xl"
              style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(30,41,59,0.6)' }}
            >
              <div className="text-2xl font-bold text-fg font-mono">{metric.value}</div>
              <div className="text-xs text-fg-muted mt-1">{metric.label}</div>
              <div className="text-[10px] text-fg-dim mt-0.5">目标: {metric.target}</div>
            </div>
          ))}
        </div>
      </motion.div>
    </div>
  )
}
