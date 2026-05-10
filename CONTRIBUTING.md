# Contributing to Datachat

Thanks for your interest. Datachat is open source under Apache 2.0.

## Ways to contribute

- **Bugs / issues** — open a GitHub issue with reproduction steps and your environment.
- **Pull requests** — see "Pull request flow" below.
- **New warehouse executors** — Datachat is designed to be extended (Postgres, BigQuery, Snowflake, Redshift, MotherDuck, DuckDB-local are built-in). See [`README.md`](README.md#adding-a-new-warehouse-type) for the executor contract.
- **MCP server integrations** — connect a new tool server to the Claude tool-use loop. Salesforce is the reference implementation; see `backend/app/services/mcp_client.py`.
- **Docs** — README clarifications, deployment recipes, troubleshooting.

## Local development

See the [README](README.md#quickstart) for a 5-minute local-dev setup.

```bash
# Backend
cd backend
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8000

# Frontend (in a second terminal)
cd frontend
npm install
npm run dev
```

## Pull request flow

1. Fork the repo and create a feature branch off `main`.
2. **Tests required.** Backend changes must come with passing `uv run pytest` (from `backend/`). Frontend changes must build cleanly with `npm run build`.
3. **No new secrets.** Don't commit API keys, real database URLs, or production credentials. `backend/.env.example` and `frontend/.env.example` are the source of truth for required environment variables.
4. **Migrations.** Database schema changes go through Alembic with hand-written migrations under `backend/alembic/versions/`. Use the next sequential ID (`001`, `002`, ...) and follow the idempotent patterns in `001_initial_schema.py` and `015_add_organizations.py`.
5. **Conventional commits encouraged but not required.** `feat:`, `fix:`, `chore:`, etc.
6. Open a PR with a short summary and a "Test plan" checklist of what you verified.

## Style

- Backend: standard Python, type hints where they clarify, prefer simple functions over classes.
- Frontend: TypeScript strict mode; React Query for server state; Tailwind classes inline; shadcn/ui primitives for components.
- Don't add comments that describe *what* well-named code already says — explain *why* only when non-obvious.

## Security disclosures

Report security vulnerabilities privately. See [SECURITY.md](SECURITY.md).

## Licensing

By submitting a contribution, you agree that your contribution is licensed under the Apache License 2.0 (see [LICENSE](LICENSE)). No CLA is required.
