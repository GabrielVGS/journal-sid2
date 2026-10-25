import { type PointerEvent, useLayoutEffect, useRef, useState } from 'react'

export interface ChartPoint {
  x: number
  y: number | null
}

interface ChartProps {
  points: ChartPoint[]
  kind: 'area' | 'bars'
  label: string
  formatX: (x: number) => string
  formatY: (y: number) => string
  xTicks: number[]
  domain?: 'zero' | 'data' | [number, number]
  extremes?: boolean
  cumulative?: boolean
  height?: number
}

const MARGIN = { top: 16, right: 10, bottom: 20, left: 32 }

// Mede a largura do container para o SVG acompanhar o tamanho da tela.
export function useWidth() {
  const ref = useRef<HTMLElement>(null)
  const [width, setWidth] = useState(0)
  useLayoutEffect(() => {
    const element = ref.current
    if (!element) return
    const observer = new ResizeObserver(([entry]) => setWidth(entry?.contentRect.width ?? 0))
    observer.observe(element)
    return () => observer.disconnect()
  }, [])
  return [ref, width] as const
}

// Marcas do eixo Y em valores redondos (1, 2, 2,5 ou 5 × 10^n).
function niceTicks(min: number, max: number, count = 3): number[] {
  const step = Math.max((max - min) / count, 0.5)
  const magnitude = 10 ** Math.floor(Math.log10(step))
  const nice = [1, 2, 2.5, 5, 10].map((m) => m * magnitude).find((s) => s >= step) ?? step
  const ticks = [Math.floor(min / nice) * nice]
  while ((ticks.at(-1) ?? max) < max - 1e-9) ticks.push((ticks.at(-1) ?? 0) + nice)
  return ticks.map((tick) => Number(tick.toFixed(6)))
}

// Curva suave que não passa do valor real entre dois pontos (Fritsch–Carlson).
function monotonePath(xy: [number, number][]): string {
  const n = xy.length
  if (n < 3) return xy.map(([x, y], i) => `${i ? 'L' : 'M'}${x},${y}`).join('')
  const dx = xy.slice(1).map(([x], i) => x - (xy[i]?.[0] ?? x))
  const slope = xy.slice(1).map(([, y], i) => (y - (xy[i]?.[1] ?? y)) / (dx[i] || 1))
  const tangent = xy.map((_, i) => {
    if (i === 0) return slope[0] ?? 0
    if (i === n - 1) return slope[n - 2] ?? 0
    const [a, b] = [slope[i - 1] ?? 0, slope[i] ?? 0]
    return a * b <= 0 ? 0 : (3 * a * b) / (2 * Math.max(a, b) + Math.min(a, b))
  })
  let path = `M${xy[0]?.[0]},${xy[0]?.[1]}`
  for (let i = 0; i < n - 1; i++) {
    const [x0, y0] = xy[i] ?? [0, 0]
    const [x1, y1] = xy[i + 1] ?? [0, 0]
    const h = (dx[i] ?? 0) / 3
    path += `C${x0 + h},${y0 + h * (tangent[i] ?? 0)} ${x1 - h},${y1 - h * (tangent[i + 1] ?? 0)} ${x1},${y1}`
  }
  return path
}

