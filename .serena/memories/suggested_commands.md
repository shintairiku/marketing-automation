Common commands:
- `supabase login` → authenticate CLI; `npx supabase link --project-ref <ref>` → link project; `npx supabase db push` or `bun run migration:up` → apply migrations and regenerate Supabase types.
- Frontend: `cd frontend && bun install` to install deps, `bun run dev` for local dev, `bun run build && bun run start` for prod, `bun run lint` for ESLint, `bun run generate-types` if DB schema changed.
- Backend: `cd backend && uv sync` to install, `uv run uvicorn main:app --reload --host 0.0.0.0 --port 8080` for dev server.
- Docker: `docker compose up -d frontend_dev backend` to run containers, `docker compose logs -f backend` to tail logs.
- Useful Linux commands: `ls`, `pwd`, `cat`, `rg`/`grep`, `find`, `git status`, `git diff` when working in the repo.