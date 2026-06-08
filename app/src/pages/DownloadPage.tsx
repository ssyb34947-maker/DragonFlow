import { useState } from 'react'
import { motion } from 'framer-motion'
import {
  Download,
  Calendar,
  Settings2,
  Play,
  Pause,
  RotateCcw,
  CheckCircle2,
  AlertCircle,
  FileText,
  TrendingUp,
  Database,
  Layers,
} from 'lucide-react'

interface DownloadConfig {
  startDate: string
  endDate: string
  indexCode: string
  adjust: string
  force: boolean
  sleep: number
  skipFundamental: boolean
  limit: number
}

interface DownloadStage {
  id: string
  name: string
  description: string
  status: 'pending' | 'running' | 'success' | 'error'
  progress: number
  detail: string
}

const defaultConfig: DownloadConfig = {
  startDate: '2026-01-01',
  endDate: '2026-05-31',
  indexCode: '932000',
  adjust: 'qfq',
  force: false,
  sleep: 0.3,
  skipFundamental: false,
  limit: 0,
}

const stages: DownloadStage[] = [
  { id: 'constituents', name: '成分股下载', description: '从中证指数/新浪获取成分股列表', status: 'pending', progress: 0, detail: '' },
  { id: 'index-daily', name: '指数行情', description: '下载中证2000指数日K线', status: 'pending', progress: 0, detail: '' },
  { id: 'stock-daily', name: '个股日线', description: '批量下载2000只股票前复权数据', status: 'pending', progress: 0, detail: '' },
  { id: 'stock-info', name: '个股信息', description: '获取总股本、行业、市值等基础信息', status: 'pending', progress: 0, detail: '' },
  { id: 'spot-snapshot', name: '截面快照', description: '获取实时行情快照', status: 'pending', progress: 0, detail: '' },
  { id: 'financial', name: '财务报表', description: '下载利润表/资产负债表/现金流量表', status: 'pending', progress: 0, detail: '' },
]

