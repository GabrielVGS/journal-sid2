.PHONY: setup dev-back dev-front api fix check entrega

setup:
	cd backend && uv sync
	cd frontend && npm ci
	git config core.hooksPath .githooks

dev-back:
	cd backend && uv run uvicorn app.main:app --reload

dev-front:
	cd frontend && npm run dev -- --host 0.0.0.0

api:
	cd backend && uv run python -m app.scripts.export_openapi
	cd frontend && npm run gen:api

fix:
	cd backend && uv run ruff check --fix . && uv run ruff format .
	cd frontend && npx oxlint --fix && npm run format

check:
	cd backend && uv run ruff check . && uv run ruff format --check . && uv run mypy
	cd frontend && npm run check

GRUPO ?= NomeGrupo
entrega:
	rm -rf build/entrega && mkdir -p build/entrega
	git archive --format=tar --prefix=codigo/ HEAD | tar -x -C build/entrega
	@if [ -f relatorio.pdf ]; then cp relatorio.pdf build/entrega/; else echo "AVISO: relatorio.pdf ausente"; fi
	@if grep -rqE 'sk-or-v1-[0-9a-f]{20,}' build/entrega; then echo "ERRO: chave no pacote!"; exit 1; fi
	cd build/entrega && zip -qr ../$(GRUPO)_JornalDoDia.zip .
	@echo "build/$(GRUPO)_JornalDoDia.zip"
