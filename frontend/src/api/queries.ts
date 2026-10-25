import { useQuery } from '@tanstack/react-query'
import { ApiRequestError, getJson, postJson } from './client'
import type { Birth, City, Editorial, Event, Exchange, Indicator, Money, Weather } from './types'

// Datas passadas não mudam: o resultado nunca expira.
// Só repete a requisição em falha de rede ou erro 5xx.
const PAST_DATA = {
  staleTime: Infinity,
  gcTime: Infinity,
  retry: (failures: number, error: Error) =>
    failures < 1 &&
    (!(error instanceof ApiRequestError) || error.status === 0 || error.status >= 500),
}

// Um hook por seção: cada uma carrega e falha de forma independente.
export function useEvents(date: string) {
  return useQuery<Event[], ApiRequestError>({
    queryKey: ['events', date],
    queryFn: () => getJson<Event[]>('/api/events', { date }),
    ...PAST_DATA,
  })
}

// Desativado: Lua e céu noturno
// export function useSky(date: string) {
//   return useQuery<Sky, ApiRequestError>({
//     queryKey: ['sky', date],
//     queryFn: () => getJson<Sky>('/api/sky', { date }),
//     ...PAST_DATA,
//   })
// }

export function useIndicators(date: string) {
  return useQuery<Indicator[], ApiRequestError>({
    queryKey: ['indicators', date],
    queryFn: () => getJson<Indicator[]>('/api/indicators', { date }),
    ...PAST_DATA,
  })
}

export function useExchange(date: string) {
  return useQuery<Exchange, ApiRequestError>({
    queryKey: ['exchange', date],
    queryFn: () => getJson<Exchange>('/api/exchange', { date }),
    ...PAST_DATA,
  })
}

export function useMoney(date: string) {
  return useQuery<Money, ApiRequestError>({
    queryKey: ['money', date],
    queryFn: () => getJson<Money>('/api/money', { date }),
    ...PAST_DATA,
  })
}

// Desativado: Lua e céu noturno
// export function useMoon(date: string) {
//   return useQuery<Moon, ApiRequestError>({
//     queryKey: ['moon', date],
//     queryFn: () => getJson<Moon>('/api/moon', { date }),
//     ...PAST_DATA,
//   })
// }

// Só é chamado depois que os eventos chegam.
export function useEditorial(date: string, enabled: boolean) {
  return useQuery<Editorial, ApiRequestError>({
    queryKey: ['editorial', date],
    queryFn: () => postJson<Editorial>('/api/editorial', { date }),
    enabled,
    ...PAST_DATA,
  })
}

export function useBirths(date: string) {
  return useQuery<Birth[], ApiRequestError>({
    queryKey: ['births', date],
    queryFn: () => getJson<Birth[]>('/api/births', { date }),
    ...PAST_DATA,
  })
}

export function useDeaths(date: string) {
  return useQuery<Birth[], ApiRequestError>({
    queryKey: ['deaths', date],
    queryFn: () => getJson<Birth[]>('/api/deaths', { date }),
    ...PAST_DATA,
  })
}

export function useCities() {
  return useQuery<City[], ApiRequestError>({
    queryKey: ['cities'],
    queryFn: () => getJson<City[]>('/api/cities', {}),
    ...PAST_DATA,
  })
}

export function useWeather(date: string, city: string) {
  return useQuery<Weather, ApiRequestError>({
    queryKey: ['weather', date, city],
    queryFn: () => getJson<Weather>('/api/weather', { date, city }),
    enabled: date >= '1940-01-01',
    ...PAST_DATA,
  })
}

export function useCitySearch(query: string) {
  return useQuery<City[], ApiRequestError>({
    queryKey: ['city-search', query.toLowerCase()],
    queryFn: () => getJson<City[]>('/api/cities/search', { q: query }),
    enabled: query.trim().length >= 2,
    ...PAST_DATA,
  })
}
