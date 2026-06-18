import { useEffect, useState, type ReactNode } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { BrainCircuit, CandlestickChart, Database, LineChart, Network } from 'lucide-react'

type Stage = 0 | 1 | 2 | 3 | 4

type StageMeta = {
  title: string
  subtitle: string
  bullets: string[]
  stats: string[]
  color: string
  icon: typeof Database
}

const stageDuration = 1450
const stages: Stage[] = [0, 1, 2, 3, 4]

const stageMeta: StageMeta[] = [
  {
    title: '输入面板',
    subtitle: 'model_panel_base.parquet',
    bullets: ['OHLCV、成交额、换手率与指数代理行情按交易日对齐。', '生成技术特征、市场状态和未来5日超额收益标签。'],
    stats: ['30D WINDOW', 'EXCESS RETURN LABEL'],
    color: '#38BDF8',
    icon: Database,
  },
  {
    title: 'K线分词嵌入器',
    subtitle: 'K-line -> granularity -> neurons -> vector',
    bullets: ['K线序列拆成粗粒度趋势与细粒度形态片段。', '片段进入轻量神经编码器，形成4维 kline_emb。'],
    stats: ['8 SHAPE FEATURES', 'KLINE EMBED x4'],
    color: '#A78BFA',
    icon: CandlestickChart,
  },
  {
    title: '预训练聚类落点',
    subtitle: 'rolling spectral graph embedding',
    bullets: ['新股票状态点进入预先构建的股票关系图。', '找到簇内落点后产生8维谱嵌入与同簇上下文。'],
    stats: ['GRAPH WINDOW 40', 'SPECTRAL EMBED x8'],
    color: '#F59E0B',
    icon: Network,
  },
  {
    title: 'KS-TFT 融合网络',
    subtitle: 'feature sequence -> TransformerEncoder -> quantile head',
    bullets: ['行情特征、K线嵌入、谱嵌入汇合成30日序列。', '神经元逐层高亮激活，输出 q10 / q50 / q90。'],
    stats: ['D_MODEL 48', 'HEADS 2'],
    color: '#FBBF24',
    icon: BrainCircuit,
  },
  {
    title: '分位数信号与回测',
    subtitle: 'prediction -> risk filter -> portfolio',
    bullets: ['q50 用于收益排序，q10 用于下行风险过滤。', 'Top-K 信号进入组合回测，形成净值与回撤。'],
    stats: ['Q10 / Q50 / Q90', 'TOP-K PORTFOLIO'],
    color: '#22C55E',
    icon: LineChart,
  },
]

const panels = [
  { left: '2.5%', top: '30%', width: '14%', height: '40%' },
  { left: '19%', top: '18%', width: '18%', height: '64%' },
  { left: '39%', top: '18%', width: '18%', height: '64%' },
  { left: '60%', top: '14%', width: '20%', height: '72%' },
  { left: '84%', top: '25%', width: '13.5%', height: '50%' },
]

const flowPaths = [
  { d: 'M16.5 50 C18 50 18 50 19 50', stage: 0, color: '#38BDF8' },
  { d: 'M37 50 C38 50 38 50 39 50', stage: 1, color: '#A78BFA' },
  { d: 'M57 50 C58.5 50 58.5 50 60 50', stage: 2, color: '#F59E0B' },
  { d: 'M80 50 C82 50 82 50 84 50', stage: 3, color: '#FBBF24' },
]

const candleSticks = Array.from({ length: 22 }, (_, i) => ({
  x: 8 + i * 3.8,
  top: 34 + ((i * 13) % 24),
  height: 13 + ((i * 7) % 18),
  up: i % 4 !== 1,
}))