export function Chart({
  points,
  kind,
  label,
  formatX,
  formatY,
  xTicks,
  domain = 'zero',
  extremes = false,
  cumulative = false,
  height = 130,
}: ChartProps) {
  const [ref, width] = useWidth()
  const [hover, setHover] = useState<ChartPoint | null>(null)
  const valid = points.filter((p): p is { x: number; y: number } => p.y !== null)
  const totals = new Map<number, number>()
  valid.reduce((sum, p) => {
    totals.set(p.x, sum + p.y)
    return sum + p.y
  }, 0)
  const showTotal = cumulative && kind === 'bars'

  const values = [...valid.map((p) => p.y), ...(showTotal ? totals.values() : [])]
  const [low, high] =
    domain === 'zero'
      ? [0, Math.max(...values, 1)]
      : domain === 'data'
        ? [Math.min(...values) - 1, Math.max(...values) + 1]
        : domain
  const yTicks = niceTicks(low, high)
  const [yMin, yMax] = [Math.min(...yTicks), Math.max(...yTicks)]
  const plotWidth = Math.max(width - MARGIN.left - MARGIN.right, 10)
  const plotHeight = height - MARGIN.top - MARGIN.bottom
  const xMin = Math.min(...points.map((p) => p.x))
  const step = plotWidth / Math.max(points.length, 1)
  const x = (value: number) => MARGIN.left + (value - xMin) * step + step / 2
  const y = (value: number) =>
    MARGIN.top + plotHeight - ((value - yMin) / (yMax - yMin || 1)) * plotHeight
  const baseline = y(yMin)

  const line = monotonePath(valid.map((p) => [x(p.x), y(p.y)]))
  const totalLine = showTotal
    ? monotonePath(valid.map((p) => [x(p.x), y(totals.get(p.x) ?? 0)]))
    : ''
  const first = valid[0]
  const last = valid.at(-1)
  const grandTotal = last ? (totals.get(last.x) ?? 0) : 0
  const area = first && last ? `${line}L${x(last.x)},${baseline}L${x(first.x)},${baseline}Z` : ''
  type Valid = (typeof valid)[number]
  const lowest = valid.reduce<Valid | undefined>((a, p) => (!a || p.y < a.y ? p : a), undefined)
  const highest = valid.reduce<Valid | undefined>((a, p) => (!a || p.y > a.y ? p : a), undefined)

  // Mostra o valor da hora mais próxima do cursor.
  function onPointer(event: PointerEvent<SVGSVGElement>) {
    const position = event.clientX - event.currentTarget.getBoundingClientRect().left
    const index = Math.round((position - MARGIN.left - step / 2) / step)
    setHover(points[Math.min(Math.max(index, 0), points.length - 1)] ?? null)
  }

  function extremeLabel(point: Valid, above: boolean) {
    const px = x(point.x)
    const anchor = px < MARGIN.left + 30 ? 'start' : px > width - 30 ? 'end' : 'middle'
    return (
      <g>
        <circle
          cx={px}
          cy={y(point.y)}
          r={3.5}
          className="fill-paper stroke-accent"
          strokeWidth={2}
        />
        <text
          x={px}
          y={y(point.y) + (above ? -8 : 14)}
          textAnchor={anchor}
          className="fill-ink stroke-paper text-[10px] font-bold"
          strokeWidth={3}
          paintOrder="stroke"
        >
          {formatY(point.y)}
        </text>
      </g>
    )
  }

  return (
    <figure ref={ref} aria-label={label} className="relative w-full">
      {showTotal && (
        <div className="mb-1 flex gap-4 text-[11px] text-ink-soft">
          <span className="flex items-center gap-1.5">
            <span aria-hidden="true" className="inline-block h-2.5 w-2 rounded-t-sm bg-ink-soft" />
            por hora
          </span>
          <span className="flex items-center gap-1.5">
            <span aria-hidden="true" className="inline-block h-0.5 w-4 bg-accent" />
            acumulado no dia
          </span>
        </div>
      )}
      {width > 0 && valid.length > 0 && (
        <svg
          width={width}
          height={height}
          aria-hidden="true"
          className="touch-none select-none"
          onPointerMove={onPointer}
          onPointerDown={onPointer}
          onPointerLeave={() => setHover(null)}
        >
          {yTicks.map((tick) => (
            <g key={tick}>
              <line
                x1={MARGIN.left}
                x2={width - MARGIN.right}
                y1={y(tick)}
                y2={y(tick)}
                className={tick === yMin ? 'stroke-ink-soft' : 'stroke-paper-dark'}
              />
              <text
                x={MARGIN.left - 5}
                y={y(tick)}
                dy="0.32em"
                textAnchor="end"
                className="fill-ink-soft text-[10px] tabular-nums"
              >
                {formatY(tick)}
              </text>
            </g>
          ))}
          {xTicks.map((tick) => (
            <text
              key={tick}
              x={x(tick)}
              y={height - 5}
              textAnchor="middle"
              className="fill-ink-soft text-[10px] tabular-nums"
            >
              {formatX(tick)}
            </text>
          ))}
          {hover && (
            <line
              x1={x(hover.x)}
              x2={x(hover.x)}
              y1={MARGIN.top}
              y2={baseline}
              className="stroke-ink-soft"
              strokeWidth={1}
            />
          )}
          {kind === 'area' && (
            <>
              {yMin === 0 && <path d={area} className="fill-accent opacity-10" />}
              <path
                d={line}
                fill="none"
                className="stroke-accent"
                strokeWidth={2}
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </>
          )}
          {kind === 'bars' &&
            valid.map((p) => {
              const top = y(p.y)
              const barWidth = Math.max(Math.min(step - 2, 10), 4)
              const left = x(p.x) - barWidth / 2
              if (baseline - top < 0.5) return null
              const radius = Math.min(2, (baseline - top) / 2)
              return (
                <path
                  key={p.x}
                  d={`M${left},${baseline}V${top + radius}q0,-${radius} ${radius},-${radius}H${left + barWidth - radius}q${radius},0 ${radius},${radius}V${baseline}Z`}
                  className={hover?.x === p.x ? 'fill-accent' : 'fill-ink-soft'}
                />
              )
            })}
          {showTotal && grandTotal > 0 && last && (
            <g>
              <path
                d={totalLine}
                fill="none"
                className="stroke-accent"
                strokeWidth={2}
                strokeLinecap="round"
                strokeLinejoin="round"
              />
              <circle
                cx={x(last.x)}
                cy={y(grandTotal)}
                r={4}
                className="fill-accent stroke-paper"
                strokeWidth={2}
              />
              <text
                x={x(last.x) - 8}
                y={y(grandTotal) - 8}
                textAnchor="end"
                className="fill-ink stroke-paper text-[10px] font-bold"
                strokeWidth={3}
                paintOrder="stroke"
              >
                {formatY(grandTotal)}
              </text>
            </g>
          )}
          {showTotal && hover && hover.y !== null && grandTotal > 0 && (
            <circle
              cx={x(hover.x)}
              cy={y(totals.get(hover.x) ?? 0)}
              r={4}
              className="fill-accent stroke-paper"
              strokeWidth={2}
            />
          )}
          {extremes && lowest && highest && lowest !== highest && (
            <>
              {extremeLabel(highest, true)}
              {extremeLabel(lowest, false)}
            </>
          )}
          {hover && hover.y !== null && kind === 'area' && (
            <circle
              cx={x(hover.x)}
              cy={y(hover.y)}
              r={4}
              className="fill-accent stroke-paper"
              strokeWidth={2}
            />
          )}
        </svg>
      )}
      {hover && (
        <div
          className="pointer-events-none absolute z-10 -translate-x-1/2 border border-ink bg-paper px-2 py-0.5 text-xs whitespace-nowrap shadow"
          style={{
            top: showTotal ? 20 : 0,
            left: Math.min(
              Math.max(x(hover.x), showTotal ? 80 : 45),
              width - (showTotal ? 80 : 45),
            ),
          }}
        >
          <span className="font-bold">{formatX(hover.x)}</span>:{' '}
          {hover.y === null ? 'sem dado' : formatY(hover.y)}
          {showTotal && hover.y !== null && (
            <span className="text-ink-soft"> · acumulado {formatY(totals.get(hover.x) ?? 0)}</span>
          )}
        </div>
      )}
    </figure>
  )
}
