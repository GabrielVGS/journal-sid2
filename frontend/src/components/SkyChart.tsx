import { useId } from 'react'
import type { Moon, Sky, SkyObject } from '../api/types'
import { moonLit } from './MoonSection'

const SIZE = 440
const C = SIZE / 2
const R = 180 // horizon
const RIM = 200 // outer edge of the graduated ring

/** Zenith at the center, horizon at R. Looking up with north at the top, east is on the
 * LEFT (a sky chart is a mirror of a map). */
function project(o: SkyObject): [number, number] {
  const r = (R * (90 - o.altitude)) / 90
  const az = (o.azimuth * Math.PI) / 180
  return [C - r * Math.sin(az), C - r * Math.cos(az)]
}

function onRing(degrees: number, r: number): [number, number] {
  const az = (degrees * Math.PI) / 180
  return [C - r * Math.sin(az), C - r * Math.cos(az)]
}

/** Engraved four-pointed star for the bright ones (magnitude under 1.3), a dot for the
 * rest; brighter = bigger (magnitudes run backwards). */
function StarMark({ star }: { star: SkyObject }) {
  const [x, y] = project(star)
  const magnitude = star.magnitude ?? 2
  if (magnitude < 1.3) {
    const s = Math.min(8, Math.max(3.2, 6.2 - 1.6 * magnitude))
    const k = 0.26 * s
    const d =
      `M${x},${y - s} L${x + k},${y - k} L${x + s},${y} L${x + k},${y + k} ` +
      `L${x},${y + s} L${x - k},${y + k} L${x - s},${y} L${x - k},${y - k}Z`
    return <path d={d} className="fill-ink" />
  }
  const r = Math.min(2.6, Math.max(1.2, 3.4 - 0.7 * magnitude))
  return <circle cx={x} cy={y} r={r} className="fill-ink" />
}

interface Placed {
  text: string
  x: number
  y: number
  anchor: 'start' | 'middle' | 'end'
  kind: 'body' | 'constellation' | 'star'
}

type Box = [number, number, number, number] // left, top, right, bottom

function overlaps(a: Box, b: Box): boolean {
  return a[0] < b[2] && b[0] < a[2] && a[1] < b[3] && b[1] < a[3]
}

const LABEL_SIZE = { body: 13, constellation: 10.5, star: 10 }

/** Puts each label in the first free spot around its point (above, below, the sides,
 * the diagonals, a bit farther), so names never sit on each other or on a planet; a
 * label with no free spot is left out (the guide below names everything that matters). */
function placeLabels(
  wanted: { text: string; x: number; y: number; kind: Placed['kind'] }[],
  marks: Box[],
): Placed[] {
  const taken = [...marks]
  const placed: Placed[] = []
  for (const label of wanted) {
    const size = LABEL_SIZE[label.kind]
    const width = label.text.length * size * 0.55
    const gap = label.kind === 'body' ? 12 : 9
    const candidates: [number, number, Placed['anchor']][] = [
      [0, -gap, 'middle'],
      [0, gap + size, 'middle'],
      [gap, size / 3, 'start'],
      [-gap, size / 3, 'end'],
      [gap, -gap, 'start'],
      [-gap, -gap, 'end'],
      [gap, gap + size, 'start'],
      [-gap, gap + size, 'end'],
      [0, -2 * gap - size, 'middle'],
    ]
    for (const [dx, dy, anchor] of candidates) {
      const x = label.x + dx
      const y = label.y + dy
      const left = anchor === 'start' ? x : anchor === 'end' ? x - width : x - width / 2
      const box: Box = [left, y - size, left + width, y + 2]
      // Labels stay inside the horizon (the ring belongs to the compass).
      const inside = Math.hypot(box[0] - C, y - C) < R - 4 && Math.hypot(box[2] - C, y - C) < R - 4
      if (inside && !taken.some((other) => overlaps(box, other))) {
        taken.push(box)
        placed.push({ text: label.text, x, y, anchor, kind: label.kind })
        break
      }
    }
  }
  return placed
}

const SYMBOLS: Record<string, string> = {
  Mercúrio: '☿',
  Vênus: '♀',
  Marte: '♂',
  Júpiter: '♃',
  Saturno: '♄',
}

/**
 * The night sky over Brasília at 21:00 as an almanac star chart: a graduated compass
 * ring, the stars engraved in ink (the bright ones as four-pointed stars), three
 * constellation outlines, the planets in the accent color with their almanac symbols
 * and the Moon drawn in its real phase. Only what is above the horizon is drawn.
 */
