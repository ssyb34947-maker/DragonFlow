import { useMemo, useState, useRef, useEffect } from 'react'

export interface CandleData {
  date: string
  open: number
  close: number
  high: number
  low: number
  volume: number
}

interface StockChartProps {
  data: CandleData[]
  showVolume?: boolean
  showMa?: boolean
  maPeriods?: number[]
  showBoll?: boolean
  bollPeriod?: number
  bollStd?: number
  showMacd?: boolean
  macdFast?: number
  macdSlow?: number
  macdSignal?: number
}

// ---- Technical Indicators ----

function sma(values: number[], period: number): (number | null)[] {
  const result: (number | null)[] = []
  for (let i = 0; i < values.length; i++) {
    if (i < period - 1) {
      result.push(null)
      continue
    }
    let sum = 0
    for (let j = 0; j < period; j++) sum += values[i - j]
    result.push(sum / period)
  }
  return result
}

function ema(values: number[], period: number): number[] {
  const k = 2 / (period + 1)
  const result: number[] = []
  for (let i = 0; i < values.length; i++) {
    if (i === 0) {
      result.push(values[0])
    } else {
      result.push(values[i] * k + result[i - 1] * (1 - k))
    }
  }
  return result
}

function bollinger(
  closes: number[],
  period: number,
  stdMult: number
): { upper: (number | null)[]; middle: (number | null)[]; lower: (number | null)[] } {
  const middle = sma(closes, period)
  const upper: (number | null)[] = []
  const lower: (number | null)[] = []
  for (let i = 0; i < closes.length; i++) {
    if (middle[i] === null) {
      upper.push(null)
      lower.push(null)
      continue
    }
    let sumSq = 0
    for (let j = 0; j < period; j++) {
      const diff = closes[i - j] - (middle[i] as number)
      sumSq += diff * diff
    }
    const std = Math.sqrt(sumSq / period)
    upper.push((middle[i] as number) + stdMult * std)
    lower.push((middle[i] as number) - stdMult * std)
  }
  return { upper, middle, lower }
}

function macdIndicator(
  closes: number[],
  fast: number,
  slow: number,
  signal: number
): { dif: number[]; dea: number[]; hist: number[] } {
  const emaFast = ema(closes, fast)
  const emaSlow = ema(closes, slow)
  const dif = emaFast.map((v, i) => v - emaSlow[i])
  const dea = ema(dif, signal)
  const hist = dif.map((v, i) => v - dea[i])
  return { dif, dea, hist }
}

// ---- Component ----

