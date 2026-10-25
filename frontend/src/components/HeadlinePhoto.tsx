import { useState } from 'react'
import type { Event } from '../api/types'
import { isTranslated } from '../util/events'

const SHARPER = 500

function sharper(url: string): string {
  return url.replace(/\/(\d+)px-/, (match, width: string) =>
    Number(width) < SHARPER ? `/${SHARPER}px-` : match,
  )
}

export function HeadlinePhoto({ event, title }: { event: Event; title: string }) {
  const original = event.image_url ?? ''
  const [src, setSrc] = useState(() => sharper(original))
  return (
    <figure>
      <img
        src={src}
        alt=""
        onError={() => src !== original && setSrc(original)}
        className="newspaper-photo aspect-[4/3] w-full border border-ink bg-paper-dark object-cover"
      />
      <figcaption className="mt-2 text-sm">
        <span className="font-bold">{title}</span>
        <p className="mt-1 text-xs text-ink-soft italic">
          Imagem ilustrativa · Wikipédia
          {event.url && (
            <>
              {' · '}
              <a href={event.url} target="_blank" rel="noreferrer" className="no-print underline">
                {isTranslated(event) ? 'ver o artigo (em inglês)' : 'ver o artigo'}
              </a>
            </>
          )}
        </p>
      </figcaption>
    </figure>
  )
}