function SkyChart({ sky, moon }: { sky: Sky; moon?: Moon }) {
  const id = useId().replace(/:/g, '')
  const gradient = `sky-${id}`
  const hatch = `sky-hatch-${id}`
  const up = sky.objects.filter((o) => o.altitude > 0)
  const stars = up.filter((o) => o.kind === 'star')
  const byName = new Map(stars.map((s) => [s.name, s]))
  const planets = up.filter((o) => o.kind === 'planet')
  const moonUp = up.find((o) => o.kind === 'moon')

  const constellations = (sky.constellations ?? []).flatMap((constellation) => {
    const segments = constellation.lines
      .map(([a, b]) => [byName.get(a ?? ''), byName.get(b ?? '')] as const)
      .filter((pair): pair is readonly [SkyObject, SkyObject] => !!pair[0] && !!pair[1])
    if (segments.length === 0) return []
    const points = segments.flatMap(([a, b]) => [project(a), project(b)])
    const x = points.reduce((sum, [px]) => sum + px, 0) / points.length
    const y = Math.max(...points.map(([, py]) => py))
    return [{ name: constellation.name, segments, x, y }]
  })

  // Planets and the Moon are named first (they are the news), then constellations, then
  // the four brightest stars.
  const bodies = [...(moonUp ? [moonUp] : []), ...planets]
  // Names keep off every drawn point: the Moon, planets and stars.
  const marks: Box[] = [...bodies, ...stars].map((o) => {
    const [x, y] = project(o)
    const r = o.kind === 'moon' ? 12 : o.kind === 'planet' ? 9 : 4
    return [x - r, y - r, x + r, y + r]
  })
  const brightest = stars.toSorted((a, b) => (a.magnitude ?? 9) - (b.magnitude ?? 9)).slice(0, 4)
  const labels = placeLabels(
    [
      ...bodies.map((body) => {
        const [x, y] = project(body)
        const symbol = body.kind === 'moon' ? '☾' : (SYMBOLS[body.name] ?? '')
        return { text: `${symbol} ${body.name}`.trim(), x, y, kind: 'body' as const }
      }),
      ...constellations.map((c) => ({
        text: c.name,
        x: c.x,
        y: c.y,
        kind: 'constellation' as const,
      })),
      ...brightest.map((star) => {
        const [x, y] = project(star)
        return { text: star.name, x, y, kind: 'star' as const }
      }),
    ],
    marks,
  )

  const ticks = Array.from({ length: 36 }, (_, i) => i * 10)
  return (
    <svg viewBox={`0 0 ${SIZE} ${SIZE}`} aria-hidden="true" className="mx-auto w-full max-w-md">
      <defs>
        <radialGradient id={gradient} cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="var(--color-paper)" />
          <stop offset="100%" stopColor="var(--color-paper-dark)" />
        </radialGradient>
        <pattern
          id={hatch}
          width="3.2"
          height="3.2"
          patternUnits="userSpaceOnUse"
          patternTransform="rotate(45)"
        >
          <line x1="0" y1="0" x2="0" y2="3.2" className="stroke-ink" strokeWidth="1.1" />
        </pattern>
      </defs>

      {/* Compass ring: degrees every 10°, longer every 30°. */}
      <circle cx={C} cy={C} r={RIM} className="fill-paper stroke-ink" strokeWidth={2.5} />
      <circle
        cx={C}
        cy={C}
        r={R}
        fill={`url(#${gradient})`}
        className="stroke-ink"
        strokeWidth={1.2}
      />
      {ticks.map((deg) => {
        const long = deg % 30 === 0
        const [x1, y1] = onRing(deg, R + 2)
        const [x2, y2] = onRing(deg, long ? R + 16 : R + 9)
        return (
          <line
            key={deg}
            x1={x1}
            y1={y1}
            x2={x2}
            y2={y2}
            className="stroke-ink"
            strokeWidth={long ? 1.4 : 0.8}
          />
        )
      })}
      <g
        className="fill-ink font-display text-[11px] font-bold"
        letterSpacing={2}
        textAnchor="middle"
      >
        <text x={C} y={14}>
          NORTE
        </text>
        <text x={C} y={SIZE - 4}>
          SUL
        </text>
        <text x={12} y={C} transform={`rotate(-90 12 ${C})`}>
          LESTE
        </text>
        <text x={SIZE - 12} y={C} transform={`rotate(90 ${SIZE - 12} ${C})`}>
          OESTE
        </text>
      </g>

      {/* Altitude rings at 30° and 60°, and the zenith. */}
      {[30, 60].map((altitude) => {
        const r = (R * (90 - altitude)) / 90
        return (
          <g key={altitude}>
            <circle
              cx={C}
              cy={C}
              r={r}
              fill="none"
              className="stroke-paper-dark"
              strokeWidth={1.2}
            />
            <text x={C + 4} y={C - r - 3} className="fill-ink-soft text-[9px] italic">
              {altitude}°
            </text>
          </g>
        )
      })}
      <path d={`M${C} ${C - 6}V${C + 6}M${C - 6} ${C}H${C + 6}`} className="stroke-ink-soft" />

      {constellations.map((c) =>
        c.segments.map(([a, b]) => {
          const [x1, y1] = project(a)
          const [x2, y2] = project(b)
          return (
            <line
              key={`${a.name}-${b.name}`}
              x1={x1}
              y1={y1}
              x2={x2}
              y2={y2}
              className="stroke-ink-soft"
              strokeWidth={1}
            />
          )
        }),
      )}
      {stars.map((star) => (
        <StarMark key={star.name} star={star} />
      ))}

      {planets.map((planet) => {
        const [x, y] = project(planet)
        return (
          <circle
            key={planet.name}
            cx={x}
            cy={y}
            r={7}
            className="fill-accent stroke-paper"
            strokeWidth={2.5}
          />
        )
      })}
      {moonUp && <MoonMark at={project(moonUp)} moon={moon} hatch={hatch} />}

      {/* Labels last, with a paper halo, so lines and dots never cover them. */}
      {labels.map((label) => (
        <text
          key={label.text}
          x={label.x}
          y={label.y}
          textAnchor={label.anchor}
          className={
            label.kind === 'body'
              ? 'fill-ink font-display text-[13px] font-bold'
              : label.kind === 'constellation'
                ? 'fill-ink-soft text-[10.5px] italic'
                : 'fill-ink-soft text-[10px] italic'
          }
          stroke="var(--color-paper)"
          strokeWidth={3.5}
          paintOrder="stroke"
        >
          {label.text}
        </text>
      ))}
    </svg>
  )
}

