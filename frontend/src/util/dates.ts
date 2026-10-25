export const MIN_DATE = '1900-01-01'
const TIMEZONE = 'America/Sao_Paulo'
const ISO_DATE = /^\d{4}-\d{2}-\d{2}$/

// Último dia permitido, no fuso de São Paulo, como no servidor.
export function yesterdayIso(): string {
  const today = new Intl.DateTimeFormat('en-CA', { timeZone: TIMEZONE }).format(new Date())
  const date = new Date(`${today}T12:00:00Z`)
  date.setUTCDate(date.getUTCDate() - 1)
  return date.toISOString().slice(0, 10)
}

export function isValidIsoDate(value: string): boolean {
  if (!ISO_DATE.test(value)) return false
  const date = new Date(`${value}T12:00:00Z`)
  return !Number.isNaN(date.getTime()) && date.toISOString().slice(0, 10) === value
}

// Mesma validação do servidor, para avisar antes de fazer a requisição.
export function dateProblem(value: string): string | null {
  if (!isValidIsoDate(value)) return 'Escolha uma data válida.'
  if (value < MIN_DATE) return 'Nosso arquivo começa em 1º de janeiro de 1900.'
  if (value > yesterdayIso())
    return 'Essa edição ainda não foi impressa. Escolha uma data até ontem.'
  return null
}

function toUtcDate(iso: string): Date {
  return new Date(`${iso}T12:00:00Z`)
}

export function longDate(iso: string): string {
  const text = new Intl.DateTimeFormat('pt-BR', { dateStyle: 'full', timeZone: 'UTC' }).format(
    toUtcDate(iso),
  )
  return text.charAt(0).toUpperCase() + text.slice(1)
}

export function dayAndMonth(iso: string): string {
  return new Intl.DateTimeFormat('pt-BR', {
    day: 'numeric',
    month: 'long',
    timeZone: 'UTC',
  }).format(toUtcDate(iso))
}

export function monthAndYear(iso: string): string {
  return new Intl.DateTimeFormat('pt-BR', {
    month: 'long',
    year: 'numeric',
    timeZone: 'UTC',
  }).format(toUtcDate(iso))
}

export function issueNumber(iso: string): number {
  const day = 24 * 60 * 60 * 1000
  return Math.round((toUtcDate(iso).getTime() - toUtcDate(MIN_DATE).getTime()) / day) + 1
}

export function shiftDay(iso: string, days: number): string {
  const date = toUtcDate(iso)
  date.setUTCDate(date.getUTCDate() + days)
  return date.toISOString().slice(0, 10)
}

export function randomDate(): string {
  const first = toUtcDate(MIN_DATE).getTime()
  const last = toUtcDate(yesterdayIso()).getTime()
  return new Date(first + Math.random() * (last - first)).toISOString().slice(0, 10)
}
