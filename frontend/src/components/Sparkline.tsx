import { type PointerEvent, useState } from 'react'
import type { Indicator } from '../api/types'
import { formatIndicator } from '../util/format'
import { useWidth } from './Chart'

const HEIGHT = 64
const MARGIN = { top: 8, right: 6, bottom: 16, left: 6 }

// A inflação varia demais (hiperinflação); usa escala logarítmica.
export const LOG_SCALE_CODES = new Set(['FP.CPI.TOTL.ZG'])

export function Sparkline({ indicator }: { indicator: Indicator }) {
  const [ref, width] = useWidth()
  const [hover, setHover] = useState<number | null>(null)
  const points = (indicator.series ?? []).filter(
    (p) => !LOG_SCALE_CODES.has(indicator.code) || p.value > 0,
  )
  if (points.length < 2) return null

  const log = LOG_SCALE_CODES.has(indicator.code)
  const scale = (value: number) => (log ? Math.log10(value) : value)
  const years = points.map((p) => p.year)
  const values = points.map((p) => scale(p.value))
  const [minYear, maxYear] = [Math.min(...years), Math.max(...years)]
  const [minValue, maxValue] = [Math.min(...values), Math.max(...values)]
  const plotWidth = Math.max(width - MARGIN.left - MARGIN.right, 10)
  const plotHeight = HEIGHT - MARGIN.top - MARGIN.bottom
  const x = (year: number) =>
    MARGIN.left + ((year - minYear) / (maxYear - minYear || 1)) * plotWidth
  const y = (value: number) =>
    MARGIN.top + plotHeight - ((scale(value) - minValue) / (maxValue - minValue || 1)) * plotHeight
  const baseline = MARGIN.top + plotHeight
  const line = points
    .map((p, i) => `${i ? 'L' : 'M'}${x(p.year).toFixed(1)},${y(p.value).toFixed(1)}`)
    .join('')
  const last = points.at(-1)
  const then = points.find((p) => p.year === indicator.then_year)
  const hovered = hover === null ? null : points[hover]

  const thenIndex = then ? points.indexOf(then) : points.length - 1

  function onPointer(event: PointerEvent<HTMLInputElement>) {
    const position = event.clientX - event.currentTarget.getBoundingClientRect().left
    const year = minYear + (position / plotWidth) * (maxYear - minYear)
    let nearest = 0
    points.forEach((p, i) => {
      if (Math.abs(p.year - year) < Math.abs((points[nearest]?.year ?? 0) - year)) nearest = i
    })
    setHover(nearest)
  }

  const format = (value: number) => formatIndicator(value, indicator.unit)
  const summary =
    `${indicator.name} de ${minYear} a ${maxYear}: ` +
    `${format(points[0]?.value ?? 0)} em ${minYear}, ${last ? format(last.value) : ''} em ${maxYear}.` +
    (log ? ' Escala logarítmica.' : '')

  return (
    <figure
      ref={ref}
      className="relative mt-2 w-full has-[input:focus-visible]:outline has-[input:focus-visible]:outline-offset-2 has-[input:focus-visible]:outline-ink"
    >
      {width > 0 && (
        <svg width={width} height={HEIGHT} aria-hidden="true" className="overflow-visible">
          <line
            x1={MARGIN.left}
            x2={width - MARGIN.right}
            y1={baseline}
            y2={baseline}
            className="stroke-paper-dark"
          />
          <path
            d={line}
            fill="none"
            className="stroke-ink-soft"
            strokeWidth={2}
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          {hovered && (
            <line
              x1={x(hovered.year)}
              x2={x(hovered.year)}
              y1={MARGIN.top - 4}
              y2={baseline}
              className="stroke-ink-soft"
              strokeWidth={1}
            />
          )}
          {last && (
            <circle
              cx={x(last.year)}
              cy={y(last.value)}
              r={4}
              className="fill-ink stroke-paper"
              strokeWidth={2}
            />
          )}
          {then && (
            <circle
              cx={x(then.year)}
              cy={y(then.value)}
              r={4.5}
              className="fill-accent stroke-paper"
              strokeWidth={2}
            />
          )}
          {hovered && hovered !== then && hovered !== last && (
            <circle
              cx={x(hovered.year)}
              cy={y(hovered.value)}
              r={4}
              className="fill-ink-soft stroke-paper"
              strokeWidth={2}
            />
          )}
          {[minYear, maxYear].map((year, i) => (
            <text
              key={year}
              x={x(year)}
              y={HEIGHT - 3}
              textAnchor={i ? 'end' : 'start'}
              className="fill-ink-soft text-[10px] tabular-nums"
            >
              {year}
            </text>
          ))}
          {log && (
            <text
              x={width / 2}
              y={HEIGHT - 3}
              textAnchor="middle"
              className="fill-ink-soft text-[9px] italic"
            >
              escala log.
            </text>
          )}
        </svg>
      )}
      <input
        type="range"
        min={0}
        max={points.length - 1}
        step={1}
        value={hover ?? thenIndex}
        aria-label={summary}
        aria-valuetext={hovered ? `${format(hovered.value)} em ${hovered.year}` : summary}
        onChange={(event) => setHover(Number(event.target.value))}
        onPointerMove={onPointer}
        onPointerDown={onPointer}
        onPointerLeave={() => setHover(null)}
        onFocus={() => setHover(thenIndex)}
        onBlur={() => setHover(null)}
        className="absolute top-0 m-0 cursor-crosshair touch-none opacity-0"
        style={{ left: MARGIN.left, width: plotWidth, height: HEIGHT - MARGIN.bottom }}
      />
      {hovered && (
        <div
          className="pointer-events-none absolute -top-7 z-10 -translate-x-1/2 border border-ink bg-paper px-2 py-0.5 text-xs whitespace-nowrap shadow"
          style={{ left: Math.min(Math.max(x(hovered.year), 50), width - 50) }}
        >
          <span className="font-bold">{format(hovered.value)}</span>{' '}
          <span className="text-ink-soft">em {hovered.year}</span>
        </div>
      )}
    </figure>
  )
}
