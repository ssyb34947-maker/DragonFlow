import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Play,
  CheckCircle2,
  XCircle,
  Clock,
  SkipForward,
  ChevronDown,
  ChevronRight,
  Terminal,
  ArrowRight,
  Database,
  Download,
  GitMerge,
  BarChart3,
  FileCheck,
} from 'lucide-react'

interface PipelineStep {
  id: string
  name: string
  description: string
  status: 'pending' | 'running' | 'success' | 'error' | 'skipped'
  progress: number
  icon: React.ElementType
  logs: string[]
  outputs?: string[]
}

const initialSteps: PipelineStep[] = [
  {
    id: 'download-constituents',
    name: '下载成分股',
    description: '从AkShare获取中证2000成分股列表',
    status: 'pending',
    progress: 0,
    icon: Database,
    logs: [],
    outputs: ['data/raw/csi2000/constituents_932000_latest.csv'],
  },
  {
    id: 'download-index',
    name: '下载指数行情',
    description: '获取中证2000指数日行情数据',
    status: 'pending',
    progress: 0,
    icon: Download,
    logs: [],
    outputs: ['data/raw/csi2000/index_daily_932000_*.csv'],
  },
  {
    id: 'download-stock-daily',
    name: '下载个股日线',
    description: '批量下载2000只成分股前复权日线（含fallback机制）',
    status: 'pending',
    progress: 0,
    icon: Download,
    logs: [],
    outputs: ['data/raw/stock_daily/qfq/*.csv'],
  },
  {
    id: 'download-fundamental',
    name: '下载基本面数据',
    description: '获取个股信息、截面快照、财务报表',
    status: 'pending',
    progress: 0,
    icon: Database,
    logs: [],
    outputs: ['data/raw/fundamental/*.csv'],
  },
  {
    id: 'merge-daily',
    name: '合并长表',
    description: '将所有个股CSV合并为统一的长表格式',
    status: 'pending',
    progress: 0,
    icon: GitMerge,
    logs: [],
    outputs: ['data/processed/stock_daily_csi2000_qfq_*.csv'],
  },
  {
    id: 'synthesize-index',
    name: '合成代理指数',
    description: '基于成分股等权重合成中证2000代理指数',
    status: 'pending',
    progress: 0,
    icon: BarChart3,
    logs: [],
    outputs: ['data/processed/index_daily_932000_proxy_equal_weight_*.csv'],
  },
  {
    id: 'synthesize-spot',
    name: '合成截面快照',
    description: '从最后交易日数据合成截面快照',
    status: 'pending',
    progress: 0,
    icon: FileCheck,
    logs: [],
    outputs: ['data/processed/stock_spot_snapshot_csi2000_latest.csv'],
  },
  {
    id: 'quality-check',
    name: '数据质量检查',
    description: '检查覆盖率、缺失值、异常值',
    status: 'pending',
    progress: 0,
    icon: FileCheck,
    logs: [],
    outputs: ['data/processed/data_coverage_report.csv'],
  },
]

const statusConfig = {
  pending: { color: 'text-fg-dim', border: 'border-border', glow: '' },
  running: { color: 'text-primary', border: 'border-primary/40', glow: 'shadow-[0_0_20px_rgba(247,147,26,0.15)]' },
  success: { color: 'text-success', border: 'border-success/30', glow: '' },
  error: { color: 'text-danger', border: 'border-danger/30', glow: '' },
  skipped: { color: 'text-fg-dim', border: 'border-border', glow: '' },
}

const statusLabel: Record<string, string> = {
  pending: '待执行',
  running: '运行中',
  success: '已完成',
  error: '失败',
  skipped: '已跳过',
}

