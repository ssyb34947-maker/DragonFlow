import { motion } from 'framer-motion'
import { Link } from 'react-router-dom'
import {
  Download,
  Database,
  BarChart3,
  GitBranch,
  Search,
  ArrowRight,
  TrendingUp,
  Layers,
  Zap,
  Shield,
  BrainCircuit,
} from 'lucide-react'

const features = [
  {
    icon: Download,
    title: '数据下载',
    desc: '从AkShare自动获取中证2000成分股、指数行情、个股日线、基本面数据',
    path: '/download',
  },
  {
    icon: Database,
    title: '数据预处理',
    desc: '合并长表、合成代理指数、生成截面快照、数据质量检查',
    path: '/process',
  },
  {
    icon: BarChart3,
    title: '分析算法',
    desc: '收益率/波动率计算、PCA降维、聚类分析、龙头股识别',
    path: '/analysis',
  },
  {
    icon: BrainCircuit,
    title: '模型方案',
    desc: 'DragonFlow-KronosGraph：KS-TFT模型、K线分词、谱聚类嵌入与回测架构',
    path: '/model',
  },
  {
    icon: Search,
    title: '数据探索',
    desc: '交互式浏览K线图、成分股分布、覆盖率报告、数据质量监控',
    path: '/explorer',
  },
]

const stats = [
  { label: '成分股', value: '2000', icon: Layers },
  { label: '数据维度', value: '15+', icon: Database },
  { label: '分析算法', value: '8+', icon: Zap },
  { label: '时间跨度', value: '2026.1-5', icon: TrendingUp },
]

const pipelineSteps = [
  '下载成分股',
  '下载指数行情',
  '下载个股日线',
  '下载基本面',
  '合并长表',
  '合成代理指数',
  '数据质量检查',
  '可视化分析',
]

export default function HomePage() {
  return (
    <div className="max-w-6xl mx-auto space-y-14">
      {/* Hero */}
      <section className="text-center py-10 relative">
        {/* Decorative glow */}
        <div
          className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[300px] pointer-events-none"
          style={{
            background: 'radial-gradient(ellipse, rgba(247,147,26,0.08) 0%, transparent 70%)',
          }}
        />

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="relative z-10"
        >
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full badge-df mb-6">
            <Shield className="w-3.5 h-3.5 text-primary" />
            <span>西南财经大学 · 数据可视化课程项目</span>
          </div>
          <h1
            className="text-6xl font-bold mb-4 tracking-tight"
            style={{
              fontFamily: 'var(--font-heading)',
              background: 'linear-gradient(135deg, #FFFFFF 0%, #F7931A 60%, #FFD600 100%)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
            }}
          >
            DragonFlow
          </h1>
          <p className="text-lg text-fg-muted max-w-2xl mx-auto leading-relaxed">
            A股龙头/热点股数据可视化分析系统。帮助用户快速复盘过往市场走势，
            识别热点板块与龙头股。
          </p>
        </motion.div>

        {/* Stats */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.2 }}
          className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-10"
        >
          {stats.map((s, i) => (
            <motion.div
              key={s.label}
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.3 + i * 0.1 }}
              className="card-df p-5 text-center"
            >
              <div
                className="w-10 h-10 rounded-xl flex items-center justify-center mx-auto mb-3"
                style={{
                  background: 'linear-gradient(135deg, rgba(247,147,26,0.15) 0%, rgba(234,88,12,0.08) 100%)',
                  border: '1px solid rgba(247,147,26,0.20)',
                }}
              >
                <s.icon className="w-5 h-5 text-primary" />
              </div>
              <div className="text-2xl font-bold text-fg font-mono">{s.value}</div>
              <div className="text-xs text-fg-muted mt-1 uppercase tracking-wider">{s.label}</div>
            </motion.div>
          ))}
        </motion.div>
      </section>

      {/* Quick Start */}
      <section>
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-bold text-fg" style={{ fontFamily: 'var(--font-heading)' }}>
            功能模块
          </h2>
          <Link
            to="/pipeline"
            className="flex items-center gap-1 text-primary hover:text-gold text-sm font-medium transition-colors"
          >
            <GitBranch className="w-4 h-4" />
            查看完整流程
            <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
        <div className="grid md:grid-cols-2 gap-4">
          {features.map((f, i) => (
            <motion.div
              key={f.title}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.4 + i * 0.1 }}
            >
              <Link to={f.path} className="card-df flex items-start gap-4 p-5 group block">
                <div
                  className="text-white p-2.5 rounded-xl flex-shrink-0"
                  style={{
                    background: 'linear-gradient(135deg, #F7931A 0%, #EA580C 100%)',
                    boxShadow: '0 4px 16px rgba(247,147,26,0.25)',
                  }}
                >
                  <f.icon className="w-6 h-6" />
                </div>
                <div className="flex-1 min-w-0">
                  <h3 className="text-lg font-semibold text-fg group-hover:text-primary transition-colors">
                    {f.title}
                  </h3>
                  <p className="text-sm text-fg-muted mt-1 leading-relaxed">{f.desc}</p>
                </div>
                <ArrowRight className="w-5 h-5 text-fg-dim group-hover:text-primary group-hover:translate-x-1 transition-all flex-shrink-0 mt-1" />
              </Link>
            </motion.div>
          ))}
        </div>
      </section>

      {/* Pipeline Preview */}
      <section className="card-df p-8 relative overflow-hidden">
        {/* Subtle glow */}
        <div
          className="absolute -top-20 -right-20 w-64 h-64 pointer-events-none"
          style={{
            background: 'radial-gradient(circle, rgba(247,147,26,0.06) 0%, transparent 70%)',
          }}
        />

        <h2 className="text-2xl font-bold text-fg mb-6 relative z-10" style={{ fontFamily: 'var(--font-heading)' }}>
          项目流程概览
        </h2>
        <div className="flex flex-wrap items-center gap-2 relative z-10">
          {pipelineSteps.map((step, i) => (
            <div key={step} className="flex items-center gap-2">
              <motion.div
                initial={{ opacity: 0, scale: 0 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: 0.6 + i * 0.08 }}
                className="flex items-center gap-2 px-4 py-2 rounded-xl"
                style={{
                  background: 'rgba(255,255,255,0.03)',
                  border: '1px solid rgba(30,41,59,0.8)',
                }}
              >
                <span
                  className="w-5 h-5 rounded-full text-xs font-bold flex items-center justify-center flex-shrink-0"
                  style={{
                    background: 'rgba(247,147,26,0.12)',
                    color: '#F7931A',
                    border: '1px solid rgba(247,147,26,0.25)',
                  }}
                >
                  {i + 1}
                </span>
                <span className="text-sm font-medium text-fg">{step}</span>
              </motion.div>
              {i < pipelineSteps.length - 1 && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: 0.7 + i * 0.08 }}
                >
                  <ArrowRight className="w-4 h-4 text-fg-dim" />
                </motion.div>
              )}
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}
