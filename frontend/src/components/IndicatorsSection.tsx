import type { Indicator } from '../api/types'
import { formatIndicator } from '../util/format'
import { Sparkline } from './Sparkline'

const oneDecimal = new Intl.NumberFormat('pt-BR', {
  maximumFractionDigits: 1,
  signDisplay: 'exceptZero',
})

function change(indicator: Indicator): string | null {
  const { then_value: then, now_value: now, unit } = indicator
  if (indicator.code === 'FP.CPI.TOTL.ZG' || indicator.then_year === indicator.now_year) return null
  if (unit.startsWith('%')) return `${oneDecimal.format(now - then)} p.p.`
  if (unit === 'anos' || unit === 'filhos') {
    const diff = now - then
    return `${oneDecimal.format(diff)} ${Math.abs(diff) < 1.05 && Math.abs(diff) >= 0.95 ? unit.slice(0, -1) : unit}`
  }
  if (then <= 0) return null
  const ratio = now / then
  return ratio >= 3
    ? `${oneDecimal.format(ratio).replace('+', '')}× maior`
    : `${oneDecimal.format((ratio - 1) * 100)}%`
}

function Legend() {
  return (
    <div className="flex flex-col justify-end gap-1 border-t-2 border-ink pt-2 text-xs text-ink-soft">
      <p className="flex items-center gap-2">
        <svg width="12" height="12" aria-hidden="true">
          <circle cx="6" cy="6" r="4.5" className="fill-accent" />
        </svg>
        Ano desta edição (ou o mais próximo com dado)
      </p>
      <p className="flex items-center gap-2">
        <svg width="12" height="12" aria-hidden="true">
          <circle cx="6" cy="6" r="4" className="fill-ink" />
        </svg>
        Dado mais recente
      </p>
      <p className="italic">
        Passe o dedo ou o mouse nos gráficos para ver cada ano. Fonte: Banco Mundial.
      </p>
    </div>
  )
}

export function IndicatorsSection({ indicators }: { indicators: Indicator[] }) {
  return (
    <div className="grid grid-cols-1 gap-x-6 gap-y-6 sm:grid-cols-2 lg:grid-cols-4">
      {indicators.map((indicator) => {
        const delta = change(indicator)
        return (
          <div key={indicator.code} className="flex flex-col border-t-2 border-ink pt-2">
            <h3 className="font-display text-base font-bold">{indicator.name}</h3>
            <div className="mt-1 grid grid-cols-2 gap-3">
              <div>
                <p className="text-xs tracking-wide text-ink-soft uppercase">
                  Então · {indicator.then_year}
                </p>
                <p className="font-display text-lg leading-tight font-bold">
                  {formatIndicator(indicator.then_value, indicator.unit)}
                </p>
              </div>
              <div>
                <p className="text-xs tracking-wide text-ink-soft uppercase">
                  Hoje · {indicator.now_year}
                </p>
                <p className="text-sm leading-tight">
                  {formatIndicator(indicator.now_value, indicator.unit)}
                </p>
                {delta && <p className="mt-0.5 text-xs text-ink-soft">{delta}</p>}
              </div>
            </div>
            <div className="mt-auto">
              <Sparkline indicator={indicator} />
            </div>
          </div>
        )
      })}
      <Legend />
    </div>
  )
}