const graphNodes = [
  { x: 22, y: 23, c: '#38BDF8' }, { x: 35, y: 18, c: '#38BDF8' }, { x: 28, y: 38, c: '#38BDF8' }, { x: 45, y: 33, c: '#38BDF8' },
  { x: 60, y: 24, c: '#F59E0B' }, { x: 74, y: 34, c: '#F59E0B' }, { x: 65, y: 50, c: '#F59E0B' }, { x: 84, y: 49, c: '#F59E0B' },
  { x: 28, y: 70, c: '#A78BFA' }, { x: 46, y: 80, c: '#A78BFA' }, { x: 63, y: 72, c: '#A78BFA' }, { x: 79, y: 82, c: '#A78BFA' },
]
const graphEdges = [[0, 1], [0, 2], [1, 3], [2, 3], [3, 4], [4, 5], [4, 6], [5, 7], [6, 7], [2, 8], [8, 9], [9, 10], [10, 11], [6, 10]]

const fusionLayers = [
  { x: 9, count: 8, color: '#38BDF8' },
  { x: 25, count: 7, color: '#A78BFA' },
  { x: 43, count: 8, color: '#F59E0B' },
  { x: 62, count: 8, color: '#FBBF24' },
  { x: 80, count: 5, color: '#A78BFA' },
  { x: 93, count: 3, color: '#22C55E' },
]

const outputCurves = [
  { d: 'M8 65 C25 45 40 60 54 36 C68 15 80 35 94 19', c: '#22C55E' },
  { d: 'M8 78 C25 66 41 76 55 58 C69 42 81 52 94 38', c: '#F59E0B' },
  { d: 'M8 89 C25 83 42 91 56 78 C70 66 82 72 94 58', c: '#38BDF8' },
]

function useOneWayStage() {
  const [stage, setStage] = useState<Stage>(0)
  useEffect(() => {
    const timers = stages.slice(1).map((nextStage, index) => window.setTimeout(() => setStage(nextStage), stageDuration * (index + 1)))
    return () => timers.forEach(window.clearTimeout)
  }, [])
  return stage
}

function Panel({ children, index, stage, className = '' }: { children: ReactNode; index: Stage; stage: Stage; className?: string }) {
  const active = stage === index
  const visited = stage >= index
  const color = stageMeta[index].color
  return (
    <motion.div
      className={`absolute overflow-hidden rounded-lg border bg-[#070a11] ${className}`}
      animate={{
        opacity: active ? 1 : visited ? 0.88 : 0.38,
        scale: active ? 1.012 : 1,
        borderColor: active ? color : visited ? `${color}99` : 'rgba(71,85,105,0.55)',
        boxShadow: active ? `0 0 0 1px ${color}55, 0 18px 48px rgba(0,0,0,0.44)` : '0 12px 34px rgba(0,0,0,0.35)',
      }}
      transition={{ duration: 0.22, ease: 'easeOut' }}
    >
      {children}
    </motion.div>
  )
}

function Explanation({ stage }: { stage: Stage }) {
  const meta = stageMeta[stage]
  const Icon = meta.icon
  return (
    <AnimatePresence mode="wait">
      <motion.aside
        key={stage}
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -8 }}
        transition={{ duration: 0.16 }}
        className="absolute bottom-[8%] left-[18%] z-20 w-[min(720px,52%)] rounded-lg border bg-[#080b10] p-4 shadow-[0_20px_54px_rgba(0,0,0,0.5)]"
        style={{ borderColor: `${meta.color}aa` }}
      >
        <div className="mb-3 flex items-start gap-3 border-b border-slate-700/80 pb-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-md border bg-[#0d1119]" style={{ borderColor: meta.color }}>
            <Icon className="h-5 w-5" style={{ color: meta.color }} />
          </div>
          <div>
            <div className="text-lg font-bold leading-tight text-white">{meta.title}</div>
            <div className="mt-1 font-mono text-[11px] text-slate-400">{meta.subtitle}</div>
          </div>
        </div>
        <div className="grid gap-4 md:grid-cols-[1fr_210px]">
          <div className="space-y-2">
            {meta.bullets.map((bullet) => (
              <div key={bullet} className="grid grid-cols-[16px_1fr] gap-2 text-sm leading-relaxed text-slate-300">
                <span className="mt-2 h-1.5 w-1.5 rounded-full" style={{ background: meta.color }} />
                <span>{bullet}</span>
              </div>
            ))}
          </div>
          <div className="grid content-start gap-2">
            {meta.stats.map((stat) => <div key={stat} className="rounded-md border border-slate-700 bg-[#0d1119] px-3 py-2 font-mono text-[11px] text-slate-300">{stat}</div>)}
          </div>
        </div>
      </motion.aside>
    </AnimatePresence>
  )
}

