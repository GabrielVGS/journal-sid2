import type { ApiError } from './types'

// Erro com o status HTTP e a mensagem em português vinda do servidor.
export class ApiRequestError extends Error {
  readonly status: number

  constructor(status: number, detail: string) {
    super(detail)
    this.status = status
  }
}

const FALLBACK_MESSAGE = 'Não foi possível falar com a redação. Verifique sua conexão.'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(path, init)
  } catch {
    // Status 0 indica falha de rede (servidor inacessível).
    throw new ApiRequestError(0, FALLBACK_MESSAGE)
  }
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as ApiError | null
    throw new ApiRequestError(response.status, body?.detail ?? FALLBACK_MESSAGE)
  }
  return (await response.json()) as T
}

export function getJson<T>(path: string, params: Record<string, string>): Promise<T> {
  return request<T>(`${path}?${new URLSearchParams(params)}`)
}

export function postJson<T>(path: string, body: unknown): Promise<T> {
  return request<T>(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}
