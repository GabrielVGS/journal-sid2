import { useState } from 'react'
import type { Event } from '../api/types'
import { dayAndMonth } from '../util/dates'
import { isTranslated } from '../util/events'

export function EventList({
  events,
  show,
  limit = Infinity,
}: {
  events: Event[]
  show: 'date' | 'year'
  limit?: number
}) {
  const [expanded, setExpanded] = useState(false)
  const visible = expanded ? events : events.slice(0, limit)
  const hidden = events.length - visible.length
  return (
    <>
      <ul className="space-y-3 text-sm leading-relaxed">
        {visible.map((event) => (
          <li key={event.id} className="border-b border-paper-dark pb-2 last:border-0">
            <span className="font-bold">
              {show === 'year' ? event.year : event.date ? dayAndMonth(event.date) : 'Neste mês'}
              {' — '}
            </span>
            {event.url ? (
              <a href={event.url} target="_blank" rel="noreferrer" className="hover:underline">
                {event.text}
              </a>
            ) : (
              event.text
            )}
            {isTranslated(event) && (
              <span className="ml-1 text-xs text-ink-soft italic">(traduzido do inglês)</span>
            )}
            {event.mentions_brazil && (
              <span className="ml-1 text-xs text-accent" title="Fato ligado ao Brasil">
                ★
              </span>
            )}
          </li>
        ))}
      </ul>
      {(hidden > 0 || expanded) && events.length > limit && (
        <button
          type="button"
          onClick={() => setExpanded(!expanded)}
          className="no-print mt-2 text-sm text-accent underline-offset-4 hover:underline"
        >
          {expanded ? 'Mostrar menos' : `Mostrar mais ${hidden} ${hidden === 1 ? 'fato' : 'fatos'}`}
        </button>
      )}
    </>
  )
}
