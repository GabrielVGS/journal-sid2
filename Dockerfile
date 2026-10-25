# Estágio 1: build do frontend (Vite)
FROM node:22-slim AS front
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Estágio 2: FastAPI servindo a API e o dist/
FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
WORKDIR /app/backend
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev
COPY backend/ ./
COPY --from=front /app/frontend/dist /app/frontend/dist
ENV PORT=8000
# --proxy-headers: o Render fica atrás de proxy (IP real para o rate limit).
CMD uv run --no-sync uvicorn app.main:app --host 0.0.0.0 --port $PORT --proxy-headers --forwarded-allow-ips="*"
