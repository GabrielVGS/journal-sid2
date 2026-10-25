import { formatInteger } from '../util/format'
import { issueNumber, longDate } from '../util/dates'

export function Masthead({ date }: { date?: string }) {
  return (
    <header className="text-center">
      {date && (
        <div className="border-b border-ink pb-1 text-xs tracking-wide uppercase">
          Edição nº {formatInteger(issueNumber(date))}
        </div>
      )}
      <h1 className="py-3 font-display text-4xl leading-none font-black tracking-tight sm:text-6xl md:text-7xl">
        O Jornal do Dia
      </h1>
      <p className="rule-double py-1 text-sm italic sm:text-base">
        {date ? longDate(date) : 'Qualquer dia, desde 1900'}
      </p>
    </header>
  )
}
