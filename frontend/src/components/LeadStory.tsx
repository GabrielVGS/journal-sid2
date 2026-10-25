import type { UseQueryResult } from '@tanstack/react-query'
import type { ApiRequestError } from '../api/client'
import type { Editorial, Event, Headline } from '../api/types'
import { isTranslated } from '../util/events'
import { Skeleton } from './SectionState'

export interface Story {
  headline: Headline
  event: Event
}

// Junta cada manchete do editorial ao evento que ela cita.
// Sem editorial, usa os três primeiros eventos.
export function stories(
  events: Event[],
  editorial: UseQueryResult<Editorial, ApiRequestError>,
): Story[] | null {
  const byId = new Map(events.map((event) => [event.id, event]))
  if (editorial.isSuccess) {
    return editorial.data.headlines.flatMap((headline) => {
      const event = byId.get(headline.event_id)
      return event ? [{ headline, event }] : []
    })
  }
  if (editorial.isError) {
    return events
      .slice(0, 3)
      .map((event) => ({ headline: { title: event.text, event_id: event.id }, event }))
  }
  return null
}

function MemoryKicker({ event, date }: { event: Event; date: string }) {
  if (event.layer !== 'on_this_day' || !event.year) return null
  const years = Number(date.slice(0, 4)) - event.year
  return (
    <p className="mb-1 text-xs font-bold tracking-widest text-accent uppercase">
      Memória · há {years} {years === 1 ? 'ano' : 'anos'} ({event.year})
    </p>
  )
}

function ReadMore({ event }: { event: Event }) {
  if (!event.url) return null
  return (
    <a
      href={event.url}
      target="_blank"
      rel="noreferrer"
      className="no-print text-sm text-accent underline-offset-2 hover:underline"
    >
      {isTranslated(event) ? 'Leia mais na Wikipedia (em inglês) →' : 'Leia mais na Wikipedia →'}
    </a>
  )
}

export function LeadStory({
  events,
  editorial,
  date,
}: {
  events: Event[]
  editorial: UseQueryResult<Editorial, ApiRequestError>
  date: string
}) {
  const items = stories(events, editorial)
  if (items === null) {
    return (
      <div>
        <Skeleton lines={2} className="mb-4 [&>div]:h-10" />
        <p className="text-sm text-ink-soft italic">A redação está fechando as manchetes…</p>
      </div>
    )
  }
  const [main, ...secondary] = items
  if (!main) return null
  return (
    <div>
      <article className="border-b border-ink pb-4">
        <MemoryKicker event={main.event} date={date} />
        <h2 className="font-display text-3xl leading-tight font-black sm:text-5xl">
          {main.headline.title}
        </h2>
        {main.headline.subtitle && (
          <p className="mt-2 font-display text-lg italic sm:text-xl">{main.headline.subtitle}</p>
        )}
        {main.headline.title !== main.event.text && (
          <p className="mt-3 leading-relaxed">{main.event.text}</p>
        )}
        <ReadMore event={main.event} />
      </article>
      {secondary.length > 0 && (
        <div className="grid gap-4 pt-4 sm:grid-cols-2 sm:divide-x sm:divide-ink print:grid-cols-2">
          {secondary.map(({ headline, event }) => (
            <article key={event.id} className="sm:pl-4 sm:first:pl-0">
              <MemoryKicker event={event} date={date} />
              <h3 className="font-display text-xl leading-snug font-bold">{headline.title}</h3>
              {headline.subtitle && <p className="mt-1 text-sm italic">{headline.subtitle}</p>}
              <ReadMore event={event} />
            </article>
          ))}
        </div>
      )}
    </div>
  )
}
