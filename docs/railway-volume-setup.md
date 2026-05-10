# Railway Volume Setup for Local DuckDB Persistence

The persistent local DuckDB feature stores one `.duckdb` file per user on disk. In production this directory **must** be backed by a [Railway persistent volume](https://docs.railway.com/reference/volumes) — otherwise Railway's ephemeral container filesystem wipes uploads on every redeploy.

## What needs to exist

For each environment that should support local file uploads (typically both `production` and `development`):

1. A volume attached to the **backend** service.
2. A `LOCAL_DUCKDB_DIR` environment variable on the backend service that points inside the volume's mount path.

## Setup steps (per environment)

1. Open the Railway dashboard → select the environment (e.g. `development`).
2. Open the **backend** service → **Volumes** tab → **Create Volume**.
3. Suggested settings:
   - **Mount path**: `/data`
   - **Size**: 5 GB to start (resizable later; pricing is roughly $0.25/GB/month)
4. On the same backend service, **Variables** tab, add:
   ```
   LOCAL_DUCKDB_DIR=/data/local_duckdb
   ```
5. Redeploy the backend service.

The first user upload will create `/data/local_duckdb/` automatically (the backend calls `os.makedirs(..., exist_ok=True)`).

## Local development

No volume needed. The default `LOCAL_DUCKDB_DIR=./local_duckdb` writes into the backend project directory. Add `local_duckdb/` to `.gitignore` if you don't want test files committed.

## Operational notes

- **One backend instance only**: a Railway volume is bound to a single service replica. Datachat already runs a single backend instance, so this isn't a constraint today, but be aware that horizontal scaling needs another approach (object storage, MotherDuck, etc.) before adding more backend replicas.
- **Backups**: Railway volumes don't snapshot automatically. If user-uploaded data is important, set up periodic copies to S3 or similar.
- **Account deletion**: the existing `DELETE /api/account` endpoint also deletes the user's `.duckdb` file. The user-facing "Remove all local files" button in Settings calls `DELETE /api/local-duckdb` which removes the file but keeps the account.
- **Disk usage**: there is currently no per-user storage cap. Add one in `local_duckdb_service.py` if usage grows.