export default function DownloadPage() {
  const [config, setConfig] = useState<DownloadConfig>(defaultConfig)
  const [downloadStages, setDownloadStages] = useState<DownloadStage[]>(stages)
  const [isRunning, setIsRunning] = useState(false)
  const [showAdvanced, setShowAdvanced] = useState(false)

  const startDownload = async () => {
    setIsRunning(true)
    for (let i = 0; i < downloadStages.length; i++) {
      if (config.skipFundamental && ['stock-info', 'spot-snapshot', 'financial'].includes(downloadStages[i].id)) {
        setDownloadStages((prev) => prev.map((s, idx) => (idx === i ? { ...s, status: 'success', progress: 100, detail: '已跳过' } : s)))
        continue
      }
      setDownloadStages((prev) => prev.map((s, idx) => (idx === i ? { ...s, status: 'running', detail: '正在下载...' } : s)))
      for (let p = 0; p <= 100; p += 5) {
        await new Promise((r) => setTimeout(r, config.sleep * 100))
        setDownloadStages((prev) => prev.map((s, idx) => (idx === i ? { ...s, progress: p } : s)))
      }
      setDownloadStages((prev) => prev.map((s, idx) => (idx === i ? { ...s, status: 'success', progress: 100, detail: '下载完成' } : s)))
    }
    setIsRunning(false)
  }

  const resetStages = () => {
    setDownloadStages(stages)
    setIsRunning(false)
  }

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-fg" style={{ fontFamily: 'var(--font-heading)' }}>数据下载</h1>
        <p className="text-fg-muted mt-1">从AkShare获取中证2000相关数据，支持断点续跑与多源fallback</p>
      </div>

      {/* Config Card */}
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="card-df p-6">
        <div className="flex items-center gap-2 mb-5">
          <Settings2 className="w-5 h-5 text-primary" />
          <h2 className="text-lg font-semibold text-fg">下载配置</h2>
        </div>

        <div className="grid md:grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium text-fg mb-1.5"><Calendar className="w-3.5 h-3.5 inline mr-1 text-primary" />起始日期</label>
            <input type="date" value={config.startDate} onChange={(e) => setConfig({ ...config, startDate: e.target.value })} disabled={isRunning} className="input-df w-full" />
          </div>
          <div>
            <label className="block text-sm font-medium text-fg mb-1.5"><Calendar className="w-3.5 h-3.5 inline mr-1 text-primary" />结束日期</label>
            <input type="date" value={config.endDate} onChange={(e) => setConfig({ ...config, endDate: e.target.value })} disabled={isRunning} className="input-df w-full" />
          </div>
          <div>
            <label className="block text-sm font-medium text-fg mb-1.5"><TrendingUp className="w-3.5 h-3.5 inline mr-1 text-primary" />指数代码</label>
            <input type="text" value={config.indexCode} onChange={(e) => setConfig({ ...config, indexCode: e.target.value })} disabled={isRunning} className="input-df w-full" />
          </div>
        </div>

        <button onClick={() => setShowAdvanced(!showAdvanced)} className="mt-4 text-sm text-primary hover:text-gold font-medium transition-colors">
          {showAdvanced ? '收起高级选项' : '展开高级选项'}
        </button>

        {showAdvanced && (
          <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }} className="grid md:grid-cols-3 gap-4 mt-4 pt-4 sep-df">
            <div>
              <label className="block text-sm font-medium text-fg mb-1.5">复权方式</label>
              <select value={config.adjust} onChange={(e) => setConfig({ ...config, adjust: e.target.value })} disabled={isRunning} className="input-df w-full">
                <option value="qfq">前复权 (qfq)</option>
                <option value="hfq">后复权 (hfq)</option>
                <option value="">不复权</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-fg mb-1.5">请求间隔(秒)</label>
              <input type="number" step={0.1} min={0} max={5} value={config.sleep} onChange={(e) => setConfig({ ...config, sleep: parseFloat(e.target.value) })} disabled={isRunning} className="input-df w-full" />
            </div>
            <div>
              <label className="block text-sm font-medium text-fg mb-1.5">限制数量(0=全部)</label>
              <input type="number" min={0} value={config.limit} onChange={(e) => setConfig({ ...config, limit: parseInt(e.target.value) })} disabled={isRunning} className="input-df w-full" />
            </div>
            <div className="flex items-center gap-3">
              <input type="checkbox" id="force" checked={config.force} onChange={(e) => setConfig({ ...config, force: e.target.checked })} disabled={isRunning} className="w-4 h-4 rounded border-border accent-primary" />
              <label htmlFor="force" className="text-sm text-fg-muted">强制重新下载（忽略已存在文件）</label>
            </div>
            <div className="flex items-center gap-3">
              <input type="checkbox" id="skipFundamental" checked={config.skipFundamental} onChange={(e) => setConfig({ ...config, skipFundamental: e.target.checked })} disabled={isRunning} className="w-4 h-4 rounded border-border accent-primary" />
              <label htmlFor="skipFundamental" className="text-sm text-fg-muted">跳过基本面数据（仅下载行情）</label>
            </div>
          </motion.div>
        )}

        <div className="flex items-center gap-3 mt-6">
          <button onClick={startDownload} disabled={isRunning} className="btn-primary flex items-center gap-2 disabled:opacity-50">
            {isRunning ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
            {isRunning ? '下载中...' : '开始下载'}
          </button>
          <button onClick={resetStages} disabled={isRunning} className="btn-secondary flex items-center gap-2 disabled:opacity-50">
            <RotateCcw className="w-4 h-4" />重置
          </button>
        </div>
      </motion.div>

      {/* Download Stages */}
      <div className="grid md:grid-cols-2 gap-4">
        {downloadStages.map((stage, index) => (
          <motion.div
            key={stage.id}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.05 }}
            className={`card-df p-5 ${
              stage.status === 'running' ? 'border-primary/40 shadow-[0_0_20px_rgba(247,147,26,0.10)]' : ''
            } ${stage.status === 'success' ? 'border-success/30' : ''}`}
          >
            <div className="flex items-start justify-between mb-3">
              <div className="flex items-center gap-3">
                <div
                  className="p-2 rounded-lg flex-shrink-0"
                  style={{
                    background:
                      stage.status === 'success'
                        ? 'rgba(16,185,129,0.10)'
                        : stage.status === 'running'
                        ? 'rgba(247,147,26,0.12)'
                        : 'rgba(255,255,255,0.03)',
                    border:
                      stage.status === 'success'
                        ? '1px solid rgba(16,185,129,0.20)'
                        : stage.status === 'running'
                        ? '1px solid rgba(247,147,26,0.25)'
                        : '1px solid rgba(30,41,59,0.6)',
                  }}
                >
                  {stage.status === 'success' ? (
                    <CheckCircle2 className="w-5 h-5 text-success" />
                  ) : stage.status === 'running' ? (
                    <Download className="w-5 h-5 text-primary animate-bounce" />
                  ) : stage.status === 'error' ? (
                    <AlertCircle className="w-5 h-5 text-danger" />
                  ) : (
                    <Database className="w-5 h-5 text-fg-dim" />
                  )}
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-fg">{stage.name}</h3>
                  <p className="text-xs text-fg-muted">{stage.description}</p>
                </div>
              </div>
              <span className="badge-df">{stage.status === 'pending' ? '待执行' : stage.status === 'running' ? '下载中' : stage.status === 'success' ? '完成' : '失败'}</span>
            </div>

            <div className="space-y-1">
              <div className="h-1.5 rounded-full overflow-hidden" style={{ background: 'rgba(30,41,59,0.6)' }}>
                <motion.div
                  className="h-full rounded-full"
                  style={{ background: stage.status === 'success' ? '#10B981' : 'linear-gradient(90deg, #F7931A, #FFD600)' }}
                  initial={{ width: 0 }}
                  animate={{ width: `${stage.progress}%` }}
                  transition={{ duration: 0.3 }}
                />
              </div>
              <div className="flex items-center justify-between text-xs text-fg-dim font-mono">
                <span>{stage.detail}</span>
                <span>{stage.progress}%</span>
              </div>
            </div>
          </motion.div>
        ))}
      </div>

      {/* Data Preview */}
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.5 }} className="card-df p-6">
        <div className="flex items-center gap-2 mb-4">
          <FileText className="w-5 h-5 text-primary" />
          <h2 className="text-lg font-semibold text-fg">输出文件预览</h2>
        </div>
        <div className="grid md:grid-cols-2 gap-3">
          {[
            { path: 'data/raw/csi2000/constituents_932000_latest.csv', desc: '成分股列表', icon: Layers },
            { path: 'data/raw/csi2000/index_daily_932000_*.csv', desc: '指数行情', icon: TrendingUp },
            { path: 'data/raw/stock_daily/qfq/*.csv', desc: '个股日线(2000文件)', icon: Database },
            { path: 'data/processed/stock_daily_csi2000_qfq_*.csv', desc: '合并长表', icon: FileText },
          ].map((file) => (
            <div
              key={file.path}
              className="flex items-center gap-3 p-3 rounded-lg hover:border-primary/30 transition-colors"
              style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(30,41,59,0.6)' }}
            >
              <file.icon className="w-4 h-4 text-primary flex-shrink-0" />
              <div className="min-w-0">
                <div className="text-xs font-mono text-fg-muted truncate">{file.path}</div>
                <div className="text-xs text-fg-dim">{file.desc}</div>
              </div>
            </div>
          ))}
        </div>
      </motion.div>
    </div>
  )
}
