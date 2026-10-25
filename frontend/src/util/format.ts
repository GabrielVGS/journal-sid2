const compact = new Intl.NumberFormat('pt-BR', {
  notation: 'compact',
  compactDisplay: 'long',
  maximumFractionDigits: 1,
})
const oneDecimal = new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 1 })
const integer = new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 0 })

export function formatIndicator(value: number, unit: string): string {
  if (unit === 'habitantes') return `${compact.format(value)} de habitantes`
  if (unit === 'US$') return `US$ ${integer.format(value)}`
  if (value > 0 && value < 0.05)
    return `menos de 0,1 ${unit === '%' ? '%' : unit}`.replace(' %', '%')
  if (unit === '%') return `${oneDecimal.format(value)}%`
  return `${oneDecimal.format(value)} ${unit}`
}

export function formatMoney(value: number, symbol: string): string {
  const digits = value < 100 ? 2 : 0
  const number = new Intl.NumberFormat('pt-BR', {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  }).format(value)
  return `${symbol} ${number}`
}

export function formatInteger(value: number): string {
  return integer.format(value)
}
