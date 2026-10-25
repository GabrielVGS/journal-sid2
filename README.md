# O Jornal do Dia

Digite uma data (de 1900 até ontem) e receba a capa de um jornal fictício daquele dia:
manchetes com a foto da notícia, o tempo daquele dia, o Brasil "então vs hoje", a moeda e o dólar da época,
quanto valia o dinheiro, aniversariantes e obituário do dia e um editorial escrito por IA.

Trabalho de Cliente/Servidor para Web (FURG).

## Fontes de dados

| API | Uso | Chave |
|---|---|---|
| Wikipedia (pt) | Eventos do dia, do mês e "neste dia" (feed onthisday + páginas "AAAA no Brasil" e "AAAA"); aniversariantes e obituário | não (User-Agent com contato) |
| Wikipedia (en) | Notícias do dia quando o pt não tem (páginas mensais, Portal:Current events, página do ano), traduzidas pela IA | não |
| World Bank | 7 indicadores do Brasil e câmbio anual (`PA.NUS.FCRF`) | não |
| Alpha Vantage | Câmbio mensal USD/BRL (`FX_MONTHLY`, desde dez/2014) | sim |
| Ipeadata | "Quanto valia o dinheiro": salário mínimo nominal e real (corrigido pelo INPC/ICV), mensal desde jul/1940 | não |
| Open-Meteo | Clima do dia hora a hora (temperatura, chuva, umidade, vento) desde 1940, em 15 cidades | não |
| OpenRouter (LLM) | Manchetes, editorial, tradução e escolha dos aniversariantes e do obituário (Claude Haiku 5.5) | sim |

## Arquitetura

```
React (Vite, TanStack Query)  ──/api──▶  FastAPI ──▶ services/ (1 por API) ──▶ APIs externas
  1 hook por seção                         │            cache no Postgres (TTL por fonte)
  skeleton / "sem sinal"                   ├─ domain/ ranking, editorial, front_page
                                           └─ PostgreSQL (Neon): cache, capas, cota Alpha Vantage
```

- `backend/app/schemas.py` é o contrato; `make api` gera os tipos TypeScript do front.
- A capa é montada com todas as fontes em paralelo; só a Wikipedia é essencial (503 sem ela).
  Qualquer outra falha vira placeholder ("Correspondente sem sinal").
- A IA só recebe fatos que o jornal daquele dia poderia conhecer; manchetes que citam
  eventos inexistentes são descartadas.
- Links de edição (`/c/AAAA-MM-DD`) saem com prévia própria (Open Graph): título com a data,
  manchetes já geradas (`backend/app/domain/share.py`).
- Capas completas são persistidas no Postgres (Neon) e geradas só na primeira visita a cada
  data (inclusive as edições históricas sugeridas na página inicial).

Endpoints (documentação interativa em `/docs`): `GET /api/front-page`, `/api/events`,
`/api/indicators`, `/api/exchange`, `/api/money`, `/api/births`, `/api/deaths`,
`/api/weather`, `/api/cities`,
`POST /api/editorial`, `GET /api/health`.

## Rodando localmente

Requisitos: Python 3.12 + [uv](https://docs.astral.sh/uv/), Node 22+.

```bash
cp .env.example .env      # preencha as chaves e o DATABASE_URL (Postgres/Neon)
make setup                # dependências + hook de pre-commit
make dev-back             # API em http://localhost:8000 (docs em /docs)
make dev-front            # front em http://localhost:5173 (proxy de /api)
```

Outros comandos:

```bash
make check                # ruff, mypy, tsc, oxlint, prettier (o mesmo do CI)
make fix                  # correções automáticas de lint/formatação
make api                  # regenera openapi.json e os tipos TS após mudar schemas.py
```

## Deploy (Render)

Serviço Web com runtime Docker apontando para este repositório (`render.yaml`).
O `Dockerfile` compila o front (Vite) e o FastAPI serve `/api` e o `dist/`.
Configure em *Environment*: `DATABASE_URL`, `ALPHAVANTAGE_API_KEY`, `LLM_API_KEY` e,
se quiser proteger o site, `SITE_PASSWORD`
(opcionais: `LLM_MODEL`, `LLM_FALLBACK_MODELS`, `LLM_BASE_URL`).
No plano gratuito o primeiro acesso após inatividade leva ~50 s.

**Senha única (opcional).** Defina `SITE_PASSWORD` no Render e o navegador passa a pedir
usuário e senha (qualquer usuário, essa senha) antes de abrir o site ou chamar a API.
Sem a variável, o site fica aberto. `/api/health` e as prévias de link do WhatsApp etc.
continuam funcionando (`backend/app/core/access.py`).

Trocar o provedor de IA (ex.: OpenAI) é só configuração:
`LLM_BASE_URL=https://api.openai.com/v1`, `LLM_MODEL=gpt-4o-mini`, `LLM_API_KEY=...`.
