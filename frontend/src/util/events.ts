import type { Event } from '../api/types'

export function isTranslated(event: Event): boolean {
  return event.url?.includes('en.wikipedia.org') ?? false
}
