import type { Editorial } from '../api/types'

export function EditorialSection({ editorial }: { editorial: Editorial }) {
  const paragraphs = editorial.body.split(/\n\s*\n/).filter(Boolean)
  return (
    <article>
      <h3 className="mb-3 font-display text-2xl font-black italic sm:text-3xl">
        {editorial.title}
      </h3>
      <div className="gap-8 leading-relaxed md:columns-2 [&>p+p]:mt-3">
        {paragraphs.map((paragraph, index) => (
          <p key={paragraph} className={index === 0 ? 'drop-cap' : ''}>
            {paragraph}
          </p>
        ))}
      </div>
      <p className="mt-3 text-xs text-ink-soft italic">
        {editorial.ai_generated
          ? `Texto gerado por inteligência artificial (${editorial.model}) a partir dos fatos desta página.`
          : 'Editorial indisponível; manchetes extraídas diretamente da Wikipedia.'}
      </p>
    </article>
  )
}
