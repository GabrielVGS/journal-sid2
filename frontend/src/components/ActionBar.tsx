import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { MIN_DATE, shiftDay, yesterdayIso } from '../util/dates'
import { Icon } from './Icon'

const BUTTON =
  'inline-flex min-h-10 min-w-10 items-center justify-center gap-1.5 border border-ink px-2 text-sm whitespace-nowrap transition hover:bg-ink hover:text-paper sm:min-h-0 sm:px-3 sm:py-1'

// Barra com dia anterior, dia seguinte, compartilhar e imprimir.
export function ActionBar({ date }: { date: string }) {
  const [toast, setToast] = useState<string | null>(null)
  const previous = shiftDay(date, -1)
  const next = shiftDay(date, 1)

  useEffect(() => {
    if (!toast) return
    const timer = setTimeout(() => setToast(null), 2500)
    return () => clearTimeout(timer)
  }, [toast])

  async function share() {
    const url = window.location.href
    if (navigator.share) {
      try {
        await navigator.share({ title: document.title, url })
        return
      } catch {
        // usuário cancelou: copia o link
      }
    }
    try {
      await navigator.clipboard.writeText(url)
      setToast('Link copiado!')
    } catch {
      setToast('Não foi possível copiar. Copie o endereço da barra do navegador.')
    }
  }

  return (
    <nav className="no-print mb-4 flex items-center justify-between gap-2" aria-label="Edição">
      <div className="flex gap-1 sm:gap-2">
        <Link to="/" className={BUTTON} aria-label="Escolher outra data">
          <Icon name="calendar" />
          <span className="hidden sm:inline">Outra data</span>
        </Link>
        {previous >= MIN_DATE && (
          <Link to={`/c/${previous}`} className={BUTTON} aria-label="Edição do dia anterior">
            <Icon name="back" />
            <span className="hidden sm:inline">Dia anterior</span>
          </Link>
        )}
        {next <= yesterdayIso() && (
          <Link to={`/c/${next}`} className={BUTTON} aria-label="Edição do dia seguinte">
            <span className="hidden sm:inline">Dia seguinte</span>
            <Icon name="forward" />
          </Link>
        )}
      </div>
      <div className="flex gap-1 sm:gap-2">
        <button type="button" onClick={() => window.print()} className={BUTTON}>
          <Icon name="print" />
          <span className="sm:hidden">PDF</span>
          <span className="hidden sm:inline">Imprimir / PDF</span>
        </button>
        <button type="button" onClick={share} className={BUTTON} aria-label="Compartilhar">
          <Icon name="share" />
          <span className="hidden sm:inline">Compartilhar</span>
        </button>
      </div>
      {toast && (
        <output className="fixed bottom-4 left-1/2 z-10 -translate-x-1/2 bg-ink px-4 py-2 text-sm text-paper shadow-lg">
          {toast}
        </output>
      )}
    </nav>
  )
}
