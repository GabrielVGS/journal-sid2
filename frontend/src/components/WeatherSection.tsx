import { useState } from 'react'
import { useWeather } from '../api/queries'
import type { City, HourlyPoint } from '../api/types'
import { CityPicker, cityLabel } from './CityPicker'
import { dayAndMonth } from '../util/dates'
import { Chart } from './Chart'
import { Icon, weatherIcon } from './Icon'
import { NoSignal, Skeleton } from './SectionState'

// A última cidade escolhida fica salva no navegador.
const STORAGE_KEY = 'jornal:city'
const DEFAULT_CITY = 'rio-grande'
const number = new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 1 })
const hour = (value: number) => `${value}h`

const DEFAULT: City = { slug: DEFAULT_CITY, name: 'Rio Grande', state: 'RS', country: 'Brasil' }

function savedCity(): City {
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (!stored) return DEFAULT
    if (!stored.startsWith('{')) return { ...DEFAULT, slug: stored, name: stored }
    return JSON.parse(stored) as City
  } catch {
    return DEFAULT
  }
}

type Variable = 'temperature' | 'precipitation' | 'humidity' | 'wind'

// Os quatro gráficos: temperatura, chuva, umidade e vento.
const VARIABLES: {
  key: Variable
  title: string
  unit: string
  kind: 'area' | 'bars'
  cumulative?: boolean
  domain: 'zero' | 'data' | [number, number]
  extremes?: boolean
  format: (value: number) => string
  summary: (values: number[]) => string
}[] = [
  {
    key: 'temperature',
    title: 'Temperatura',
    unit: '°C',
    kind: 'area',
    domain: 'data',
    extremes: true,
    format: (v) => `${number.format(v)}°`,
    summary: (v) => `média ${number.format(v.reduce((a, b) => a + b, 0) / v.length)}°C`,
  },
  {
    key: 'precipitation',
    title: 'Chuva',
    unit: 'mm',
    kind: 'bars',
    cumulative: true,
    domain: 'zero',
    format: (v) => number.format(v),
    summary: (v) => `total ${number.format(v.reduce((a, b) => a + b, 0))} mm`,
  },
  {
    key: 'humidity',
    title: 'Umidade',
    unit: '%',
    kind: 'area',
    domain: [0, 100],
    format: (v) => `${number.format(v)}%`,
    summary: (v) => `média ${number.format(v.reduce((a, b) => a + b, 0) / v.length)}%`,
  },
  {
    key: 'wind',
    title: 'Vento',
    unit: 'km/h',
    kind: 'area',
    domain: 'zero',
    extremes: true,
    format: (v) => number.format(v),
    summary: (v) => `máximo ${number.format(Math.max(...v))} km/h`,
  },
]

function valuesOf(hourly: HourlyPoint[], key: Variable): number[] {
  return hourly.map((p) => p[key]).filter((v): v is number => v != null)
}

export function WeatherSection({ date }: { date: string }) {
  const [city, setCity] = useState(savedCity)
  const weather = useWeather(date, city.slug)

  function choose(chosen: City) {
    setCity(chosen)
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(chosen))
    } catch {
      // navegador sem armazenamento: só não lembra a cidade
    }
  }

  if (date < '1940-01-01') {
    return <p className="text-sm text-ink-soft italic">Os registros de clima começam em 1940.</p>
  }

  const day = weather.data
  const hourly = day?.hourly ?? []
  const rainSoFar = hourly.reduce<number[]>(
    (sums, p) => [...sums, (sums.at(-1) ?? 0) + (p.precipitation ?? 0)],
    [],
  )
  const icon = weatherIcon(day?.weather_code)
  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4 text-sm">
        <CityPicker value={city} onChange={choose} />
        {weather.isPending && <Skeleton lines={4} />}
        {weather.isError && <NoSignal message={weather.error.message} />}
        {day && (
          <div className="order-first">
            <p className="flex items-center gap-3 font-display text-3xl font-bold">
              {icon && <Icon name={icon} className="h-12 w-12" />}
              {day.description}
            </p>
            <p className="text-base">
              {day.temp_min != null && day.temp_max != null
                ? `Mín. ${number.format(day.temp_min)}° · Máx. ${number.format(day.temp_max)}°C`
                : 'Temperatura sem registro'}
            </p>
            <p className="text-ink-soft">
              {cityLabel(day.city)} · {dayAndMonth(date)} de {date.slice(0, 4)}
            </p>
          </div>
        )}
      </div>

      <div>
        {weather.isPending && <Skeleton lines={10} />}
        {hourly.length > 0 && (
          <>
            <div className="grid gap-x-10 gap-y-8 md:grid-cols-2 print:grid-cols-2">
              {VARIABLES.map((variable) => {
                const values = valuesOf(hourly, variable.key)
                return (
                  <div key={variable.key}>
                    <h3 className="text-xs font-bold tracking-wide uppercase">
                      {variable.title} <span className="normal-case">({variable.unit})</span>
                      {values.length > 0 && (
                        <span className="ml-2 font-normal normal-case text-ink-soft">
                          {variable.summary(values)}
                        </span>
                      )}
                    </h3>
                    <Chart
                      kind={variable.kind}
                      domain={variable.domain}
                      extremes={variable.extremes}
                      cumulative={variable.cumulative}
                      label={`${variable.title} hora a hora em ${dayAndMonth(date)} de ${date.slice(0, 4)}`}
                      points={hourly.map((p) => ({ x: p.hour, y: p[variable.key] ?? null }))}
                      formatX={hour}
                      formatY={variable.format}
                      xTicks={[0, 3, 6, 9, 12, 15, 18, 21, 23]}
                      height={220}
                    />
                  </div>
                )
              })}
            </div>
            <p className="mt-3 text-xs text-ink-soft italic">
              Reanálise climática ERA5 (Open-Meteo). Passe o mouse nos gráficos para ver cada hora.
            </p>
            <details className="no-print mt-1 text-xs">
              <summary className="cursor-pointer text-ink-soft">Ver os dados em tabela</summary>
              <table className="mt-1 w-full max-w-md tabular-nums">
                <thead>
                  <tr className="text-left text-ink-soft">
                    <th scope="col">Hora</th>
                    {VARIABLES.map((variable) => (
                      <th key={variable.key} scope="col">
                        {variable.title} ({variable.unit})
                      </th>
                    ))}
                    <th scope="col">Chuva acumulada (mm)</th>
                  </tr>
                </thead>
                <tbody>
                  {hourly.map((p, index) => (
                    <tr key={p.hour}>
                      <td>{hour(p.hour)}</td>
                      {VARIABLES.map((variable) => (
                        <td key={variable.key}>
                          {p[variable.key] == null ? '—' : number.format(p[variable.key] ?? 0)}
                        </td>
                      ))}
                      <td>{number.format(rainSoFar[index] ?? 0)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </details>
          </>
        )}
      </div>
    </div>
  )
}
