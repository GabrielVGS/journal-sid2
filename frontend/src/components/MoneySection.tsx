import type { Money } from '../api/types'
import { monthAndYear } from '../util/dates'
import { formatMoney } from '../util/format'

export function MoneySection({ money }: { money: Money }) {
  const { currency_symbol: symbol } = money
  const month = money.period ? monthAndYear(`${money.period}-01`) : null
  const today = money.today_period ? monthAndYear(`${money.today_period}-01`) : 'hoje'
  const share =
    money.min_wage_then_today != null && money.min_wage_now
      ? money.min_wage_then_today / money.min_wage_now
      : null
  return (
    <div className="space-y-3 text-sm">
      {money.min_wage_then != null && (
        <div>
          <p className="text-xs tracking-wide text-ink-soft uppercase">Salário mínimo · {month}</p>
          <p className="font-display text-xl font-bold">
            {formatMoney(money.min_wage_then, symbol)}
          </p>
          {money.min_wage_then_today != null && (
            <p>
              equivalem a <strong>{formatMoney(money.min_wage_then_today, 'R$')}</strong> em valores
              de {today}
            </p>
          )}
        </div>
      )}
      {money.min_wage_now != null && (
        <div>
          <p className="text-xs tracking-wide text-ink-soft uppercase">Salário mínimo hoje</p>
          <p>{formatMoney(money.min_wage_now, 'R$')}</p>
          {share != null && (
            <div className="mt-1" title="Poder de compra do mínimo de então, frente ao de hoje">
              <div className="h-2 border border-ink">
                <div className="h-full bg-ink" style={{ width: `${Math.min(share, 1) * 100}%` }} />
              </div>
              <p className="mt-0.5 text-xs text-ink-soft">
                O mínimo de então compraria {Math.round(share * 100)}% do que o de hoje compra.
              </p>
            </div>
          )}
        </div>
      )}
      {money.amount_then != null && money.amount_today != null && (
        <div>
          <p className="text-xs tracking-wide text-ink-soft uppercase">Uma nota da época</p>
          <p>
            {formatMoney(money.amount_then, symbol)} de então valem{' '}
            <strong>{formatMoney(money.amount_today, 'R$')}</strong> hoje
          </p>
        </div>
      )}
      {money.note && <p className="text-xs text-ink-soft italic">{money.note}</p>}
    </div>
  )
}
