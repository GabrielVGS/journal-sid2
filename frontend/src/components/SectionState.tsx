import type { UseQueryResult } from '@tanstack/react-query'
import type { ApiRequestError } from '../api/client'
import type { ReactNode } from 'react'

// Esboço exibido enquanto a seção carrega.
export function Skeleton({ lines = 3, className = '' }: { lines?: number; className?: string }) {
  return (
    <div
      className={`animate-pulse space-y-2 ${className}`}
      aria-busy="true"
      aria-label="Carregando"
    >
      {Array.from({ length: lines }, (_, index) => (
        <div
          key={index}
          className="h-3 rounded bg-paper-dark"
          style={{ width: `${100 - ((index * 17) % 40)}%` }}
        />
      ))}
    </div>
  )
}

// Aviso exibido quando a fonte da seção falhou.
export function NoSignal({ message }: { message?: string }) {
  return (
    <div className="border border-dashed border-ink-soft p-4 text-center text-ink-soft italic">
      <p className="font-display text-lg font-bold not-italic">Correspondente sem sinal</p>
      <p className="text-sm">{message ?? 'Esta seção não chegou a tempo para a edição.'}</p>
    </div>
  )
}

interface SectionProps<T> {
  query: UseQueryResult<T, ApiRequestError>
  title?: string
  skeletonLines?: number
  isEmpty?: (data: T) => boolean
  className?: string
  children: (data: T) => ReactNode
}

// Envolve uma seção: carregando, erro, vazio ou conteúdo.
export function Section<T>({
  query,
  title,
  skeletonLines = 4,
  isEmpty,
  className = '',
  children,
}: SectionProps<T>) {
  if (query.isSuccess && isEmpty?.(query.data)) return null
  return (
    <section className={className}>
      {title && <h2 className="section-title">{title}</h2>}
      {query.isPending && <Skeleton lines={skeletonLines} />}
      {query.isError && <NoSignal message={query.error.message} />}
      {query.isSuccess && children(query.data)}
    </section>
  )
}
