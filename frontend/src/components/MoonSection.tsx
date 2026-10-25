import { useId } from 'react'
import type { Moon } from '../api/types'

const R = 40
const C = 46

/** "26/07" */
function shortDate(iso: string): string {
  return iso.slice(8, 10) + '/' + iso.slice(5, 7)
}

/**
 * The Moon as seen from Brazil, engraving style: the dark part hatched, the lit part in
 * paper. In the southern hemisphere a waxing Moon is lit on the LEFT (the opposite of
 * the usual northern drawings), so the waning one is the mirror image. Decorative: the
 * phase and the illuminated share are written next to it.
 */
/** Lit part of a Moon of radius `r` at (cx, cy), as seen from Brazil: an SVG path plus the
 * transform that mirrors it for a waning Moon. Shared with the sky chart. */
export function moonLit(
  moon: Pick<Moon, 'phase_angle' | 'illumination' | 'waxing'>,
  cx: number,
  cy: number,
  r: number,
): { d: string; transform: string | undefined } {
  // Terminator: half an ellipse whose width follows the phase (0 at the quarters).
  const rx = Math.abs(Math.cos((moon.phase_angle * Math.PI) / 180)) * r
  const crescent = moon.illumination < 0.5
  // Lit side on the left: outer left half-circle top -> bottom, then the terminator back
  // up, bulging left (crescent) or right (gibbous).
  const d = `M${cx},${cy - r} A${r},${r} 0 0 0 ${cx},${cy + r} A${rx},${r} 0 0 ${crescent ? 1 : 0} ${cx},${cy - r}Z`
  // Waning: the same shape, lit on the right.
  return { d, transform: moon.waxing ? undefined : `translate(${2 * cx} 0) scale(-1 1)` }
}

function MoonDrawing({ moon }: { moon: Moon }) {
  const hatch = `moon-hatch-${useId().replace(/:/g, '')}`
  const lit = moonLit(moon, C, C, R)
  return (
    <svg viewBox="0 0 92 92" aria-hidden="true" className="h-24 w-24 shrink-0 text-ink">
      <defs>
        <pattern
          id={hatch}
          width="3.4"
          height="3.4"
          patternUnits="userSpaceOnUse"
          patternTransform="rotate(45)"
        >
          <line x1="0" y1="0" x2="0" y2="3.4" stroke="currentColor" strokeWidth="1.3" />
        </pattern>
      </defs>
      <circle cx={C} cy={C} r={R} fill={`url(#${hatch})`} />
      {moon.illumination > 0.005 && (
        <path d={lit.d} className="fill-paper" transform={lit.transform} />
      )}
      {/* A few craters, faint, so the full Moon is not a blank disc. */}
      <g fill="none" stroke="currentColor" strokeWidth="1" opacity="0.35">
        <circle cx="34" cy="34" r="6" />
        <circle cx="56" cy="30" r="3.5" />
        <circle cx="58" cy="56" r="7" />
        <circle cx="36" cy="62" r="4" />
      </g>
      <circle cx={C} cy={C} r={R} fill="none" stroke="currentColor" strokeWidth="2" />
    </svg>
  )
}

/** "A Lua naquela noite": phase, illuminated share and the next main phases. */
export function MoonSection({ moon }: { moon: Moon }) {
  const next = moon.next_phases ?? []
  return (
    <div className="space-y-2 text-sm">
      <div className="flex items-center gap-4">
        <MoonDrawing moon={moon} />
        <div>
          <p className="font-display text-xl leading-tight font-bold">{moon.phase}</p>
          <p>{Math.round(moon.illumination * 100)}% iluminada</p>
          <p className="text-xs text-ink-soft">Vista do Brasil, às 21h</p>
        </div>
      </div>
      {next.length > 0 && (
        <p className="text-xs tracking-wide text-ink-soft uppercase">
          {next.map((p) => `${p.phase} em ${shortDate(p.date)}`).join(' · ')}
        </p>
      )}
    </div>
  )
}