function SignalDot({ d, active, color }: { d: string; active: boolean; color: string }) {
  return active ? (
    <circle r="3.8" fill={color} stroke="#fff" strokeWidth="0.7" filter="url(#crispGlow)">
      <animateMotion dur="0.85s" repeatCount="1" fill="freeze" path={d} />
    </circle>
  ) : null
}

function InputPanel({ active, visited }: { active: boolean; visited: boolean }) {
  return (
    <svg className="absolute inset-0 h-full w-full" viewBox="0 0 100 100" preserveAspectRatio="xMidYMid meet">
      {Array.from({ length: 12 }, (_, i) => (
        <motion.rect key={i} x="12" y={13 + i * 6.4} width={70 - (i % 4) * 8} height="2.8" rx="1.4" fill={i % 3 === 0 ? '#38BDF8' : '#475569'} animate={{ opacity: active ? [0.35, 1, 0.7] : visited ? 0.72 : 0.22, x: active ? [10, 16, 12] : 12 }} transition={{ duration: 0.52, delay: i * 0.03 }} />
      ))}
      {Array.from({ length: 7 }, (_, i) => (
        <motion.circle key={i} cx={18 + i * 11} cy={84} r="2.5" fill="#38BDF8" stroke="#E0F2FE" strokeWidth="0.5" animate={{ r: active ? [1.8, 3.8, 2.5] : 2.2, opacity: active ? [0.35, 1, 0.78] : visited ? 0.75 : 0.24 }} transition={{ duration: 0.48, delay: 0.18 + i * 0.045 }} />
      ))}
    </svg>
  )
}

function Neuron({ x, y, color, active, visited, delay, small = false, output = false }: { x: number; y: number; color: string; active: boolean; visited: boolean; delay: number; small?: boolean; output?: boolean }) {
  const r = output ? 3.6 : small ? 2.25 : 2.65
  return (
    <motion.g>
      <motion.circle cx={x} cy={y} r={r + 2.6} fill="none" stroke={color} strokeWidth="0.8" vectorEffect="non-scaling-stroke" animate={{ r: active ? [r + 1.1, r + 5.2, r + 1.8] : visited ? r + 2 : r + 1, opacity: active ? [0.16, 0.92, 0.38] : visited ? 0.42 : 0.14 }} transition={{ duration: 0.42, delay }} />
      <motion.circle cx={x} cy={y} r={r} fill="#0B1020" stroke={color} strokeWidth="1.2" filter="url(#crispGlow)" vectorEffect="non-scaling-stroke" animate={{ r: active ? [r * 0.9, r * 1.65, r] : visited ? r : r * 0.9, opacity: active ? [0.55, 1, 0.82] : visited ? 0.82 : 0.32 }} transition={{ duration: 0.36, delay }} />
      <motion.circle cx={x} cy={y} r={r * 0.42} fill={color} animate={{ opacity: active ? [0.25, 1, 0.7] : visited ? 0.76 : 0.24 }} transition={{ duration: 0.32, delay: delay + 0.04 }} />
    </motion.g>
  )
}

