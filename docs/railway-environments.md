# Railway Environment Setup

Datachat uses [Railway](https://railway.app) with two environments: **production** and **development**.

## Architecture

```
Railway Project: datachat
├── production (environment)
│   ├── backend (service)   → railway.json in backend/
│   ├── frontend (service)  → railway.json in frontend/
│   └── postgres (plugin)
└── development (environment)
    ├── backend (service)   → railway.json in backend/
    ├── frontend (service)  → railway.json in frontend/
    └── postgres (plugin)
```

Both environments share the same codebase and `railway.json` configs. Environment-specific behavior is controlled entirely through environment variables.

## Config as Code

Each service has a `railway.json` that defines build and deploy settings:

- **backend/railway.json** — Railpack builder, `uv run uvicorn` start command, `/health` healthcheck, `ON_FAILURE` restart
- **frontend/railway.json** — Railpack builder, `npx serve` for the built SPA, `ON_FAILURE` restart

These configs override Railway dashboard settings per deployment. The dashboard settings are not modified by the config files.

Watch patterns ensure only relevant changes trigger deploys:
- Backend deploys only on `backend/**` changes
- Frontend deploys only on `frontend/**` changes

## Environment Variables

### Backend

| Variable | Description | Differs per env? |
|----------|-------------|:---:|
| `DATABASE_URL` | PostgreSQL connection string | ✅ |
| `ANTHROPIC_API_KEY` | Claude API key | ❌ (shared) |
| `CLERK_SECRET_KEY` | Clerk JWT validation | ✅ |
| `ENCRYPTION_KEY` | Fernet key for warehouse credentials | ✅ |
| `ALLOWED_ORIGINS` | CORS origins (frontend URL) | ✅ |
| `DISABLE_AUTH` | Bypass auth (dev only) | ✅ |

### Frontend

| Variable | Description | Differs per env? |
|----------|-------------|:---:|
| `VITE_API_URL` | Backend URL | ✅ |
| `VITE_CLERK_PUBLISHABLE_KEY` | Clerk public key | ✅ |

### Future (Stripe)

| Variable | Description |
|----------|-------------|
| `STRIPE_SECRET_KEY` | Stripe API key (test key for dev, live for prod) |
| `STRIPE_WEBHOOK_SECRET` | Stripe webhook signing secret |
| `STRIPE_PRICE_ID_STARTER` | Price ID for Starter plan |
| `STRIPE_PRICE_ID_PRO` | Price ID for Pro plan |

## Setup Instructions

### 1. Create environments in Railway

1. Open your Railway project
2. Go to **Settings → Environments**
3. Create two environments: `production` and `development`
4. Railway will duplicate all services into both environments

### 2. Configure environment variables

Set the variables listed above in each environment. Use Railway's **Shared Variables** for values that don't change between environments (e.g., `ANTHROPIC_API_KEY`).

### 3. Set up databases

Each environment gets its own Railway Postgres plugin. The `DATABASE_URL` is auto-injected by Railway when you add the plugin.

### 4. Configure deployment triggers

- **production** — deploys from `main` branch
- **development** — deploys from `develop` branch (or use PR deploys)

### 5. Custom domains

- **production** — `app.datachat.dev` (or your domain)
- **development** — use Railway's generated `*.up.railway.app` domain

## Branch Strategy

| Branch | Environment | Purpose |
|--------|------------|---------|
| `main` | production | Stable releases |
| `develop` | development | Integration testing |
| Feature branches | PR deploys (optional) | Per-PR preview environments |