export default function PipelinePage() {
  const [steps, setSteps] = useState<PipelineStep[]>(initialSteps)
  const [expandedStep, setExpandedStep] = useState<string | null>(null)
  const [isRunning, setIsRunning] = useState(false)

  const runStep = async (stepId: string) => {
    setSteps((prev) =>
      prev.map((s) =>
        s.id === stepId ? { ...s, status: 'running', progress: 0, logs: ['开始执行...'] } : s
      )
    )

    for (let i = 0; i <= 100; i += 10) {
      await new Promise((r) => setTimeout(r, 200))
      setSteps((prev) =>
        prev.map((s) =>
          s.id === stepId
            ? { ...s, progress: i, logs: [...s.logs, `进度: ${i}%`] }
            : s
        )
      )
    }

    setSteps((prev) =>
      prev.map((s) =>
        s.id === stepId
          ? { ...s, status: 'success', progress: 100, logs: [...s.logs, '执行完成'] }
          : s
      )
    )
  }

  const runAll = async () => {
    setIsRunning(true)
    for (const step of steps) {
      if (step.status === 'pending') {
        await runStep(step.id)
      }
    }
    setIsRunning(false)
  }

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-fg" style={{ fontFamily: 'var(--font-heading)' }}>
            流程总览
          </h1>
          <p className="text-fg-muted mt-1">DragonFlow 完整数据处理流水线</p>
        </div>
        <button
          onClick={runAll}
          disabled={isRunning}
          className="btn-primary flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <Play className="w-4 h-4" />
          {isRunning ? '运行中...' : '运行全部'}
        </button>
      </div>

      {/* Pipeline Visualization */}
      <div className="card-df p-6 relative overflow-hidden">
        <div className="relative">
          {/* Connection Line */}
          <div
            className="absolute left-6 top-8 bottom-8 w-px"
            style={{ background: 'linear-gradient(180deg, rgba(247,147,26,0.3), rgba(30,41,59,0.5))' }}
          />

          <div className="space-y-4">
            {steps.map((step, index) => {
              const config = statusConfig[step.status]
              const isExpanded = expandedStep === step.id
              const StepIcon = step.icon

              return (
                <motion.div
                  key={step.id}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: index * 0.05 }}
                >
                  <div
                    className={`relative flex items-start gap-4 p-4 rounded-xl border transition-all cursor-pointer ${
                      isExpanded ? 'border-primary/40 bg-primary/[0.04]' : config.border + ' bg-surface hover:border-primary/30'
                    } ${config.glow}`}
                    onClick={() => setExpandedStep(isExpanded ? null : step.id)}
                  >
                    {/* Status Icon */}
                    <div
                      className="relative z-10 flex items-center justify-center w-12 h-12 rounded-xl flex-shrink-0"
                      style={{
                        background:
                          step.status === 'running'
                            ? 'rgba(247,147,26,0.12)'
                            : step.status === 'success'
                            ? 'rgba(16,185,129,0.10)'
                            : 'rgba(255,255,255,0.03)',
                        border:
                          step.status === 'running'
                            ? '1px solid rgba(247,147,26,0.25)'
                            : step.status === 'success'
                            ? '1px solid rgba(16,185,129,0.20)'
                            : '1px solid rgba(30,41,59,0.6)',
                      }}
                    >
                      <StepIcon className={`w-6 h-6 ${config.color}`} />
                      {step.status === 'running' && (
                        <div className="absolute inset-0 rounded-xl border border-primary animate-ping opacity-20" />
                      )}
                    </div>

                    {/* Content */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-3">
                        <h3 className="text-base font-semibold text-fg">{step.name}</h3>
                        <span className="badge-df">{statusLabel[step.status]}</span>
                        {step.outputs && (
                          <span className="text-xs text-fg-dim">{step.outputs.length} 个输出</span>
                        )}
                      </div>
                      <p className="text-sm text-fg-muted mt-1">{step.description}</p>

                      {/* Progress Bar */}
                      {step.status === 'running' && (
                        <div className="mt-3">
                          <div className="h-1.5 rounded-full overflow-hidden" style={{ background: 'rgba(30,41,59,0.6)' }}>
                            <motion.div
                              className="h-full rounded-full"
                              style={{ background: 'linear-gradient(90deg, #F7931A, #FFD600)' }}
                              initial={{ width: 0 }}
                              animate={{ width: `${step.progress}%` }}
                              transition={{ duration: 0.3 }}
                            />
                          </div>
                          <span className="text-xs text-fg-dim mt-1 font-mono">{step.progress}%</span>
                        </div>
                      )}
                    </div>

                    {/* Actions */}
                    <div className="flex items-center gap-2 flex-shrink-0">
                      {step.status === 'pending' && (
                        <button
                          onClick={(e) => {
                            e.stopPropagation()
                            runStep(step.id)
                          }}
                          disabled={isRunning}
                          className="p-2 rounded-lg hover:bg-primary/10 text-primary transition-colors"
                        >
                          <Play className="w-4 h-4" />
                        </button>
                      )}
                      {isExpanded ? (
                        <ChevronDown className="w-5 h-5 text-fg-dim" />
                      ) : (
                        <ChevronRight className="w-5 h-5 text-fg-dim" />
                      )}
                    </div>
                  </div>

                  {/* Expanded Details */}
                  <AnimatePresence>
                    {isExpanded && (
                      <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: 'auto', opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        transition={{ duration: 0.2 }}
                        className="overflow-hidden"
                      >
                        <div
                          className="ml-16 mt-2 p-4 rounded-xl border"
                          style={{
                            background: 'rgba(0,0,0,0.25)',
                            borderColor: 'rgba(30,41,59,0.8)',
                          }}
                        >
                          {/* Logs */}
                          {step.logs.length > 0 && (
                            <div className="mb-4">
                              <div className="flex items-center gap-2 text-sm font-medium text-fg mb-2">
                                <Terminal className="w-4 h-4 text-primary" />
                                执行日志
                              </div>
                              <div
                                className="rounded-lg p-3 max-h-40 overflow-auto font-mono text-xs"
                                style={{ background: '#030304', border: '1px solid rgba(30,41,59,0.6)' }}
                              >
                                {step.logs.map((log, i) => (
                                  <div key={i} className="text-success">
                                    <span className="text-fg-dim">[{new Date().toLocaleTimeString()}]</span>{' '}
                                    {log}
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}

                          {/* Outputs */}
                          {step.outputs && step.outputs.length > 0 && (
                            <div>
                              <div className="flex items-center gap-2 text-sm font-medium text-fg mb-2">
                                <FileCheck className="w-4 h-4 text-primary" />
                                输出文件
                              </div>
                              <div className="space-y-1">
                                {step.outputs.map((output, i) => (
                                  <div
                                    key={i}
                                    className="flex items-center gap-2 text-xs text-fg-muted px-3 py-2 rounded-lg font-mono"
                                    style={{ background: 'rgba(255,255,255,0.03)' }}
                                  >
                                    <ArrowRight className="w-3 h-3 text-primary" />
                                    {output}
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </motion.div>
              )
            })}
          </div>
        </div>
      </div>
    </div>
  )
}