function KLineTokenizer({ active, visited }: { active: boolean; visited: boolean }) {
  const coarse = ['M13 29 C20 20 26 35 33 25', 'M13 45 C21 52 27 39 33 49', 'M13 61 C20 55 26 70 33 62']
  return (
    <svg className="absolute inset-0 h-full w-full" viewBox="0 0 100 100" preserveAspectRatio="xMidYMid meet">
      {candleSticks.map((item, index) => (
        <g key={index} opacity={active || visited ? 1 : 0.3}>
          <line x1={item.x} x2={item.x} y1={item.top - 7} y2={item.top + item.height + 7} stroke={item.up ? '#22C55E' : '#EF4444'} strokeWidth="0.8" vectorEffect="non-scaling-stroke" />
          <motion.rect x={item.x - 1.25} y={item.top} width="2.5" height={item.height} rx="0.5" fill={item.up ? '#22C55E' : '#EF4444'} animate={{ opacity: active ? [0.5, 1, 0.8] : visited ? 0.86 : 0.28 }} transition={{ duration: 0.25, delay: index * 0.012 }} />
        </g>
      ))}
      {coarse.map((d, index) => <motion.path key={d} d={d} fill="none" stroke="#A78BFA" strokeWidth="1.8" strokeLinecap="round" vectorEffect="non-scaling-stroke" animate={{ pathLength: active ? [0, 1] : visited ? 1 : 0, opacity: active || visited ? 0.95 : 0.18 }} transition={{ duration: 0.42, delay: 0.18 + index * 0.08 }} />)}
      {Array.from({ length: 8 }, (_, i) => <motion.rect key={i} x={42 + (i % 2) * 6} y={19 + Math.floor(i / 2) * 15} width={i % 2 ? 8 : 3.2} height="8" rx="1.2" fill={i % 2 ? '#FBBF24' : '#38BDF8'} stroke="#0F172A" strokeWidth="0.4" animate={{ opacity: active ? [0.28, 1, 0.8] : visited ? 0.76 : 0.18, scaleY: active ? [0.65, 1.25, 1] : 1 }} transition={{ duration: 0.3, delay: 0.42 + i * 0.025 }} />)}
      {Array.from({ length: 5 }, (_, i) => <Neuron key={i} x={65} y={23 + i * 13} color="#A78BFA" active={active} visited={visited} delay={0.58 + i * 0.045} />)}
      {Array.from({ length: 4 }, (_, i) => <motion.rect key={i} x={82 + i * 3.2} y={55 - i * 7} width="2.4" height={18 + i * 7} rx="1" fill="#22C55E" animate={{ opacity: active ? [0.2, 1, 0.85] : visited ? 0.8 : 0.16, scaleY: active ? [0.25, 1.18, 1] : 1 }} transition={{ duration: 0.32, delay: 0.78 + i * 0.04 }} />)}
      <path d="M34 48 C39 48 39 48 43 48 M54 48 C59 48 60 48 64 48 M70 48 C76 48 77 48 82 48" stroke="rgba(226,232,240,0.5)" strokeWidth="0.8" strokeDasharray="2 2" vectorEffect="non-scaling-stroke" />
    </svg>
  )
}

