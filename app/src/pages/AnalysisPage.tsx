import { useState } from 'react'
import { motion } from 'framer-motion'
import {
  BarChart3,
  TrendingUp,
  Activity,
  PieChart,
  GitBranch,
  Play,
  Settings2,
  Info,
} from 'lucide-react'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  AreaChart,
  Area,
  BarChart,
  Bar,
  ScatterChart,
  Scatter,
  ZAxis,
} from 'recharts'

interface AnalysisMethod {
  id: string
  name: string
  description: string
  icon: React.ElementType
  category: string
}

const methods: AnalysisMethod[] = [
  {
    id: 'returns',
    name: '收益率分析',
    description: '计算个股/指数的日收益率、累计收益率',
    icon: TrendingUp,
    category: '基础统计',
  },
  {
    id: 'volatility',
    name: '波动率分析',
    description: '滚动窗口波动率、GARCH模型估计',
    icon: Activity,
    category: '基础统计',
  },
  {
    id: 'correlation',
    name: '相关性矩阵',
    description: '个股间收益率相关性热力图',
    icon: GitBranch,
    category: '基础统计',
  },
  {
    id: 'pca',
    name: 'PCA降维',
    description: '主成分分析，提取市场主要因子',
    icon: PieChart,
    category: '机器学习',
  },
  {
    id: 'clustering',
    name: '聚类分析',
    description: 'K-Means聚类识别相似股票群体',
    icon: GitBranch,
    category: '机器学习',
  },
  {
    id: 'leaders',
    name: '龙头股识别',
    description: '基于涨幅、成交量、相关性识别龙头',
    icon: TrendingUp,
    category: '主题分析',
  },
]

// Mock data for charts
const indexData = Array.from({ length: 30 }, (_, i) => ({
  date: `2026-01-${String(i + 1).padStart(2, '0')}`,
  official: 2500 + Math.sin(i * 0.3) * 100 + i * 5,
  proxy: 2500 + Math.sin(i * 0.3 + 0.1) * 95 + i * 4.8,
}))

const returnDistData = Array.from({ length: 50 }, (_, i) => ({
  stock: `股票${i + 1}`,
  return: (Math.random() - 0.3) * 40,
  volatility: Math.random() * 30 + 5,
}))

const sectorData = [
  { name: '科技', value: 35, count: 420 },
  { name: '医药', value: 20, count: 240 },
  { name: '消费', value: 18, count: 216 },
  { name: '制造', value: 15, count: 180 },
  { name: '金融', value: 8, count: 96 },
  { name: '其他', value: 4, count: 48 },
]

