"""Salesforce OAuth and MCP client service."""

import logging
from datetime import datetime, timedelta
from typing import Optional
from urllib.parse import urlencode

import httpx

from app.core.config import (
    SALESFORCE_CLIENT_ID,
    SALESFORCE_CLIENT_SECRET,
    BACKEND_URL,
)
from app.core.security import encrypt_credentials, decrypt_credentials
from app.models.salesforce import SalesforceConnection

logger = logging.getLogger(__name__)

SALESFORCE_AUTH_URL = "https://login.salesforce.com/services/oauth2/authorize"
SALESFORCE_TOKEN_URL = "https://login.salesforce.com/services/oauth2/token"
SALESFORCE_USERINFO_URL = "/services/oauth2/userinfo"
SALESFORCE_REVOKE_URL = "https://login.salesforce.com/services/oauth2/revoke"

OAUTH_REDIRECT_PATH = "/api/salesforce/callback"
OAUTH_SCOPES = "api refresh_token"


def get_oauth_redirect_uri() -> str:
    """Build the OAuth redirect URI pointing to the backend callback."""
    return f"{BACKEND_URL.rstrip('/')}{OAUTH_REDIRECT_PATH}"


def get_oauth_authorize_url(state: str) -> str:
    """Build the Salesforce OAuth authorization URL."""
    params = {
        "response_type": "code",
        "client_id": SALESFORCE_CLIENT_ID,
        "redirect_uri": get_oauth_redirect_uri(),
        "scope": OAUTH_SCOPES,
        "state": state,
    }
    return f"{SALESFORCE_AUTH_URL}?{urlencode(params)}"


async def exchange_code_for_tokens(code: str) -> dict:
    """Exchange an authorization code for access and refresh tokens."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            SALESFORCE_TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "client_id": SALESFORCE_CLIENT_ID,
                "client_secret": SALESFORCE_CLIENT_SECRET,
                "redirect_uri": get_oauth_redirect_uri(),
            },
        )
        response.raise_for_status()
        return response.json()


async def refresh_access_token(refresh_token: str) -> dict:
    """Use a refresh token to get a new access token."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            SALESFORCE_TOKEN_URL,
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": SALESFORCE_CLIENT_ID,
                "client_secret": SALESFORCE_CLIENT_SECRET,
            },
        )
        response.raise_for_status()
        return response.json()


async def get_user_info(instance_url: str, access_token: str) -> dict:
    """Fetch user info from the connected Salesforce org."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{instance_url}{SALESFORCE_USERINFO_URL}",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        response.raise_for_status()
        return response.json()


async def get_valid_access_token(connection: SalesforceConnection, db) -> str:
    """Get a valid access token, refreshing if expired."""
    now = datetime.utcnow()

    if connection.token_expires_at and now < connection.token_expires_at - timedelta(minutes=5):
        creds = decrypt_credentials(connection.access_token_encrypted)
        return creds["access_token"]

    # Token expired or close to expiring — refresh
    refresh_creds = decrypt_credentials(connection.refresh_token_encrypted)
    refresh_token = refresh_creds["refresh_token"]

    try:
        token_data = await refresh_access_token(refresh_token)
    except httpx.HTTPStatusError as e:
        logger.error(f"Salesforce token refresh failed: {e.response.text}")
        connection.connection_status = "error"
        db.commit()
        raise ValueError(
            "Salesforce connection expired. Please reconnect your Salesforce org in Settings."
        )

    new_access_token = token_data["access_token"]
    connection.access_token_encrypted = encrypt_credentials({"access_token": new_access_token})
    # Salesforce tokens typically last 2 hours
    connection.token_expires_at = now + timedelta(hours=2)
    connection.connection_status = "connected"
    if "instance_url" in token_data:
        connection.instance_url = token_data["instance_url"]
    db.commit()

    return new_access_token


async def revoke_token(access_token: str) -> None:
    """Revoke a Salesforce access token."""
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                SALESFORCE_REVOKE_URL,
                data={"token": access_token},
            )
    except Exception:
        logger.warning("Failed to revoke Salesforce token", exc_info=True)