function ClusterModel({ active, visited }: { active: boolean; visited: boolean }) {
  const landing = { x: 63, y: 50 }
  const path = 'M8 52 C18 42 34 31 47 40 C55 45 57 49 63 50'
  return (
    <svg className="absolute inset-0 h-full w-full" viewBox="0 0 100 100" preserveAspectRatio="xMidYMid meet">
      {graphEdges.map(([a, b], i) => {
        const from = graphNodes[a]
        const to = graphNodes[b]
        return <motion.line key={`${a}-${b}`} x1={from.x} y1={from.y} x2={to.x} y2={to.y} stroke="#64748B" strokeWidth="0.85" vectorEffect="non-scaling-stroke" animate={{ opacity: active ? [0.28, 0.85, 0.48] : visited ? 0.56 : 0.2 }} transition={{ duration: 0.34, delay: i * 0.012 }} />
      })}
      {graphNodes.map((node, i) => <Neuron key={i} x={node.x} y={node.y} color={node.c} active={active} visited={visited} delay={0.12 + i * 0.018} small />)}
      <motion.path d={path} fill="none" stroke="#F59E0B" strokeWidth="1.3" strokeDasharray="3 3" strokeLinecap="round" vectorEffect="non-scaling-stroke" animate={{ pathLength: active ? [0, 1] : visited ? 1 : 0, opacity: active || visited ? 0.95 : 0.12 }} transition={{ duration: 0.45, delay: 0.08 }} />
      {active && <circle r="3.8" fill="#FDE68A" stroke="#fff" strokeWidth="0.6" filter="url(#crispGlow)"><animateMotion dur="0.65s" repeatCount="1" fill="freeze" path={path} /></circle>}
      <motion.circle cx={landing.x} cy={landing.y} r="6" fill="none" stroke="#FDE68A" strokeWidth="1.1" vectorEffect="non-scaling-stroke" animate={{ r: active ? [3, 10, 6] : visited ? 6 : 0, opacity: active ? [0, 1, 0.45] : visited ? 0.45 : 0 }} transition={{ duration: 0.34, delay: 0.62 }} />
      {Array.from({ length: 8 }, (_, i) => <motion.rect key={i} x={74 + i * 2.3} y={68 - ((i * 9) % 34)} width="1.7" height={9 + ((i * 5) % 24)} rx="0.7" fill={i % 2 ? '#F59E0B' : '#A78BFA'} animate={{ opacity: active ? [0, 1, 0.86] : visited ? 0.76 : 0.16, scaleY: active ? [0.1, 1.2, 1] : 1 }} transition={{ duration: 0.32, delay: 0.78 + i * 0.025 }} />)}
    </svg>
  )
}

function FusionNetwork({ active, visited }: { active: boolean; visited: boolean }) {
  const points = fusionLayers.map((layer) => {
    const gap = layer.count === 3 ? 14 : 7.2
    const start = layer.count === 3 ? 36 : 25
    return { ...layer, points: Array.from({ length: layer.count }, (_, i) => ({ x: layer.x, y: start + i * gap, i })) }
  })
  const lines = points.slice(0, -1).flatMap((layer, layerIndex) => points[layerIndex + 1].points.flatMap((to) => layer.points.map((from) => ({ from, to, layerIndex, strong: (from.i + to.i + layerIndex) % 4 === 0, color: points[layerIndex + 1].color }))))
  return (
    <svg className="absolute inset-0 h-full w-full" viewBox="0 0 100 100" preserveAspectRatio="xMidYMid meet">
      {lines.map((line, i) => <motion.line key={i} x1={line.from.x} y1={line.from.y} x2={line.to.x} y2={line.to.y} stroke={line.strong ? line.color : '#475569'} strokeWidth={line.strong ? '0.72' : '0.36'} strokeDasharray={line.strong ? '2 2.4' : '1 3'} strokeLinecap="round" vectorEffect="non-scaling-stroke" animate={{ opacity: active ? (line.strong ? [0.16, 0.9, 0.3] : [0.08, 0.36, 0.14]) : visited ? (line.strong ? 0.42 : 0.18) : 0.06, strokeDashoffset: active ? [0, -9] : 0 }} transition={{ duration: 0.32, delay: 0.08 + line.layerIndex * 0.12 + i * 0.0015 }} />)}
      {points.map((layer, layerIndex) => layer.points.map((node) => <Neuron key={`${layer.x}-${node.i}`} x={node.x} y={node.y} color={layer.color} active={active} visited={visited} delay={0.12 + layerIndex * 0.13 + node.i * 0.025} output={layer.count === 3} />))}
    </svg>
  )
}

