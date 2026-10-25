import { useEffect } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  useBirths,
  useDeaths,
  useEditorial,
  useEvents,
  useExchange,
  useIndicators,
  useMoney,
} from '../api/queries'
import { ActionBar } from '../components/ActionBar'
import { BirthsSection } from '../components/BirthsSection'
import { EditorialSection } from '../components/EditorialSection'
import { EventList } from '../components/EventList'
import { ExchangeSection } from '../components/ExchangeSection'
// Desativado: ilustração do jornal
// import { FoldedNewspaper } from '../components/FoldedNewspaper'
import { IndicatorsSection } from '../components/IndicatorsSection'
import { HeadlinePhoto } from '../components/HeadlinePhoto'
import { LeadStory, stories } from '../components/LeadStory'
import { Masthead } from '../components/Masthead'
import { MoneySection } from '../components/MoneySection'
// Desativado: Lua e céu noturno
// import { MoonSection } from '../components/MoonSection'
// import { SkySection } from '../components/SkyChart'
import { NoSignal, Section, Skeleton } from '../components/SectionState'
import { WeatherSection } from '../components/WeatherSection'
import { dateProblem, dayAndMonth, monthAndYear } from '../util/dates'

function ErrorPage({ title, message }: { title: string; message: string }) {
  return (
    <main className="mx-auto max-w-3xl px-4 py-8">
      <Masthead />
      <div className="mt-10 text-center">
        {/* Desativado: ilustração do jornal
        <FoldedNewspaper className="mx-auto mb-6 w-40 opacity-80" /> */}
        <h2 className="font-display text-3xl font-black">{title}</h2>
        <p className="mt-2">{message}</p>
        <Link
          to="/"
          className="mt-6 inline-block border border-ink px-4 py-2 hover:bg-ink hover:text-paper"
        >
          Escolher outra data
        </Link>
      </div>
    </main>
  )
}

export function FrontPage() {
  const { date = '' } = useParams()
  const problem = dateProblem(date)
  if (problem) return <ErrorPage title="Edição não encontrada" message={problem} />
  return <FrontPageContent date={date} />
}

