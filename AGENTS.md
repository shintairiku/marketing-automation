# Repository Guidelines

## Project Structure & Module Organization
- Monorepo anchors: `backend/` (FastAPI), `frontend/` (Next.js 15 + Bun), and `shared/supabase/` (SQL migrations, seeds). 
- Backend applies DDD/onion layering—`app/domains/*` hold core flows (e.g., `seo_article` agents), `app/common` supplies cross-cutting auth/DB helpers, `app/core` owns config and exceptions, and `app/infrastructure` exposes SerpAPI, logging, and GCP adapters. 
- FastAPI assembles domain routers through `app/api/router.py`, with execution starting in `backend/main.py`. 
- Frontend code: `frontend/src/app` (App Router), `features/` (domain bundles), `components/` (shared UI), and helpers in `lib/`, `hooks/`, `utils/`.
- Docs live in `docs/` (see `docs/backend/openai_agents_sdk_usage_specification.md`); Supabase schema history stays in `shared/supabase/migrations`.

## Build, Test, and Development Commands
- Backend: `uv sync`, then `uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000`. 
- Quality: `uv run pytest tests/` covers `backend/tests`, and `uv run python -m ruff check app` enforces lint rules. 
- Frontend: `bun install`, `bun run dev`, `bun run lint`, and `bun run build`. 
- Database: `bun run migration:up` pushes Supabase migrations; `bun run generate-types` refreshes `frontend/src/libs/supabase/types.ts`.

## Coding Style & Naming Conventions
- Python modules stay snake_case; classes and Pydantic schemas use PascalCase; prefer typed signatures and FastAPI `Depends` for cross-layer wiring. 
- Keep core business rules inside domain services, delegating IO to infrastructure adapters to preserve the onion boundary. 
- TypeScript/React components follow PascalCase filenames (`frontend/src/components/ApiConnectionStatus.tsx`), hooks use camelCase (`useX`), and Tailwind utilities rely on `prettier-plugin-tailwindcss` ordering. 
- Configuration belongs in `.env`, `backend/.env`, or `frontend/.env.local`; never inline API keys.

## Testing Guidelines
- Grow backend coverage alongside domain code in `backend/tests/` (logging, Notion sync, agent orchestration); use `test_<feature>.py` naming and tag async flows with `pytest.mark.asyncio`. 
- Before replaying long agent sessions, run utilities in `backend/testing/` to clean Supabase snapshots, and sanity-check UI changes with `bun run lint` plus manual flows in `frontend/src/features/article-generation`.

## Commit & Pull Request Guidelines
- Follow the repository’s imperative Title Case subject style (`Refactor ArticleAgentSession...`), keep subjects ≤72 chars, and expand rationale in the body when necessary. 
- Link related issues or migration IDs, attach UI evidence, and call out impacted agents (`backend/app/domains/seo_article/agents/definitions.py`) or schema objects (`shared/supabase/migrations`) with explicit validation notes.

## OpenAI Agents Integration Tips
- Agents live in `backend/app/domains/seo_article/agents/definitions.py` and register with orchestrators like `services/flow_service.py`; add new external tools under `app/infrastructure/external_apis`. 
- Reflect model or tracing toggles in `app/core/config.py` so `setup_agents_sdk()` matches `docs/backend/openai_agents_sdk_usage_specification.md`, and persist session telemetry via Supabase tables (`article_generation_flows`, `generated_articles_state`) plus `MultiAgentWorkflowLogger`.