function OutputPanel({ active, visited }: { active: boolean; visited: boolean }) {
  return (
    <svg className="absolute inset-0 h-full w-full" viewBox="0 0 100 100" preserveAspectRatio="xMidYMid meet">
      {outputCurves.map((line, i) => <motion.path key={line.d} d={line.d} fill="none" stroke={line.c} strokeWidth="2.1" strokeLinecap="round" vectorEffect="non-scaling-stroke" animate={{ pathLength: active ? [0, 1] : visited ? 1 : 0, opacity: active ? [0.45, 1, 0.8] : visited ? 0.76 : 0.16 }} transition={{ duration: 0.5, delay: i * 0.08 }} />)}
      {Array.from({ length: 18 }, (_, i) => <motion.rect key={i} x={9 + i * 4.7} y={76 - ((i * 11) % 32)} width="2.5" height={7 + ((i * 7) % 20)} rx="1" fill={i % 3 ? '#F59E0B' : '#22C55E'} animate={{ opacity: active ? [0.16, 0.95, 0.68] : visited ? 0.62 : 0.14, scaleY: active ? [0.2, 1.2, 1] : 1 }} transition={{ duration: 0.32, delay: 0.38 + i * 0.018 }} />)}
    </svg>
  )
}

export default function DataFlowPage() {
  const stage = useOneWayStage()

  return (
    <div className="mx-auto flex min-h-[calc(100vh-48px)] max-w-[1600px] items-center" aria-label="DragonFlow-KronosGraph one-way algorithm animation">
      <section className="relative h-[calc(100vh-96px)] min-h-[720px] w-full overflow-hidden rounded-xl border border-slate-800 bg-[#020409] shadow-2xl">
        <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.028)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.028)_1px,transparent_1px)] bg-[length:48px_48px]" />
        <svg className="absolute inset-0 h-full w-full" viewBox="0 0 100 100" preserveAspectRatio="none">
          <defs><filter id="crispGlow"><feGaussianBlur stdDeviation="0.75" result="blur" /><feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge></filter></defs>
          {flowPaths.map((segment) => <g key={segment.d}><motion.path d={segment.d} fill="none" stroke={segment.color} strokeOpacity={stage > segment.stage ? 0.58 : stage === segment.stage ? 0.9 : 0.16} strokeWidth="0.82" strokeLinecap="round" strokeDasharray="2 2" vectorEffect="non-scaling-stroke" animate={{ pathLength: stage >= segment.stage ? 1 : 0 }} transition={{ duration: 0.32 }} /> <SignalDot d={segment.d} active={stage === segment.stage} color={segment.color} /></g>)}
        </svg>

        <motion.div className="absolute rounded-xl border pointer-events-none" style={{ ...panels[stage], borderColor: stageMeta[stage].color }} animate={{ opacity: [0.35, 0.95, 0.45], scale: [1, 1.008, 1] }} transition={{ duration: 0.55 }} />

        <Panel stage={stage} index={0} className="left-[2.5%] top-[30%] h-[40%] w-[14%]"><InputPanel active={stage === 0} visited={stage >= 0} /></Panel>
        <Panel stage={stage} index={1} className="left-[19%] top-[18%] h-[64%] w-[18%]"><KLineTokenizer active={stage === 1} visited={stage >= 1} /></Panel>
        <Panel stage={stage} index={2} className="left-[39%] top-[18%] h-[64%] w-[18%]"><ClusterModel active={stage === 2} visited={stage >= 2} /></Panel>
        <Panel stage={stage} index={3} className="left-[60%] top-[14%] h-[72%] w-[20%]"><FusionNetwork active={stage === 3} visited={stage >= 3} /></Panel>
        <Panel stage={stage} index={4} className="left-[84%] top-[25%] h-[50%] w-[13.5%]"><OutputPanel active={stage === 4} visited={stage >= 4} /></Panel>

        <Explanation stage={stage} />

        <div className="absolute bottom-[3.5%] left-[7%] right-[7%] flex gap-3">
          {stages.map((item) => <div key={item} className="relative h-7 flex-1 overflow-hidden rounded-md border border-slate-700 bg-[#080b10]"><motion.div className="h-full rounded-md" style={{ background: stageMeta[item].color }} animate={{ width: stage > item ? '100%' : stage === item ? '100%' : '0%', opacity: stage >= item ? 0.9 : 0.18 }} transition={{ duration: stage === item ? stageDuration / 1000 : 0.18, ease: 'linear' }} /></div>)}
        </div>
      </section>
    </div>
  )
}
