import { useId } from 'react'

export function FoldedNewspaper({ className = 'w-56' }: { className?: string }) {
  const id = useId().replace(/:/g, '')
  const hatch = `hatch-${id}`
  const cross = `cross-${id}`
  return (
    <svg viewBox="0 0 420 360" aria-hidden="true" className={`text-ink ${className}`}>
      <defs>
        <pattern
          id={hatch}
          width="5"
          height="5"
          patternUnits="userSpaceOnUse"
          patternTransform="rotate(45)"
        >
          <line x1="0" y1="0" x2="0" y2="5" stroke="currentColor" strokeWidth="1.3" />
        </pattern>
        <pattern
          id={cross}
          width="5"
          height="5"
          patternUnits="userSpaceOnUse"
          patternTransform="rotate(45)"
        >
          <line x1="0" y1="0" x2="0" y2="5" stroke="currentColor" strokeWidth="1.1" />
          <line x1="0" y1="0" x2="5" y2="0" stroke="currentColor" strokeWidth="1.1" />
        </pattern>
      </defs>
      <g
        fill="none"
        stroke="currentColor"
        strokeWidth="3"
        strokeLinejoin="round"
        strokeLinecap="round"
      >
        <ellipse cx="210" cy="328" rx="170" ry="10" fill={`url(#${hatch})`} stroke="none" />
        <g transform="rotate(-6 210 180)">
          <path d="M84 52 L330 40 L338 300 L92 312 Z" className="fill-paper" strokeWidth="2" />
          <path d="M76 46 L322 34 L330 294 L84 306 Z" className="fill-paper" />
          <line x1="88" y1="70" x2="318" y2="60" strokeWidth="2" />
          <line x1="88" y1="74" x2="318" y2="64" strokeWidth="1" />
          <path d="M128 92 L282 85" strokeWidth="12" />
          <line x1="90" y1="110" x2="320" y2="100" strokeWidth="2" />
          <line x1="90" y1="114" x2="320" y2="104" strokeWidth="1" />
          <path d="M98 132 L310 123 M98 146 L262 139" strokeWidth="7" />
          <rect
            x="98"
            y="160"
            width="104"
            height="80"
            fill={`url(#${cross})`}
            strokeWidth="2"
            transform="rotate(-2.4 150 200)"
          />
          <path
            d="M214 160 H312 M214 170 H306 M214 180 H310 M214 190 H300 M214 200 H312 M214 210 H296 M214 220 H308 M214 230 H286"
            strokeWidth="1.5"
            transform="rotate(-2.4 260 195)"
          />
          <path
            d="M100 258 H196 M100 268 H190 M100 278 H194 M100 288 H160"
            strokeWidth="1.5"
            transform="rotate(-2.4 150 270)"
          />
          <path
            d="M214 250 H312 M214 260 H304 M214 270 H310 M214 280 H262"
            strokeWidth="1.5"
            transform="rotate(-2.4 260 265)"
          />
        </g>
      </g>
    </svg>
  )
}
