"""Health check endpoints."""

from fastapi import APIRouter

from app.core.config import (
    MODELS, DEFAULT_MODEL, BILLING_ENABLED, RESEND_API_KEY,
)

router = APIRouter()


@router.get("/")
async def root():
    return {
        "status": "online",
        "message": "Datachat API v2.0",
        "version": "2.0.0",
    }


@router.get("/health")
async def health():
    return {"status": "healthy"}


@router.get("/api/models")
async def list_models():
    """Return available models with display names and the default."""
    return {
        "models": [
            {"id": model_id, "display_name": info["display_name"]}
            for model_id, info in MODELS.items()
        ],
        "default": DEFAULT_MODEL,
    }


@router.get("/api/config")
async def runtime_config():
    """Public runtime feature flags. Self-hosters who haven't set up Stripe
    or Resend will see those features disabled in the UI."""
    return {
        "billing_enabled": BILLING_ENABLED,
        "email_enabled": bool(RESEND_API_KEY),
    }
