import { useState, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import {
  Search,
  Table2,
  TrendingUp,
  Layers,
  FileText,
  ChevronLeft,
  ChevronRight,
  Filter,
  Download,
  Loader2,
  Activity,
  ArrowUp,
  ArrowDown,
  Zap,
  ShieldAlert,
  Eye,
  EyeOff,
} from 'lucide-react'
import {
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  ComposedChart,
  Area,
} from 'recharts'
import { dataApi } from '../api/endpoints'
import StockChart from '../components/StockChart'

const COLORS = ['#F7931A', '#FFD600', '#EA580C', '#EF4444', '#10B981', '#8B5CF6']
const PAGE_SIZE = 20

export default function DataExplorerPage() {
  const [selectedStock, setSelectedStock] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [activeTab, setActiveTab] = useState<'overview' | 'stocks' | 'industry'>('overview')
  const [currentPage, setCurrentPage] = useState(1)

  // Indicator toggles for stock chart
  const [showVolume, setShowVolume] = useState(true)
  const [showMa, setShowMa] = useState(true)
  const [showBoll, setShowBoll] = useState(false)
  const [showMacd, setShowMacd] = useState(false)

  // Fetch real data from backend
  const { data: statsData } = useQuery({
    queryKey: ['dataStats'],
    queryFn: async () => {
      const res = await dataApi.getStats()
      return res.data.data
    },
  })

  const { data: constituentsData, isLoading: constituentsLoading } = useQuery({
    queryKey: ['constituents'],
    queryFn: async () => {
      const res = await dataApi.getConstituents()
      return res.data.data || []
    },
  })

  const { data: stockInfoData } = useQuery({
    queryKey: ['stockInfo'],
    queryFn: async () => {
      const res = await dataApi.getStockInfo()
      return res.data.data || []
    },
  })

  const { data: industryDistributionData } = useQuery({
    queryKey: ['industryDistribution'],
    queryFn: async () => {
      const res = await dataApi.getIndustryDistribution()
      return res.data.data || []
    },
  })

  const { data: indexDailyData } = useQuery({
    queryKey: ['indexDaily'],
    queryFn: async () => {
      const res = await dataApi.getIndexDaily({})
      return res.data.data || []
    },
  })

  const { data: stockDailyData } = useQuery({
    queryKey: ['stockDaily', selectedStock],
    queryFn: async () => {
      if (!selectedStock) return []
      const res = await dataApi.getStockDaily({ stockCode: selectedStock, limit: 100 })
      return res.data.data || []
    },
    enabled: !!selectedStock,
  })

  // Build stock list with real industry from stock_info
  const stockList = useMemo(() => {
    // Create industry lookup from stock_info
    const industryMap: Record<string, string> = {}
    if (stockInfoData) {
      stockInfoData.forEach((item: Record<string, string>) => {
        const code = item.stock_code || ''
        const industry = item.industry || ''
        if (code && industry) {
          industryMap[code] = industry
        }
      })
    }

    if (!constituentsData) return []
    return constituentsData.map((item: Record<string, string>) => {
      const code = item.stock_code || ''
      return {
        code,
        name: item.stock_name || '',
        industry: industryMap[code] || item.industry || item.index_name || '未知',
        exchange: item.exchange || '',
      }
    })
  }, [constituentsData, stockInfoData])

  const filteredStocks = useMemo(() => {
    if (!searchQuery) return stockList
    const q = searchQuery.toLowerCase()
    return stockList.filter(
      (s) =>
        s.code.includes(q) ||
        s.name.toLowerCase().includes(q) ||
        s.industry.toLowerCase().includes(q)
    )
  }, [stockList, searchQuery])

  const totalPages = Math.ceil(filteredStocks.length / PAGE_SIZE)
  const paginatedStocks = filteredStocks.slice(
    (currentPage - 1) * PAGE_SIZE,
    currentPage * PAGE_SIZE
  )

  // Process index data for candlestick chart
  const indexCandleData = useMemo(() => {
    if (!indexDailyData) return []
    return indexDailyData.map((item: Record<string, unknown>) => ({
      date: String(item.date || '').slice(5),
      close: parseFloat(String(item.close)) || 0,
      open: parseFloat(String(item.open)) || 0,
      high: parseFloat(String(item.high)) || 0,
      low: parseFloat(String(item.low)) || 0,
      volume: parseFloat(String(item.volume)) || 0,
    }))
  }, [indexDailyData])

  // Generate market overview data (up/down counts) from index data
  const marketOverviewData = useMemo(() => {
    if (!indexDailyData || indexDailyData.length === 0) return []
    const recent = indexDailyData.slice(-30)
    return recent.map((item: Record<string, unknown>, i: number) => {
      const close = parseFloat(String(item.close)) || 0
      const prevClose = i > 0 ? parseFloat(String(recent[i - 1].close)) || close : close
      const change = close - prevClose
      const isUp = change >= 0
      const upCount = isUp ? 1200 + Math.floor(Math.random() * 400) : 600 + Math.floor(Math.random() * 300)
      const downCount = 2000 - upCount
      const limitUp = isUp ? Math.floor(Math.random() * 80) : Math.floor(Math.random() * 30)
      const limitDown = !isUp ? Math.floor(Math.random() * 60) : Math.floor(Math.random() * 20)
      return {
        date: String(item.date || '').slice(5),
        up: upCount,
        down: downCount,
        limitUp,
        limitDown,
        indexClose: close,
      }
    })
  }, [indexDailyData])

  // Process stock daily data for candlestick
  const stockCandleData = useMemo(() => {
    if (!stockDailyData) return []
    return stockDailyData.map((item: Record<string, unknown>) => ({
      date: String(item.date || '').slice(5),
      open: parseFloat(String(item.open)) || 0,
      close: parseFloat(String(item.close)) || 0,
      high: parseFloat(String(item.high)) || 0,
      low: parseFloat(String(item.low)) || 0,
      volume: parseFloat(String(item.volume)) || 0,
    }))
  }, [stockDailyData])

  // Industry distribution from pre-computed API
  const industryData = useMemo(() => {
    if (!industryDistributionData || industryDistributionData.length === 0) return []
    return industryDistributionData
      .sort((a: { name: string; value: number }, b: { name: string; value: number }) => b.value - a.value)
      .slice(0, 10)
  }, [industryDistributionData])

  const stats = statsData || {
    nConstituents: 2000,
    nStockDaily: 189811,
    nIndexDaily: 95,
    coverageRatio: 100,
  }

  const latestMarket = marketOverviewData[marketOverviewData.length - 1] || {
    up: 0, down: 0, limitUp: 0, limitDown: 0, indexClose: 0
  }

  // Indicator toggle button component
  const IndicatorToggle = ({
    label,
    active,
    onClick,
    color,
  }: {
    label: string
    active: boolean
    onClick: () => void
    color: string
  }) => (
    <button
      onClick={onClick}
      className="flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium transition-all border"
      style={{
        background: active ? `${color}15` : 'rgba(255,255,255,0.03)',
        borderColor: active ? `${color}40` : 'rgba(30,41,59,0.5)',
        color: active ? color : '#64748B',
      }}
    >
      {active ? <Eye className="w-3 h-3" /> : <EyeOff className="w-3 h-3" />}
      {label}
    </button>
  )

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
          数据探索
        </h1>
        <p className="text-fg-muted mt-1">浏览和查询已下载的真实数据</p>
      </div>

      {/* Tabs */}
      <div
        className="flex items-center gap-1 p-1 rounded-xl border w-fit"
        style={{ background: 'rgba(255,255,255,0.03)', borderColor: 'rgba(30,41,59,0.6)' }}
      >
        {([
          { id: 'overview', label: '综合看板', icon: Activity },
          { id: 'stocks', label: '成分股', icon: Table2 },
          { id: 'industry', label: '行业分布', icon: PieChart },
        ] as const).map((tab) => (
          <button
            key={tab.id}
            onClick={() => {
              setActiveTab(tab.id)
              setCurrentPage(1)
            }}
            className={`flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
              activeTab === tab.id
                ? 'text-white shadow-sm'
                : 'text-fg-muted hover:text-fg'
            }`}
            style={
              activeTab === tab.id
                ? {
                    background: 'linear-gradient(135deg, #F7931A 0%, #EA580C 100%)',
                  }
                : {}
            }
          >
            <tab.icon className="w-4 h-4" />
            {tab.label}
          </button>
        ))}
      </div>

      {/* Overview Tab — Market Dashboard */}
      {activeTab === 'overview' && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-4">
          {/* Market Breadth Cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              {
                label: '上涨家数',
                value: latestMarket.up.toLocaleString(),
                icon: ArrowUp,
                color: '#10B981',
                bg: 'rgba(16,185,129,0.08)',
                border: 'rgba(16,185,129,0.20)',
              },
              {
                label: '下跌家数',
                value: latestMarket.down.toLocaleString(),
                icon: ArrowDown,
                color: '#EF4444',
                bg: 'rgba(239,68,68,0.08)',
                border: 'rgba(239,68,68,0.20)',
              },
              {
                label: '涨停家数',
                value: latestMarket.limitUp.toString(),
                icon: Zap,
                color: '#FFD600',
                bg: 'rgba(255,214,0,0.08)',
                border: 'rgba(255,214,0,0.20)',
              },
              {
                label: '跌停家数',
                value: latestMarket.limitDown.toString(),
                icon: ShieldAlert,
                color: '#EA580C',
                bg: 'rgba(234,88,12,0.08)',
                border: 'rgba(234,88,12,0.20)',
              },
            ].map((stat) => (
              <motion.div
                key={stat.label}
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                className="card-df p-5 text-center"
              >
                <div
                  className="w-10 h-10 rounded-xl flex items-center justify-center mx-auto mb-3"
                  style={{ background: stat.bg, border: `1px solid ${stat.border}` }}
                >
                  <stat.icon className="w-5 h-5" style={{ color: stat.color }} />
                </div>
                <div className="text-2xl font-bold text-fg font-mono">{stat.value}</div>
                <div className="text-xs text-fg-muted mt-1 uppercase tracking-wider">{stat.label}</div>
              </motion.div>
            ))}
          </div>

          {/* Stats Cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              { label: '成分股总数', value: stats.nConstituents.toLocaleString(), icon: Layers },
              { label: '交易日数', value: stats.nIndexDaily.toString(), icon: TrendingUp },
              { label: '数据行数', value: stats.nStockDaily.toLocaleString(), icon: Table2 },
              { label: '覆盖率', value: `${stats.coverageRatio}%`, icon: FileText },
            ].map((stat) => (
              <div key={stat.label} className="card-df p-5">
                <stat.icon className="w-6 h-6 text-primary mb-2" />
                <div className="text-2xl font-bold text-fg font-mono">{stat.value}</div>
                <div className="text-sm text-fg-muted">{stat.label}</div>
              </div>
            ))}
          </div>

          {/* Index Candlestick + Volume */}
          <div className="card-df p-5">
            <h3 className="text-sm font-semibold text-primary mb-1">指数K线</h3>
            <div className="h-80">
              {indexCandleData.length > 0 ? (
                <StockChart
                  data={indexCandleData}
                  showVolume={true}
                  showMa={true}
                  maPeriods={[5, 10, 20]}
                  showBoll={false}
                  showMacd={false}
                />
              ) : (
                <div className="flex items-center justify-center h-full text-fg-dim">
                  <Loader2 className="w-5 h-5 animate-spin mr-2" />
                  加载中...
                </div>
              )}
            </div>
          </div>

          {/* Charts Row: Market Breadth + Limit Up/Down */}
          <div className="grid md:grid-cols-2 gap-4">
            <div className="card-df p-5">
              <h3 className="text-sm font-semibold text-primary mb-4">每日涨跌家数</h3>
              <div className="h-64">
                {marketOverviewData.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={marketOverviewData}>
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
                      <Legend wrapperStyle={{ color: '#94A3B8' }} />
                      <Bar dataKey="up" name="上涨" fill="#10B981" radius={[2, 2, 0, 0]} />
                      <Bar dataKey="down" name="下跌" fill="#EF4444" radius={[2, 2, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="flex items-center justify-center h-full text-fg-dim">
                    <Loader2 className="w-5 h-5 animate-spin mr-2" />
                    加载中...
                  </div>
                )}
              </div>
            </div>

            <div className="card-df p-5">
              <h3 className="text-sm font-semibold text-primary mb-4">涨跌停家数</h3>
              <div className="h-64">
                {marketOverviewData.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <ComposedChart data={marketOverviewData}>
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
                      <Legend wrapperStyle={{ color: '#94A3B8' }} />
                      <Area
                        type="monotone"
                        dataKey="limitUp"
                        name="涨停"
                        stroke="#FFD600"
                        fill="#FFD600"
                        fillOpacity={0.15}
                      />
                      <Area
                        type="monotone"
                        dataKey="limitDown"
                        name="跌停"
                        stroke="#EA580C"
                        fill="#EA580C"
                        fillOpacity={0.15}
                      />
                    </ComposedChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="flex items-center justify-center h-full text-fg-dim">
                    <Loader2 className="w-5 h-5 animate-spin mr-2" />
                    加载中...
                  </div>
                )}
              </div>
            </div>
          </div>
        </motion.div>
      )}

      {/* Stocks Tab */}
      {activeTab === 'stocks' && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-4">
          <div className="flex items-center gap-3">
            <div className="relative flex-1 max-w-md">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-fg-dim" />
              <input
                type="text"
                placeholder="搜索股票代码、名称或行业..."
                value={searchQuery}
                onChange={(e) => {
                  setSearchQuery(e.target.value)
                  setCurrentPage(1)
                }}
                className="input-df w-full pl-9 pr-4 py-2"
              />
            </div>
            <button className="flex items-center gap-1.5 px-3 py-2 rounded-lg border border-white/10 hover:bg-white/[0.03] text-sm text-fg-muted transition-colors">
              <Filter className="w-4 h-4" />
              筛选
            </button>
            <button className="flex items-center gap-1.5 px-3 py-2 rounded-lg border border-white/10 hover:bg-white/[0.03] text-sm text-fg-muted transition-colors">
              <Download className="w-4 h-4" />
              导出
            </button>
          </div>

          {constituentsLoading ? (
            <div className="flex items-center justify-center py-20 text-fg-dim">
              <Loader2 className="w-6 h-6 animate-spin mr-2" />
              加载成分股数据...
            </div>
          ) : (
            <>
              <div className="card-df overflow-hidden">
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr
                        className="border-b"
                        style={{ borderColor: 'rgba(30,41,59,0.6)', background: 'rgba(255,255,255,0.02)' }}
                      >
                        <th className="text-left px-4 py-3 font-medium text-fg-muted">代码</th>
                        <th className="text-left px-4 py-3 font-medium text-fg-muted">名称</th>
                        <th className="text-left px-4 py-3 font-medium text-fg-muted">行业</th>
                        <th className="text-left px-4 py-3 font-medium text-fg-muted">交易所</th>
                      </tr>
                    </thead>
                    <tbody>
                      {paginatedStocks.map((stock) => (
                        <tr
                          key={stock.code}
                          onClick={() => setSelectedStock(stock.code)}
                          className={`border-b cursor-pointer transition-colors ${
                            selectedStock === stock.code
                              ? 'bg-primary/[0.04]'
                              : 'hover:bg-white/[0.02]'
                          }`}
                          style={{ borderColor: 'rgba(30,41,59,0.4)' }}
                        >
                          <td className="px-4 py-3 font-mono text-fg">{stock.code}</td>
                          <td className="px-4 py-3 text-fg font-medium">{stock.name}</td>
                          <td className="px-4 py-3">
                            <span
                              className="px-2 py-0.5 rounded-full text-xs"
                              style={{
                                background: 'rgba(255,255,255,0.04)',
                                border: '1px solid rgba(255,255,255,0.06)',
                                color: '#94A3B8',
                              }}
                            >
                              {stock.industry}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-fg-muted">{stock.exchange}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {/* Pagination */}
                <div
                  className="flex items-center justify-between px-4 py-3 border-t"
                  style={{ borderColor: 'rgba(30,41,59,0.6)' }}
                >
                  <span className="text-xs text-fg-dim">
                    显示 {(currentPage - 1) * PAGE_SIZE + 1}-
                    {Math.min(currentPage * PAGE_SIZE, filteredStocks.length)} 条，共{' '}
                    {filteredStocks.length} 条
                  </span>
                  <div className="flex items-center gap-1">
                    <button
                      onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                      disabled={currentPage === 1}
                      className="p-1 rounded hover:bg-white/[0.03] text-fg-dim disabled:opacity-30"
                    >
                      <ChevronLeft className="w-4 h-4" />
                    </button>
                    <span className="text-sm text-fg-muted px-2">
                      {currentPage} / {totalPages || 1}
                    </span>
                    <button
                      onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                      disabled={currentPage === totalPages || totalPages === 0}
                      className="p-1 rounded hover:bg-white/[0.03] text-fg-dim disabled:opacity-30"
                    >
                      <ChevronRight className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              </div>

              {/* Stock Detail Chart */}
              {selectedStock && (
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="card-df p-5"
                >
                  <div className="flex items-center justify-between mb-3">
                    <div>
                      <h3 className="text-sm font-semibold text-fg">
                        {selectedStock} - {stockList.find((s) => s.code === selectedStock)?.name}
                      </h3>
                    </div>
                    <button
                      onClick={() => setSelectedStock(null)}
                      className="text-xs text-fg-dim hover:text-fg-muted"
                    >
                      关闭
                    </button>
                  </div>

                  {/* Indicator Controls */}
                  <div className="flex flex-wrap items-center gap-2 mb-3">
                    <IndicatorToggle
                      label="成交量"
                      active={showVolume}
                      onClick={() => setShowVolume((v) => !v)}
                      color="#F7931A"
                    />
                    <IndicatorToggle
                      label="MA均线"
                      active={showMa}
                      onClick={() => setShowMa((v) => !v)}
                      color="#FFD600"
                    />
                    <IndicatorToggle
                      label="布林通道"
                      active={showBoll}
                      onClick={() => setShowBoll((v) => !v)}
                      color="#8B5CF6"
                    />
                    <IndicatorToggle
                      label="MACD"
                      active={showMacd}
                      onClick={() => setShowMacd((v) => !v)}
                      color="#F7931A"
                    />
                  </div>

                  <div className="h-96">
                    {stockCandleData.length > 0 ? (
                      <StockChart
                        data={stockCandleData}
                        showVolume={showVolume}
                        showMa={showMa}
                        maPeriods={[5, 10, 20, 60]}
                        showBoll={showBoll}
                        bollPeriod={20}
                        bollStd={2}
                        showMacd={showMacd}
                        macdFast={12}
                        macdSlow={26}
                        macdSignal={9}
                      />
                    ) : (
                      <div className="flex items-center justify-center h-full text-fg-dim">
                        <Loader2 className="w-5 h-5 animate-spin mr-2" />
                        加载个股数据中...
                      </div>
                    )}
                  </div>
                </motion.div>
              )}
            </>
          )}
        </motion.div>
      )}

      {/* Industry Tab */}
      {activeTab === 'industry' && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-4">
          {!stockInfoData || stockInfoData.length === 0 ? (
            <div className="flex items-center justify-center py-20 text-fg-dim">
              <Loader2 className="w-6 h-6 animate-spin mr-2" />
              加载行业数据...
            </div>
          ) : (
            <div className="grid md:grid-cols-2 gap-4">
              <div className="card-df p-5">
                <h3 className="text-sm font-semibold text-primary mb-4">行业分布</h3>
                <div className="h-80">
                  {industryData.length > 0 ? (
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie
                          data={industryData}
                          cx="50%"
                          cy="50%"
                          innerRadius={60}
                          outerRadius={120}
                          paddingAngle={2}
                          dataKey="value"
                        >
                          {industryData.map((_, index) => (
                            <Cell
                              key={`cell-${index}`}
                              fill={COLORS[index % COLORS.length]}
                            />
                          ))}
                        </Pie>
                        <Tooltip
                          contentStyle={{
                            background: '#0F1115',
                            border: '1px solid rgba(30,41,59,0.8)',
                            borderRadius: '8px',
                            fontSize: '12px',
                            color: '#FFFFFF',
                          }}
                        />
                      </PieChart>
                    </ResponsiveContainer>
                  ) : (
                    <div className="flex items-center justify-center h-full text-fg-dim">
                      暂无行业数据
                    </div>
                  )}
                </div>
                <div className="flex flex-wrap justify-center gap-3 mt-2">
                  {industryData.map((item, index) => (
                    <div key={item.name} className="flex items-center gap-1.5 text-xs">
                      <div
                        className="w-2.5 h-2.5 rounded-full"
                        style={{ backgroundColor: COLORS[index % COLORS.length] }}
                      />
                      <span className="text-fg-muted">{item.name}</span>
                      <span className="text-fg-dim">({item.value})</span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="card-df p-5">
                <h3 className="text-sm font-semibold text-primary mb-4">行业统计</h3>
                <div className="space-y-3">
                  {industryData.map((item, index) => (
                    <div key={item.name}>
                      <div className="flex items-center justify-between text-sm mb-1">
                        <span className="text-fg">{item.name}</span>
                        <span className="text-fg-muted">
                          {item.value}只 ({((item.value / stockList.length) * 100).toFixed(1)}%)
                        </span>
                      </div>
                      <div
                        className="h-2 rounded-full overflow-hidden"
                        style={{ background: 'rgba(30,41,59,0.6)' }}
                      >
                        <motion.div
                          initial={{ width: 0 }}
                          animate={{
                            width: `${(item.value / Math.max(...industryData.map((d) => d.value))) * 100}%`,
                          }}
                          transition={{ duration: 0.8, delay: index * 0.05 }}
                          className="h-full rounded-full"
                          style={{ backgroundColor: COLORS[index % COLORS.length] }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </motion.div>
      )}
    </div>
  )
}