export default function StockChart({
  data,
  showVolume = true,
  showMa = true,
  maPeriods = [5, 10, 20, 60],
  showBoll = false,
  bollPeriod = 20,
  bollStd = 2,
  showMacd = false,
  macdFast = 12,
  macdSlow = 26,
  macdSignal = 9,
}: StockChartProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [size, setSize] = useState({ width: 600, height: 400 })
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null)

  useEffect(() => {
    const el = containerRef.current
    if (!el) return
    const ro = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const cr = entry.contentRect
        setSize({ width: cr.width, height: cr.height })
      }
    })
    ro.observe(el)
    return () => ro.disconnect()
  }, [])

  const chart = useMemo(() => {
    if (!data.length) return null

    const margin = { top: 10, right: 55, bottom: 24, left: 2 }

    // Determine panel heights
    const hasVolume = showVolume
    const hasMacd = showMacd
    const mainRatio = hasMacd ? 0.55 : hasVolume ? 0.7 : 1
    const volRatio = hasMacd ? 0.2 : 0.3
    const macdRatio = hasMacd ? 0.25 : 0

    const totalH = size.height
    const mainTop = margin.top
    const mainH = totalH * mainRatio - margin.top
    const volTop = mainTop + mainH + 4
    const volH = hasVolume ? totalH * volRatio - 8 : 0
    const macdTop = volTop + volH + 4
    const macdH = hasMacd ? totalH * macdRatio - 8 : 0

    const innerWidth = size.width - margin.left - margin.right

    // X scale
    const gap = innerWidth / data.length
    const candleW = Math.max(1.5, Math.min(10, gap * 0.65))
    const indexToX = (i: number) => margin.left + i * gap + gap / 2

    // Price scale
    const allPrices = data.flatMap((d) => [d.high, d.low])
    let minP = Math.min(...allPrices)
    let maxP = Math.max(...allPrices)

    // Include MA/Bollinger in scale
    const closes = data.map((d) => d.close)
    const maLines: { period: number; values: (number | null)[]; color: string }[] = []
    const maColors = ['#F7931A', '#FFD600', '#8B5CF6', '#06B6D4']
    if (showMa) {
      maPeriods.forEach((p, idx) => {
        const vals = sma(closes, p)
        maLines.push({ period: p, values: vals, color: maColors[idx % maColors.length] })
        vals.forEach((v) => {
          if (v !== null) {
            minP = Math.min(minP, v)
            maxP = Math.max(maxP, v)
          }
        })
      })
    }

    let bollLines: { key: string; values: (number | null)[]; color: string }[] = []
    if (showBoll) {
      const boll = bollinger(closes, bollPeriod, bollStd)
      bollLines = [
        { key: 'upper', values: boll.upper, color: 'rgba(139,92,246,0.6)' },
        { key: 'middle', values: boll.middle, color: 'rgba(139,92,246,0.4)' },
        { key: 'lower', values: boll.lower, color: 'rgba(139,92,246,0.6)' },
      ]
      bollLines.forEach((l) =>
        l.values.forEach((v) => {
          if (v !== null) {
            minP = Math.min(minP, v)
            maxP = Math.max(maxP, v)
          }
        })
      )
    }

    const pRange = maxP - minP || 1
    const pPad = pRange * 0.03
    const yMin = minP - pPad
    const yMax = maxP + pPad

    const priceToY = (p: number) => mainTop + ((yMax - p) / (yMax - yMin)) * mainH

    // Volume scale
    const volumes = data.map((d) => d.volume)
    const maxVol = Math.max(...volumes) * 1.05
    const volToY = (v: number) => volTop + volH - (v / maxVol) * volH

    // MACD
    let macdData: { dif: number[]; dea: number[]; hist: number[] } | null = null
    let macdScale: { min: number; max: number; toY: (v: number) => number } | null = null
    if (showMacd) {
      const m = macdIndicator(closes, macdFast, macdSlow, macdSignal)
      macdData = m
      const allMacd = [...m.dif, ...m.dea, ...m.hist]
      const mmMin = Math.min(...allMacd)
      const mmMax = Math.max(...allMacd)
      const mmRange = Math.max(Math.abs(mmMin), Math.abs(mmMax)) * 1.1
      macdScale = {
        min: -mmRange,
        max: mmRange,
        toY: (v: number) => macdTop + macdH / 2 - (v / mmRange) * (macdH / 2),
      }
    }

    // Ticks
    const yTickCount = 5
    const yTicks = Array.from({ length: yTickCount }, (_, i) => {
      const p = yMin + (i / (yTickCount - 1)) * (yMax - yMin)
      return { price: p, y: priceToY(p) }
    })

    const xStep = Math.max(1, Math.floor(data.length / 8))
    const xTicks = data
      .map((d, i) => ({ date: d.date, x: indexToX(i) }))
      .filter((_, i) => i % xStep === 0 || i === data.length - 1)

    return {
      margin,
      innerWidth,
      mainTop,
      mainH,
      volTop,
      volH,
      macdTop,
      macdH,
      gap,
      candleW,
      indexToX,
      priceToY,
      volToY,
      yTicks,
      xTicks,
      maLines,
      bollLines,
      macdData,
      macdScale,
      maxVol,
      yMin,
      yMax,
    }
  }, [data, size, showVolume, showMa, maPeriods, showBoll, bollPeriod, bollStd, showMacd, macdFast, macdSlow, macdSignal])

  if (!chart || !data.length) {
    return (
      <div ref={containerRef} className="w-full h-full flex items-center justify-center text-fg-dim text-sm">
        暂无数据
      </div>
    )
  }

  const {
    margin,
    innerWidth,
    mainTop,
    mainH,
    volTop,
    volH,
    macdTop,
    macdH,
    candleW,
    indexToX,
    priceToY,
    volToY,
    yTicks,
    xTicks,
    maLines,
    bollLines,
    macdData,
    macdScale,
    maxVol,
  } = chart

  const hovered = hoveredIndex !== null ? data[hoveredIndex] : null
  const hoveredX = hoveredIndex !== null ? indexToX(hoveredIndex) : 0

  const W = size.width
  const H = size.height

  // Build path strings for lines
  const buildPath = (values: (number | null)[], toY: (v: number) => number) => {
    let path = ''
    for (let i = 0; i < values.length; i++) {
      const v = values[i]
      if (v === null) continue
      const x = indexToX(i)
      const y = toY(v)
      if (path === '') path += `M ${x} ${y}`
      else path += ` L ${x} ${y}`
    }
    return path
  }

  return (
    <div ref={containerRef} className="w-full h-full relative">
      <svg
        viewBox={`0 0 ${W} ${H}`}
        preserveAspectRatio="none"
        className="w-full h-full"
        onMouseLeave={() => setHoveredIndex(null)}
      >
        {/* ---- Main Price Panel ---- */}
        {/* Horizontal grid */}
        {yTicks.map((t, i) => (
          <g key={`hgrid-${i}`}>
            <line
              x1={margin.left}
              y1={t.y}
              x2={W - margin.right}
              y2={t.y}
              stroke="rgba(30,41,59,0.35)"
              strokeDasharray="2 2"
            />
            <text
              x={W - margin.right + 3}
              y={t.y + 3}
              fill="#64748B"
              fontSize="9"
              fontFamily="JetBrains Mono, monospace"
            >
              {t.price.toFixed(2)}
            </text>
          </g>
        ))}

        {/* Bollinger bands (fill area) */}
        {showBoll && bollLines.length === 3 && (
          <>
            <path
              d={(() => {
                let upperPath = ''
                let lowerPath = ''
                for (let i = 0; i < data.length; i++) {
                  const u = bollLines[0].values[i]
                  const l = bollLines[2].values[i]
                  if (u === null || l === null) continue
                  const x = indexToX(i)
                  if (upperPath === '') {
                    upperPath += `M ${x} ${priceToY(u)}`
                    lowerPath += `M ${x} ${priceToY(l)}`
                  } else {
                    upperPath += ` L ${x} ${priceToY(u)}`
                    lowerPath += ` L ${x} ${priceToY(l)}`
                  }
                }
                // Close the loop
                return upperPath + ' ' + lowerPath.split('M')[1].split('').reverse().join('').replace(/L/g, 'L') + ' Z'
              })()}
              fill="rgba(139,92,246,0.06)"
              stroke="none"
            />
            {bollLines.map((line) => (
              <path
                key={line.key}
                d={buildPath(line.values, priceToY)}
                fill="none"
                stroke={line.color}
                strokeWidth={1}
                strokeDasharray={line.key === 'middle' ? '3 3' : undefined}
              />
            ))}
          </>
        )}

        {/* MA lines */}
        {showMa &&
          maLines.map((line) => (
            <path
              key={line.period}
              d={buildPath(line.values, priceToY)}
              fill="none"
              stroke={line.color}
              strokeWidth={1.2}
            />
          ))}

        {/* Candles */}
        {data.map((d, i) => {
          const x = indexToX(i)
          const yOpen = priceToY(d.open)
          const yClose = priceToY(d.close)
          const yHigh = priceToY(d.high)
          const yLow = priceToY(d.low)
          const isUp = d.close >= d.open
          const color = isUp ? '#10B981' : '#EF4444'
          const bodyTop = Math.min(yOpen, yClose)
          const bodyH = Math.max(Math.abs(yClose - yOpen), 0.8)

          return (
            <g
              key={`c-${i}`}
              onMouseEnter={() => setHoveredIndex(i)}
              style={{ cursor: 'pointer' }}
            >
              {/* Hit area */}
              <rect
                x={x - candleW}
                y={yHigh}
                width={candleW * 2}
                height={Math.max(yLow - yHigh, 1)}
                fill="transparent"
              />
              {/* Wick */}
              <line x1={x} y1={yHigh} x2={x} y2={yLow} stroke={color} strokeWidth={1} />
              {/* Body */}
              <rect
                x={x - candleW / 2}
                y={bodyTop}
                width={candleW}
                height={bodyH}
                fill={color}
                stroke={color}
                strokeWidth={0.5}
                rx={0.5}
              />
            </g>
          )
        })}

        {/* Crosshair */}
        {hoveredIndex !== null && (
          <line
            x1={hoveredX}
            y1={mainTop}
            x2={hoveredX}
            y2={mainTop + mainH}
            stroke="rgba(247,147,26,0.25)"
            strokeDasharray="3 3"
            strokeWidth={1}
          />
        )}

        {/* ---- Volume Panel ---- */}
        {showVolume && volH > 0 && (
          <g>
            {/* Separator */}
            <line
              x1={margin.left}
              y1={volTop - 2}
              x2={W - margin.right}
              y2={volTop - 2}
              stroke="rgba(30,41,59,0.5)"
              strokeWidth={1}
            />
            {/* Volume bars */}
            {data.map((d, i) => {
              const x = indexToX(i)
              const isUp = d.close >= d.open
              const color = isUp ? 'rgba(16,185,129,0.5)' : 'rgba(239,68,68,0.5)'
              const y = volToY(d.volume)
              const h = volTop + volH - y
              return (
                <rect
                  key={`v-${i}`}
                  x={x - candleW / 2}
                  y={y}
                  width={candleW}
                  height={Math.max(h, 1)}
                  fill={color}
                  rx={0.5}
                />
              )
            })}
            {/* Volume label */}
            <text
              x={W - margin.right + 3}
              y={volTop + 10}
              fill="#64748B"
              fontSize="8"
              fontFamily="JetBrains Mono, monospace"
            >
              {(maxVol / 10000).toFixed(0)}万
            </text>
          </g>
        )}

        {/* ---- MACD Panel ---- */}
        {showMacd && macdData && macdScale && macdH > 0 && (
          <g>
            {/* Separator */}
            <line
              x1={margin.left}
              y1={macdTop - 2}
              x2={W - margin.right}
              y2={macdTop - 2}
              stroke="rgba(30,41,59,0.5)"
              strokeWidth={1}
            />
            {/* Zero line */}
            <line
              x1={margin.left}
              y1={macdScale.toY(0)}
              x2={W - margin.right}
              y2={macdScale.toY(0)}
              stroke="rgba(30,41,59,0.5)"
              strokeDasharray="2 2"
            />
            {/* Histogram */}
            {macdData.hist.map((v, i) => {
              const x = indexToX(i)
              const y0 = macdScale.toY(0)
              const y1 = macdScale.toY(v)
              const isPos = v >= 0
              return (
                <rect
                  key={`mh-${i}`}
                  x={x - 1}
                  y={Math.min(y0, y1)}
                  width={2}
                  height={Math.max(Math.abs(y1 - y0), 1)}
                  fill={isPos ? 'rgba(16,185,129,0.6)' : 'rgba(239,68,68,0.6)'}
                />
              )
            })}
            {/* DIF line */}
            <path
              d={buildPath(
                macdData.dif.map((v) => v),
                macdScale.toY
              )}
              fill="none"
              stroke="#F7931A"
              strokeWidth={1}
            />
            {/* DEA line */}
            <path
              d={buildPath(
                macdData.dea.map((v) => v),
                macdScale.toY
              )}
              fill="none"
              stroke="#06B6D4"
              strokeWidth={1}
            />
            {/* MACD label */}
            <text
              x={W - margin.right + 3}
              y={macdTop + 10}
              fill="#F7931A"
              fontSize="8"
              fontFamily="JetBrains Mono, monospace"
            >
              MACD
            </text>
          </g>
        )}

        {/* X-axis labels */}
        {xTicks.map((t, i) => (
          <text
            key={`xl-${i}`}
            x={t.x}
            y={H - 4}
            fill="#94A3B8"
            fontSize="9"
            textAnchor="middle"
            fontFamily="Inter, sans-serif"
          >
            {t.date}
          </text>
        ))}
      </svg>

      {/* HTML Tooltip overlay */}
      {hovered && hoveredIndex !== null && (
        <div
          className="absolute pointer-events-none rounded-lg p-2.5 text-xs z-10"
          style={{
            left: Math.min(hoveredX + 12, W - 150),
            top: mainTop + 4,
            background: 'rgba(15,17,21,0.95)',
            border: '1px solid rgba(30,41,59,0.8)',
            backdropFilter: 'blur(4px)',
            color: '#FFFFFF',
            fontFamily: 'JetBrains Mono, monospace',
            minWidth: 130,
          }}
        >
          <div className="text-fg-muted mb-1">{hovered.date}</div>
          <div className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-0.5">
            <span className="text-fg-dim">开</span>
            <span className="text-right">{hovered.open.toFixed(2)}</span>
            <span className="text-fg-dim">收</span>
            <span
              className="text-right"
              style={{ color: hovered.close >= hovered.open ? '#10B981' : '#EF4444' }}
            >
              {hovered.close.toFixed(2)}
            </span>
            <span className="text-fg-dim">高</span>
            <span className="text-right">{hovered.high.toFixed(2)}</span>
            <span className="text-fg-dim">低</span>
            <span className="text-right">{hovered.low.toFixed(2)}</span>
            <span className="text-fg-dim">量</span>
            <span className="text-right">{(hovered.volume / 10000).toFixed(1)}万</span>
          </div>
          {/* MA values */}
          {showMa && maLines.length > 0 && (
            <div className="mt-1.5 pt-1.5 border-t border-white/5">
              {maLines.map((line) => {
                const v = line.values[hoveredIndex]
                if (v === null) return null
                return (
                  <div key={line.period} className="flex justify-between">
                    <span style={{ color: line.color }}>MA{line.period}</span>
                    <span>{v.toFixed(2)}</span>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
