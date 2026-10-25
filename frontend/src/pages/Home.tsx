import { type FormEvent, useState } from 'react'
import { useNavigate } from 'react-router-dom'
// Desativado: ilustração do jornal
// import { FoldedNewspaper } from '../components/FoldedNewspaper'
import { Masthead } from '../components/Masthead'
import { MIN_DATE, dateProblem, randomDate, yesterdayIso } from '../util/dates'

// Datas sugeridas na página inicial.
const SUGGESTIONS = [
  { date: '1969-07-20', label: 'Homem na Lua' },
  { date: '1994-07-01', label: 'Plano Real' },
  { date: '1950-07-16', label: 'Maracanazo' },
  { date: '1985-01-15', label: 'Tancredo eleito' },
  { date: '2002-06-30', label: 'Pentacampeão' },
  { date: '2014-07-08', label: 'O 7 a 1' },
  { date: '1900-01-01', label: 'Primeira edição' },
]

export function Home() {
  const navigate = useNavigate()
  const [date, setDate] = useState('')
  const [problem, setProblem] = useState<string | null>(null)

  function submit(event: FormEvent) {
    event.preventDefault()
    const issue = dateProblem(date)
    setProblem(issue)
    if (!issue) navigate(`/c/${date}`)
  }

  return (
    <main className="mx-auto max-w-3xl px-4 py-8">
      <Masthead />
      {/* Desativado: ilustração do jornal
      <FoldedNewspaper className="mx-auto mt-8 w-48 sm:w-60" /> */}
      <form onSubmit={submit} noValidate className="mx-auto mt-10 max-w-md text-center">
        <label htmlFor="date" className="font-display text-2xl font-bold">
          Que dia você quer ler?
        </label>
        <p className="mt-1 text-sm text-ink-soft">
          Seu aniversário, um jogo histórico, uma data marcante: escolha qualquer dia desde 1900 e
          receba a capa do jornal.
        </p>
        <div className="mt-4 flex flex-col gap-2 sm:flex-row">
          <input
            id="date"
            type="date"
            min={MIN_DATE}
            max={yesterdayIso()}
            value={date}
            onChange={(event) => setDate(event.target.value)}
            aria-invalid={problem !== null}
            aria-describedby={problem ? 'date-problem' : undefined}
            className="flex-1 border-2 border-ink bg-white/60 px-3 py-2 text-lg"
          />
          <button
            type="submit"
            className="bg-ink px-5 py-2 font-display text-lg font-bold text-paper hover:bg-accent"
          >
            Ver a capa
          </button>
        </div>
        {problem && (
          <p id="date-problem" role="alert" className="mt-2 text-sm text-accent">
            {problem}
          </p>
        )}
      </form>
      <p className="mx-auto mt-4 max-w-md text-center text-sm text-ink-soft">
        Manchetes da época · foto da manchete · o tempo hora a hora · moeda e dólar · o Brasil de
        então e de hoje · aniversariantes famosos · editorial
      </p>
      <div className="mt-4 text-center">
        <button
          type="button"
          onClick={() => navigate(`/c/${randomDate()}`)}
          className="text-sm text-accent underline-offset-4 hover:underline"
        >
          Não sabe por onde começar? Surpreenda-me com uma data qualquer →
        </button>
      </div>
      <section className="mt-10 text-center">
        <h2 className="section-title inline-block">Edições históricas</h2>
        <div className="mt-3 flex flex-wrap justify-center gap-2">
          {SUGGESTIONS.map((suggestion) => (
            <button
              key={suggestion.date}
              type="button"
              onClick={() => navigate(`/c/${suggestion.date}`)}
              className="border border-ink px-3 py-1 text-sm hover:bg-ink hover:text-paper"
            >
              {suggestion.label}{' '}
              <span className="text-ink-soft">
                ({suggestion.date.split('-').toReversed().join('/')})
              </span>
            </button>
          ))}
        </div>
      </section>
    </main>
  )
}
