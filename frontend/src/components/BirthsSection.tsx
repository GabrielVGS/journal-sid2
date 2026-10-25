import type { Birth } from '../api/types'

function formatYear(year: number): string {
  return year < 0 ? `${-year} a.C.` : String(year)
}

export function BirthsSection({
  births,
  obituary = false,
}: {
  births: Birth[]
  obituary?: boolean
}) {
  return (
    <ul className="grid grid-cols-2 gap-4 sm:grid-cols-4 print:grid-cols-4">
      {births.map((birth) => (
        <li key={`${birth.year}-${birth.text}`} className="flex gap-3">
          {birth.image_url ? (
            <img
              src={birth.image_url}
              alt=""
              className="newspaper-photo h-14 w-14 shrink-0 rounded-full border border-ink bg-paper-dark object-cover"
            />
          ) : (
            <div
              aria-hidden="true"
              className="flex h-14 w-14 shrink-0 items-center justify-center rounded-full border border-ink font-display text-2xl font-bold"
            >
              {birth.text.charAt(0)}
            </div>
          )}
          <p className="text-sm leading-snug">
            <span className="font-bold">
              {obituary && '† '}
              {formatYear(birth.year)}
            </span>
            {' — '}
            {birth.url ? (
              <a href={birth.url} target="_blank" rel="noreferrer" className="hover:underline">
                {birth.text}
              </a>
            ) : (
              birth.text
            )}
          </p>
        </li>
      ))}
    </ul>
  )
}