/** The Moon on the chart in its real phase (hatched dark part, paper lit part); a plain
 * disc while the phase is still loading. */
function MoonMark({ at, moon, hatch }: { at: [number, number]; moon?: Moon; hatch: string }) {
  const [x, y] = at
  const lit = moon ? moonLit(moon, x, y, 10) : null
  return (
    <g>
      <circle cx={x} cy={y} r={10} fill={`url(#${hatch})`} />
      {lit ? (
        <path d={lit.d} className="fill-paper" transform={lit.transform} />
      ) : (
        <circle cx={x} cy={y} r={10} className="fill-paper" />
      )}
      <circle cx={x} cy={y} r={10} fill="none" className="stroke-ink" strokeWidth={1.6} />
    </g>
  )
}

/** "O céu daquela noite": the almanac chart and "O que olhar", in words. */
export function SkySection({ sky, moon }: { sky: Sky; moon?: Moon }) {
  const guide = sky.guide ?? []
  return (
    <div className="space-y-3 text-sm">
      <SkyChart sky={sky} moon={moon} />
      {guide.length > 0 ? (
        <div className="space-y-1.5 border-t border-ink pt-2">
          <p className="font-display text-xs font-bold tracking-[0.15em] uppercase">O que olhar</p>
          <ul className="space-y-1">
            {guide.map((tip) => (
              <li key={tip.title} className="grid grid-cols-[1.25rem_minmax(0,1fr)] gap-1.5">
                <span aria-hidden="true" className="font-bold text-accent">
                  {tip.symbol}
                </span>
                <span>
                  <span className="font-bold">{tip.title}</span>: {tip.detail}
                </span>
              </li>
            ))}
          </ul>
        </div>
      ) : (
        <p className="border-t border-ink pt-2">Nenhum planeta à vista às 21h.</p>
      )}
      <p className="text-xs text-ink-soft italic">
        Céu de Brasília às 21h. Olhando para cima, o leste fica à esquerda. Lua e planetas: NASA JPL
        Horizons.
      </p>
    </div>
  )
}
