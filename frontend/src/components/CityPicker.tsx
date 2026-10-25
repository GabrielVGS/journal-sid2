import { type KeyboardEvent, useState } from 'react'
import { useCities, useCitySearch } from '../api/queries'
import type { City } from '../api/types'
import { useDebounced } from '../util/useDebounced'

export function cityLabel(city: City): string {
  const country = city.country && city.country !== 'Brasil' ? `, ${city.country}` : ''
  return `${city.name}${city.state ? `, ${city.state}` : ''}${country}`
}

const STATE_NAMES: Record<string, string> = {
  AM: 'Amazonas',
  BA: 'Bahia',
  CE: 'Ceará',
  DF: 'Distrito Federal',
  GO: 'Goiás',
  MG: 'Minas Gerais',
  PA: 'Pará',
  PE: 'Pernambuco',
  PR: 'Paraná',
  RJ: 'Rio de Janeiro',
  RS: 'Rio Grande do Sul',
  SC: 'Santa Catarina',
  SP: 'São Paulo',
}

function normalize(text: string): string {
  return (
    text
      .normalize('NFD')
      // Remove os acentos separados pelo NFD, para "sao" achar "São".
      .replace(/\p{Diacritic}/gu, '')
      .toLowerCase()
  )
}

// Campo de cidade: filtra as sugeridas e busca as demais na API.
export function CityPicker({ value, onChange }: { value: City; onChange: (city: City) => void }) {
  const [text, setText] = useState('')
  const [open, setOpen] = useState(false)
  const [active, setActive] = useState(0)
  const query = useDebounced(text.trim())
  const presets = useCities()
  const search = useCitySearch(query)

  const searching = query.length >= 2
  const typed = normalize(text.trim())
  const matchingPresets = (presets.data ?? []).filter((city) =>
    normalize(city.name).includes(typed),
  )
  const found = searching ? (search.data ?? []) : []
  const isPreset = (city: City) =>
    city.country === 'Brasil' &&
    matchingPresets.some(
      (preset) =>
        normalize(preset.name) === normalize(city.name) && STATE_NAMES[preset.state] === city.state,
    )
  const options = [...matchingPresets, ...found.filter((city) => !isPreset(city))]

  function choose(city: City) {
    onChange(city)
    setText('')
    setOpen(false)
  }

  function onKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === 'Escape') setOpen(false)
    if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
      event.preventDefault()
      setOpen(true)
      const delta = event.key === 'ArrowDown' ? 1 : -1
      setActive((current) => (current + delta + options.length) % Math.max(options.length, 1))
    }
    const highlighted = options[active]
    if (event.key === 'Enter' && open && highlighted) {
      event.preventDefault()
      choose(highlighted)
    }
  }

  return (
    <div className="no-print relative w-full max-w-xs text-sm">
      <label htmlFor="city" className="block text-xs tracking-wide text-ink-soft uppercase">
        Cidade <span className="normal-case">· digite para buscar qualquer uma</span>
      </label>
      <input
        id="city"
        type="search"
        autoComplete="off"
        value={text}
        placeholder={cityLabel(value)}
        onChange={(event) => {
          setText(event.target.value)
          setActive(0)
          setOpen(true)
        }}
        onFocus={() => setOpen(true)}
        onBlur={() => setTimeout(() => setOpen(false), 150)}
        onKeyDown={onKeyDown}
        role="combobox"
        aria-expanded={open}
        aria-controls="city-options"
        aria-autocomplete="list"
        aria-activedescendant={
          open && options[active] ? `city-${options[active]?.slug}` : undefined
        }
        className="w-full border border-ink bg-white/60 px-2 py-1 placeholder:text-ink"
      />
      {open && (
        <ul
          id="city-options"
          className="absolute z-20 mt-1 max-h-72 w-full overflow-y-auto border border-ink bg-paper shadow-lg"
        >
          {!searching && (
            <li className="px-2 py-1 text-xs text-ink-soft italic">
              Digite para buscar qualquer cidade
            </li>
          )}
          {searching && search.isFetching && (
            <li className="px-2 py-1 text-xs text-ink-soft italic">Buscando…</li>
          )}
          {searching && search.isError && (
            <li className="px-2 py-1 text-xs text-accent">{search.error.message}</li>
          )}
          {searching && search.isSuccess && options.length === 0 && (
            <li className="px-2 py-1 text-xs text-ink-soft italic">Nenhuma cidade encontrada.</li>
          )}
          {options.map((city, index) => (
            <li key={city.slug} id={`city-${city.slug}`}>
              <button
                type="button"
                onClick={() => choose(city)}
                onMouseEnter={() => setActive(index)}
                className={`block w-full px-2 py-1 text-left ${index === active ? 'bg-ink text-paper' : ''}`}
              >
                {cityLabel(city)}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
