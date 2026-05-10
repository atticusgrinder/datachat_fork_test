"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import ALLOWED_ORIGINS
from app.api import health, warehouses, conversations, feedback, usage, admin, account, demo, visualizations, salesforce, files, changelog, context, integrations, local_duckdb, reports, organization
from app.services import scheduler_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler_service.start_scheduler()
    try:
        yield
    finally:
        await scheduler_service.stop_scheduler()


app = FastAPI(title="Datachat API", version="2.0.0", lifespan=lifespan)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS if ALLOWED_ORIGINS != ["*"] else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router)
app.include_router(warehouses.router)
app.include_router(conversations.router)
app.include_router(feedback.router)
app.include_router(usage.router)
app.include_router(admin.router)
app.include_router(account.router)
app.include_router(demo.router)
app.include_router(visualizations.router)
app.include_router(salesforce.router)
app.include_router(files.router)
app.include_router(changelog.router)
app.include_router(context.router)
app.include_router(integrations.router)
app.include_router(local_duckdb.router)
app.include_router(reports.router)
app.include_router(organization.router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
