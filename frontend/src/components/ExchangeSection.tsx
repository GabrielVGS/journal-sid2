import type { Exchange } from '../api/types'
import { formatMoney } from '../util/format'

export function ExchangeSection({ exchange }: { exchange: Exchange }) {
  const { currency } = exchange
  return (
    <div className="space-y-3 text-sm">
      <div>
        <p className="text-xs tracking-wide text-ink-soft uppercase">Moeda em circulação</p>
        <p className="font-display text-2xl font-black">
          {currency.name}{' '}
          <span className="font-body text-base font-normal">({currency.symbol})</span>
        </p>
      </div>
      {exchange.usd_then != null && (
        <div>
          <p className="text-xs tracking-wide text-ink-soft uppercase">
            Dólar na época · {exchange.usd_then_period}
          </p>
          <p className="font-display text-xl font-bold">
            US$ 1 = {formatMoney(exchange.usd_then, currency.symbol)}
          </p>
        </div>
      )}
      {exchange.usd_now != null && (
        <div>
          <p className="text-xs tracking-wide text-ink-soft uppercase">
            Dólar hoje · {exchange.usd_now_period}
          </p>
          <p>US$ 1 = {formatMoney(exchange.usd_now, 'R$')}</p>
        </div>
      )}
      {exchange.note && <p className="text-xs text-ink-soft italic">{exchange.note}</p>}
    </div>
  )
}