function FrontPageContent({ date }: { date: string }) {
  const events = useEvents(date)
  // Desativado: Lua e céu noturno
  // const nightSky = useSky(date)
  // const moon = useMoon(date)
  const indicators = useIndicators(date)
  const exchange = useExchange(date)
  const births = useBirths(date)
  const deaths = useDeaths(date)
  const money = useMoney(date)
  // O editorial depende dos eventos.
  const editorial = useEditorial(date, events.isSuccess && events.data.length > 0)

  useEffect(() => {
    const previous = document.title
    document.title = `Jornal de ${dayAndMonth(date)} de ${date.slice(0, 4)} · O Jornal do Dia`
    return () => {
      document.title = previous
    }
  }, [date])

  if (events.isError) {
    return (
      <ErrorPage
        title={events.error.status === 422 ? 'Edição não encontrada' : 'Correspondente sem sinal'}
        message={events.error.message}
      />
    )
  }

  const all = events.data ?? []
  const headlineIds = new Set(
    editorial.data?.headlines.map((h) => h.event_id) ?? all.slice(0, 3).map((e) => e.id),
  )
  // Separa os eventos por camada, sem repetir os que já são manchete.
  const alsoToday = all.filter((e) => e.layer === 'day' && !headlineIds.has(e.id))
  const thisMonth = all.filter((e) => e.layer === 'month' && !headlineIds.has(e.id))
  const onThisDay = all.filter((e) => e.layer === 'on_this_day' && !headlineIds.has(e.id))
  const year = Number(date.slice(0, 4))
  const history = onThisDay
    .filter((e) => (e.year ?? 0) < year)
    .toSorted((a, b) => (b.year ?? 0) - (a.year ?? 0))
  const future = onThisDay
    .filter((e) => (e.year ?? 0) > year)
    .toSorted((a, b) => (a.year ?? 0) - (b.year ?? 0))
  const leadStories = events.isPending ? null : all.length > 0 ? stories(all, editorial) : []
  const headlinePhoto = leadStories?.find((story) => story.event.image_url)
  const hasLeftColumn = events.isPending || alsoToday.length > 0 || thisMonth.length > 0
  // Sem foto, a manchete ocupa a largura toda.
  const hasSideColumn = leadStories === null || Boolean(headlinePhoto)

  return (
    <main className="mx-auto max-w-6xl px-4 py-6">
      <ActionBar date={date} />
      <Masthead date={date} />

      <div className="mt-6 grid gap-6 lg:grid-cols-12 print:grid-cols-12">
        <div
          className={
            hasSideColumn ? 'lg:col-span-8 print:col-span-8' : 'lg:col-span-12 print:col-span-12'
          }
        >
          {events.isPending ? (
            <Skeleton lines={6} className="[&>div:first-child]:h-12" />
          ) : all.length === 0 ? (
            <NoSignal message="Nenhum acontecimento registrado para esta data." />
          ) : (
            <LeadStory events={all} editorial={editorial} date={date} />
          )}
        </div>
        {hasSideColumn && (
          <div className="space-y-6 lg:col-span-4 print:col-span-4">
            {leadStories === null ? (
              <Skeleton lines={8} />
            ) : (
              headlinePhoto && (
                <section>
                  <h2 className="section-title">Foto da manchete</h2>
                  <HeadlinePhoto event={headlinePhoto.event} title={headlinePhoto.headline.title} />
                </section>
              )
            )}
            {/* Desativado: Lua e céu noturno
          <Section query={nightSky} title="O céu daquela noite" skeletonLines={8}>
            {(data) => <SkySection sky={data} moon={moon.data} />}
          </Section>
          <Section query={moon} title="A Lua naquela noite" skeletonLines={3}>
            {(data) => <MoonSection moon={data} />}
          </Section> */}
          </div>
        )}
      </div>

      <div className="mt-8 grid gap-6 border-t-4 border-double border-ink pt-6 md:grid-cols-2 lg:grid-cols-12 print:grid-cols-12">
        {hasLeftColumn && (
          <div className="space-y-6 lg:col-span-4 print:col-span-4">
            {alsoToday.length > 0 && (
              <section>
                <h2 className="section-title">Também neste dia</h2>
                <EventList events={alsoToday} show="date" />
              </section>
            )}
            {thisMonth.length > 0 && (
              <section>
                <h2 className="section-title">Em {monthAndYear(date)}</h2>
                <EventList events={thisMonth} show="date" />
              </section>
            )}
            {events.isPending && <Skeleton lines={6} />}
          </div>
        )}
        <div
          className={`space-y-6 ${
            hasLeftColumn
              ? 'lg:col-span-5 print:col-span-5'
              : 'lg:col-span-9 lg:grid lg:grid-cols-2 lg:items-start lg:gap-6 lg:space-y-0 print:col-span-9 print:grid print:grid-cols-2 print:items-start print:gap-6 print:space-y-0'
          }`}
        >
          {events.isPending && <Skeleton lines={8} />}
          {history.length > 0 && (
            <section>
              <h2 className="section-title">Neste dia, na história</h2>
              <EventList events={history} show="year" limit={5} />
            </section>
          )}
          {future.length > 0 && (
            <section className="border border-ink p-3">
              <h2 className="section-title">O que o futuro reserva</h2>
              <p className="mb-2 text-xs text-ink-soft italic">
                Coisas que ainda vão acontecer num {dayAndMonth(date)}, segundo nossos videntes.
              </p>
              <EventList events={future} show="year" limit={4} />
            </section>
          )}
        </div>
        <div className="space-y-6 md:col-span-2 lg:col-span-3 print:col-span-3">
          <Section query={exchange} title="Câmbio e moeda" skeletonLines={5}>
            {(data) => <ExchangeSection exchange={data} />}
          </Section>
          <Section query={money} title="Quanto valia o dinheiro" skeletonLines={6}>
            {(data) => <MoneySection money={data} />}
          </Section>
        </div>
      </div>

      <section className="mt-8 border-t-4 border-double border-ink pt-6">
        <h2 className="section-title">O tempo naquele dia</h2>
        <WeatherSection date={date} />
      </section>

      <div className="mt-8 border-t-4 border-double border-ink pt-6">
        <Section
          query={births}
          title={`Fazem aniversário em ${dayAndMonth(date)}`}
          isEmpty={(data) => data.length === 0}
          skeletonLines={3}
        >
          {(data) => <BirthsSection births={data} />}
        </Section>
        <Section
          query={deaths}
          title={`Despediram-se em ${dayAndMonth(date)}`}
          isEmpty={(data) => data.length === 0}
          className="mt-6"
          skeletonLines={3}
        >
          {(data) => <BirthsSection births={data} obituary />}
        </Section>
      </div>

      <div className="mt-8 border-t-4 border-double border-ink pt-6">
        <Section query={indicators} title="O Brasil de então e de hoje" skeletonLines={4}>
          {(data) =>
            data.length > 0 ? (
              <IndicatorsSection indicators={data} />
            ) : (
              <p className="text-sm text-ink-soft italic">
                Os indicadores do Banco Mundial começam em 1960.
              </p>
            )
          }
        </Section>
      </div>

      <div className="mt-8 border-t-4 border-double border-ink pt-6">
        <h2 className="section-title">Editorial</h2>
        {editorial.isError ? (
          <NoSignal message={editorial.error.message} />
        ) : editorial.isSuccess ? (
          <EditorialSection editorial={editorial.data} />
        ) : (
          <div>
            <Skeleton lines={6} />
            <p className="mt-2 text-sm text-ink-soft italic">O editorialista está escrevendo…</p>
          </div>
        )}
      </div>

      <footer className="mt-10 border-t border-ink pt-2 text-center text-xs text-ink-soft">
        Fontes: Wikipedia · Banco Mundial · Alpha Vantage · Ipeadata · Open-Meteo
      </footer>
    </main>
  )
}