export default function AnalysisPage() {
  const [selectedMethod, setSelectedMethod] = useState<string>('returns')
  const [isAnalyzing, setIsAnalyzing] = useState(false)

  const runAnalysis = async () => {
    setIsAnalyzing(true)
    await new Promise((r) => setTimeout(r, 1500))
    setIsAnalyzing(false)
  }

  const selectedMethodData = methods.find((m) => m.id === selectedMethod)

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div>
        <h1
          className="text-3xl font-bold tracking-tight"
          style={{
            fontFamily: 'var(--font-heading)',
            background: 'linear-gradient(135deg, #FFFFFF 0%, #F7931A 60%, #FFD600 100%)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
          }}
        >
          分析算法
        </h1>
        <p className="text-fg-muted mt-1">数据可视化分析与机器学习算法</p>
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        {/* Method Selector */}
        <div className="lg:col-span-1 space-y-3">
          <div className="flex items-center gap-2 mb-3">
            <Settings2 className="w-4 h-4 text-primary" />
            <span className="text-sm font-medium text-fg">选择分析方法</span>
          </div>
          {methods.map((method) => {
            const Icon = method.icon
            return (
              <motion.button
                key={method.id}
                whileHover={{ scale: 1.01 }}
                whileTap={{ scale: 0.99 }}
                onClick={() => setSelectedMethod(method.id)}
                className={`w-full flex items-start gap-3 p-3 rounded-xl border text-left transition-all ${
                  selectedMethod === method.id
                    ? 'border-primary/40 bg-primary/[0.04]'
                    : 'border-white/10 bg-surface hover:border-primary/30'
                }`}
              >
                <div
                  className={`p-1.5 rounded-lg flex-shrink-0 ${
                    selectedMethod === method.id
                      ? 'bg-primary/15 border border-primary/20'
                      : 'bg-white/[0.03] border border-white/5'
                  }`}
                >
                  <Icon
                    className={`w-4 h-4 ${
                      selectedMethod === method.id ? 'text-primary' : 'text-fg-dim'
                    }`}
                  />
                </div>
                <div className="min-w-0">
                  <div className="text-sm font-medium text-fg">{method.name}</div>
                  <div className="text-xs text-fg-muted mt-0.5">{method.description}</div>
                  <span
                    className="inline-block mt-1.5 text-[10px] px-1.5 py-0.5 rounded"
                    style={{
                      background: 'rgba(255,255,255,0.04)',
                      border: '1px solid rgba(255,255,255,0.06)',
                      color: '#94A3B8',
                    }}
                  >
                    {method.category}
                  </span>
                </div>
              </motion.button>
            )
          })}
        </div>

        {/* Analysis Panel */}
        <div className="lg:col-span-2 space-y-4">
          <div className="card-df p-5">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="text-lg font-semibold text-fg">{selectedMethodData?.name}</h2>
                <p className="text-sm text-fg-muted">{selectedMethodData?.description}</p>
              </div>
              <button
                onClick={runAnalysis}
                disabled={isAnalyzing}
                className="btn-primary flex items-center gap-2 disabled:opacity-50 text-sm"
              >
                <Play className="w-3.5 h-3.5" />
                {isAnalyzing ? '分析中...' : '运行分析'}
              </button>
            </div>

            {/* Chart Area */}
            {selectedMethod === 'returns' && (
              <div className="space-y-4">
                <div className="h-72">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={indexData}>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(30,41,59,0.6)" />
                      <XAxis dataKey="date" tick={{ fontSize: 11, fill: '#94A3B8' }} />
                      <YAxis tick={{ fontSize: 11, fill: '#94A3B8' }} />
                      <Tooltip
                        contentStyle={{
                          background: '#0F1115',
                          border: '1px solid rgba(30,41,59,0.8)',
                          borderRadius: '8px',
                          fontSize: '12px',
                          color: '#FFFFFF',
                        }}
                      />
                      <Legend
                        wrapperStyle={{ color: '#94A3B8' }}
                      />
                      <Line
                        type="monotone"
                        dataKey="official"
                        name="官方指数"
                        stroke="#F7931A"
                        strokeWidth={2}
                        dot={false}
                      />
                      <Line
                        type="monotone"
                        dataKey="proxy"
                        name="代理指数"
                        stroke="#FFD600"
                        strokeWidth={2}
                        strokeDasharray="5 5"
                        dot={false}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
                <div className="grid grid-cols-3 gap-3">
                  {[
                    { label: '区间收益', value: '+12.5%' },
                    { label: '最大回撤', value: '-8.3%' },
                    { label: '夏普比率', value: '1.45' },
                  ].map((stat) => (
                    <div
                      key={stat.label}
                      className="text-center p-3 rounded-xl"
                      style={{
                        background: 'rgba(255,255,255,0.03)',
                        border: '1px solid rgba(30,41,59,0.6)',
                      }}
                    >
                      <div className="text-lg font-bold text-fg font-mono">{stat.value}</div>
                      <div className="text-xs text-fg-muted">{stat.label}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {selectedMethod === 'volatility' && (
              <div className="h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={indexData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(30,41,59,0.6)" />
                    <XAxis dataKey="date" tick={{ fontSize: 11, fill: '#94A3B8' }} />
                    <YAxis tick={{ fontSize: 11, fill: '#94A3B8' }} />
                    <Tooltip
                      contentStyle={{
                        background: '#0F1115',
                        border: '1px solid rgba(30,41,59,0.8)',
                        borderRadius: '8px',
                        fontSize: '12px',
                        color: '#FFFFFF',
                      }}
                    />
                    <Area
                      type="monotone"
                      dataKey="official"
                      name="滚动波动率"
                      stroke="#EA580C"
                      fill="#EA580C"
                      fillOpacity={0.15}
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            )}

            {selectedMethod === 'pca' && (
              <div className="space-y-4">
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={sectorData}>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(30,41,59,0.6)" />
                      <XAxis dataKey="name" tick={{ fontSize: 11, fill: '#94A3B8' }} />
                      <YAxis tick={{ fontSize: 11, fill: '#94A3B8' }} />
                      <Tooltip
                        contentStyle={{
                          background: '#0F1115',
                          border: '1px solid rgba(30,41,59,0.8)',
                          borderRadius: '8px',
                          fontSize: '12px',
                          color: '#FFFFFF',
                        }}
                      />
                      <Bar
                        dataKey="value"
                        name="方差解释率(%)"
                        fill="url(#barGradient)"
                        radius={[4, 4, 0, 0]}
                      />
                      <defs>
                        <linearGradient id="barGradient" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="0%" stopColor="#F7931A" />
                          <stop offset="100%" stopColor="#EA580C" />
                        </linearGradient>
                      </defs>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
                <div
                  className="flex items-start gap-2 p-3 rounded-lg text-sm"
                  style={{
                    background: 'rgba(247,147,26,0.06)',
                    border: '1px solid rgba(247,147,26,0.15)',
                    color: '#F7931A',
                  }}
                >
                  <Info className="w-4 h-4 flex-shrink-0 mt-0.5" />
                  <span>前3个主成分解释了总方差的 68.5%，可用于降维和因子分析</span>
                </div>
              </div>
            )}

            {selectedMethod === 'clustering' && (
              <div className="h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <ScatterChart>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(30,41,59,0.6)" />
                    <XAxis
                      type="number"
                      dataKey="return"
                      name="收益率"
                      tick={{ fontSize: 11, fill: '#94A3B8' }}
                      unit="%"
                    />
                    <YAxis
                      type="number"
                      dataKey="volatility"
                      name="波动率"
                      tick={{ fontSize: 11, fill: '#94A3B8' }}
                      unit="%"
                    />
                    <ZAxis type="number" dataKey="volatility" range={[50, 200]} />
                    <Tooltip
                      cursor={{ strokeDasharray: '3 3' }}
                      contentStyle={{
                        background: '#0F1115',
                        border: '1px solid rgba(30,41,59,0.8)',
                        borderRadius: '8px',
                        fontSize: '12px',
                        color: '#FFFFFF',
                      }}
                    />
                    <Scatter name="股票" data={returnDistData} fill="#F7931A" />
                  </ScatterChart>
                </ResponsiveContainer>
              </div>
            )}

            {(selectedMethod === 'correlation' || selectedMethod === 'leaders') && (
              <div className="flex items-center justify-center h-72 text-fg-dim">
                <div className="text-center">
                  <BarChart3 className="w-12 h-12 mx-auto mb-3 opacity-30" />
                  <p>点击"运行分析"生成结果</p>
                </div>
              </div>
            )}
          </div>

          {/* Method Info */}
          <div className="card-df p-5">
            <h3 className="text-sm font-semibold text-fg mb-3">算法说明</h3>
            <div className="space-y-2 text-sm text-fg-muted">
              {selectedMethod === 'returns' && (
                <>
                  <p>{`1. 计算日收益率: r_t = (P_t - P_{t-1}) / P_{t-1}`}</p>
                  <p>{`2. 累计收益率: R_t = ∏(1 + r_i) - 1`}</p>
                  <p>3. 对比官方指数与等权代理指数的走势差异</p>
                </>
              )}
              {selectedMethod === 'volatility' && (
                <>
                  <p>1. 滚动窗口标准差估计实现波动率</p>
                  <p>2. 支持GARCH(1,1)模型进行波动率预测</p>
                  <p>3. 识别高波动时期与风险聚集</p>
                </>
              )}
              {selectedMethod === 'pca' && (
                <>
                  <p>1. 对收益率矩阵进行标准化</p>
                  <p>2. 计算协方差矩阵并特征分解</p>
                  <p>3. 提取前K个主成分作为市场因子</p>
                </>
              )}
              {selectedMethod === 'clustering' && (
                <>
                  <p>1. 基于收益率特征构建特征向量</p>
                  <p>2. K-Means++初始化聚类中心</p>
                  <p>3. silhouette score 评估聚类质量</p>
                </>
              )}
              {selectedMethod === 'correlation' && (
                <>
                  <p>1. 计算个股间收益率的Pearson相关系数</p>
                  <p>2. 构建相关性矩阵并可视化热力图</p>
                  <p>3. 识别高度相关的股票群体</p>
                </>
              )}
              {selectedMethod === 'leaders' && (
                <>
                  <p>1. 综合涨幅、成交量、市场关注度评分</p>
                  <p>2. 计算个股与板块指数的超额收益</p>
                  <p>3. 识别阶段性龙头与热点切换</p>
                </>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
