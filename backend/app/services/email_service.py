"""Resend email wrapper. Stateless — call send_html() to deliver an email."""

import logging
import httpx

from app.core.config import RESEND_API_KEY, RESEND_FROM_EMAIL

logger = logging.getLogger(__name__)

RESEND_URL = "https://api.resend.com/emails"


class EmailNotConfiguredError(RuntimeError):
    """Raised when RESEND_API_KEY is not set."""


class EmailSendError(RuntimeError):
    """Raised when Resend rejects a send. Carries the upstream status + message."""

    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(f"Resend error {status_code}: {message}")


def _extract_resend_message(body_text: str) -> str:
    try:
        import json as _json
        data = _json.loads(body_text)
        if isinstance(data, dict):
            return data.get("message") or data.get("error") or body_text
    except Exception:
        pass
    return body_text


async def send_html(*, to: str, subject: str, html: str) -> str:
    """Send an HTML email via Resend. Returns the Resend message id."""
    if not RESEND_API_KEY:
        raise EmailNotConfiguredError(
            "RESEND_API_KEY is not configured. Set it in backend/.env to enable email sending."
        )

    payload = {
        "from": RESEND_FROM_EMAIL,
        "to": [to],
        "subject": subject,
        "html": html,
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            RESEND_URL,
            headers={
                "Authorization": f"Bearer {RESEND_API_KEY}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
    if resp.status_code >= 400:
        logger.error("Resend send failed: %s %s", resp.status_code, resp.text)
        raise EmailSendError(resp.status_code, _extract_resend_message(resp.text))
    data = resp.json()
    return data.get("id", "")
