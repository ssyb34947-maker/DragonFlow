import { useMemo, useState } from 'react'

interface CandleData {
  date: string
  open: number
  close: number
  high: number
  low: number
  volume: number
}

interface CandlestickChartProps {
  data: CandleData[]
  width?: number
  height?: number
}

export default function CandlestickChart({ data }: CandlestickChartProps) {
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null)

  const margin = { top: 10, right: 50, bottom: 30, left: 10 }

  const chart = useMemo(() => {
    if (!data.length) return null

    const innerWidth = 600 - margin.left - margin.right
    const innerHeight = 288 - margin.top - margin.bottom

    // Find min/max for Y scale
    const allValues = data.flatMap((d) => [d.high, d.low])
    const minPrice = Math.min(...allValues)
    const maxPrice = Math.max(...allValues)
    const priceRange = maxPrice - minPrice || 1
    const padding = priceRange * 0.05
    const yMin = minPrice - padding
    const yMax = maxPrice + padding

    // X scale
    const candleWidth = Math.max(2, Math.min(12, (innerWidth / data.length) * 0.6))
    const gap = innerWidth / data.length

    // Helper: price -> y pixel
    const priceToY = (price: number) =>
      margin.top + ((yMax - price) / (yMax - yMin)) * innerHeight

    // Helper: index -> x pixel (center of candle)
    const indexToX = (i: number) => margin.left + i * gap + gap / 2

    // Generate Y-axis ticks
    const tickCount = 5
    const yTicks = Array.from({ length: tickCount }, (_, i) => {
      const price = yMin + (i / (tickCount - 1)) * (yMax - yMin)
      return { price, y: priceToY(price) }
    })

    // X-axis ticks (show every Nth label)
    const xLabelStep = Math.max(1, Math.floor(data.length / 6))
    const xTicks = data
      .map((d, i) => ({ date: d.date, x: indexToX(i), index: i }))
      .filter((_, i) => i % xLabelStep === 0 || i === data.length - 1)

    return { innerWidth, innerHeight, candleWidth, gap, priceToY, indexToX, yTicks, xTicks, yMin, yMax }
  }, [data])

  if (!chart || !data.length) return null

  const { candleWidth, priceToY, indexToX, yTicks, xTicks } = chart

  const hovered = hoveredIndex !== null ? data[hoveredIndex] : null
  const hoveredX = hoveredIndex !== null ? indexToX(hoveredIndex) : 0

  return (
    <svg
      viewBox="0 0 600 288"
      preserveAspectRatio="xMidYMid meet"
      className="w-full h-full"
      onMouseLeave={() => setHoveredIndex(null)}
    >
      {/* Background grid - horizontal */}
      {yTicks.map((t, i) => (
        <g key={`hgrid-${i}`}>
          <line
            x1={margin.left}
            y1={t.y}
            x2={600 - margin.right}
            y2={t.y}
            stroke="rgba(30,41,59,0.4)"
            strokeDasharray="3 3"
          />
          <text
            x={600 - margin.right + 4}
            y={t.y + 3}
            fill="#64748B"
            fontSize="9"
            fontFamily="JetBrains Mono, monospace"
          >
            {t.price.toFixed(2)}
          </text>
        </g>
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
        const bodyHeight = Math.max(Math.abs(yClose - yOpen), 1)

        return (
          <g
            key={i}
            onMouseEnter={() => setHoveredIndex(i)}
            style={{ cursor: 'pointer' }}
          >
            {/* Invisible hit area */}
            <rect
              x={x - candleWidth}
              y={yHigh}
              width={candleWidth * 2}
              height={yLow - yHigh}
              fill="transparent"
            />
            {/* Upper wick */}
            <line
              x1={x}
              y1={yHigh}
              x2={x}
              y2={bodyTop}
              stroke={color}
              strokeWidth={1}
            />
            {/* Lower wick */}
            <line
              x1={x}
              y1={bodyTop + bodyHeight}
              x2={x}
              y2={yLow}
              stroke={color}
              strokeWidth={1}
            />
            {/* Body */}
            <rect
              x={x - candleWidth / 2}
              y={bodyTop}
              width={candleWidth}
              height={bodyHeight}
              fill={isUp ? color : color}
              stroke={color}
              strokeWidth={1}
              rx={1}
            />
          </g>
        )
      })}

      {/* Hover crosshair */}
      {hoveredIndex !== null && (
        <g>
          <line
            x1={hoveredX}
            y1={margin.top}
            x2={hoveredX}
            y2={288 - margin.bottom}
            stroke="rgba(247,147,26,0.3)"
            strokeDasharray="3 3"
            strokeWidth={1}
          />
        </g>
      )}

      {/* X-axis labels */}
      {xTicks.map((t, i) => (
        <text
          key={`xlabel-${i}`}
          x={t.x}
          y={288 - margin.bottom + 14}
          fill="#94A3B8"
          fontSize="9"
          textAnchor="middle"
          fontFamily="Inter, sans-serif"
        >
          {t.date}
        </text>
      ))}

      {/* Hover tooltip */}
      {hovered && hoveredIndex !== null && (
        <g>
          {/* Tooltip background */}
          <rect
            x={hoveredX + 10 > 400 ? hoveredX - 140 : hoveredX + 10}
            y={margin.top}
            width={130}
            height={90}
            rx={6}
            fill="#0F1115"
            stroke="rgba(30,41,59,0.8)"
            strokeWidth={1}
          />
          {/* Tooltip text */}
          <text
            x={(hoveredX + 10 > 400 ? hoveredX - 140 : hoveredX + 10) + 8}
            y={margin.top + 14}
            fill="#94A3B8"
            fontSize="9"
            fontFamily="JetBrains Mono, monospace"
          >
            {hovered.date}
          </text>
          <text
            x={(hoveredX + 10 > 400 ? hoveredX - 140 : hoveredX + 10) + 8}
            y={margin.top + 28}
            fill="#FFFFFF"
            fontSize="9"
            fontFamily="JetBrains Mono, monospace"
          >
            {`开: ${hovered.open.toFixed(2)}`}
          </text>
          <text
            x={(hoveredX + 10 > 400 ? hoveredX - 140 : hoveredX + 10) + 8}
            y={margin.top + 42}
            fill={hovered.close >= hovered.open ? '#10B981' : '#EF4444'}
            fontSize="9"
            fontFamily="JetBrains Mono, monospace"
          >
            {`收: ${hovered.close.toFixed(2)}`}
          </text>
          <text
            x={(hoveredX + 10 > 400 ? hoveredX - 140 : hoveredX + 10) + 8}
            y={margin.top + 56}
            fill="#FFFFFF"
            fontSize="9"
            fontFamily="JetBrains Mono, monospace"
          >
            {`高: ${hovered.high.toFixed(2)} 低: ${hovered.low.toFixed(2)}`}
          </text>
          <text
            x={(hoveredX + 10 > 400 ? hoveredX - 140 : hoveredX + 10) + 8}
            y={margin.top + 72}
            fill="#94A3B8"
            fontSize="9"
            fontFamily="JetBrains Mono, monospace"
          >
            {`量: ${(hovered.volume / 10000).toFixed(1)}万`}
          </text>
        </g>
      )}
    </svg>
  )
}
