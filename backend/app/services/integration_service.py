"""Integration service — CRUD, sync, and context generation."""

import io
import json
import logging
import tarfile
import tempfile
import uuid
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional

import httpx

from sqlalchemy.orm import Session

from app.core.security import encrypt_credentials, decrypt_credentials
from app.models.integration import Integration, IntegrationSync
from app.services.dbt_parser import parse_manifest
from app.services.omni_parser import parse_repo as parse_omni_repo
from app.services import context_service

logger = logging.getLogger(__name__)

SUPPORTED_TYPES = {"dbt", "omni"}


def create_integration(db: Session, user_id: str, integration_type: str, name: str, config: dict) -> Integration:
    """Create a new integration with encrypted config."""
    if integration_type not in SUPPORTED_TYPES:
        raise ValueError(f"Unsupported integration type: {integration_type}")

    if not config.get("repo_url"):
        raise ValueError("repo_url is required")

    encrypted = encrypt_credentials(config)
    integration = Integration(
        id=str(uuid.uuid4()),
        user_id=user_id,
        integration_type=integration_type,
        name=name,
        config_encrypted=encrypted,
        connection_status="pending",
    )
    db.add(integration)
    db.commit()
    db.refresh(integration)
    return integration


def list_integrations(db: Session, user_id: str) -> list[Integration]:
    """List all integrations for a user."""
    return (
        db.query(Integration)
        .filter(Integration.user_id == user_id)
        .order_by(Integration.created_at.desc())
        .all()
    )


def get_integration(db: Session, user_id: str, integration_id: str) -> Optional[Integration]:
    """Get a single integration owned by the user."""
    return (
        db.query(Integration)
        .filter(Integration.id == integration_id, Integration.user_id == user_id)
        .first()
    )


def delete_integration(db: Session, user_id: str, integration_id: str) -> bool:
    """Delete an integration and all related data (cascades context files too)."""
    integration = get_integration(db, user_id, integration_id)
    if not integration:
        return False
    context_service.delete_integration_context(db, integration_id)
    db.delete(integration)
    db.commit()
    return True


def sync_integration(db: Session, user_id: str, integration_id: str) -> IntegrationSync:
    """Trigger a sync for an integration — clone repo, parse manifest, store metadata."""
    integration = get_integration(db, user_id, integration_id)
    if not integration:
        raise ValueError("Integration not found")

    sync = IntegrationSync(
        id=str(uuid.uuid4()),
        integration_id=integration.id,
        status="running",
        started_at=datetime.utcnow(),
    )
    db.add(sync)
    db.commit()

    try:
        config = decrypt_credentials(integration.config_encrypted)
        if integration.integration_type == "dbt":
            manifest = _clone_and_find_manifest(config)
            parsed = parse_manifest(manifest)
            context_content = _format_metadata_as_markdown(parsed)
        elif integration.integration_type == "omni":
            parsed = _clone_and_parse_omni(config)
            context_content = _format_omni_metadata_as_markdown(parsed)
        else:
            raise ValueError(
                f"Unsupported integration type: {integration.integration_type}"
            )

        context_service.upsert_integration_context(
            db,
            user_id,
            integration.id,
            integration.integration_type,
            integration.name,
            context_content,
        )

        sync.status = "completed"
        sync.completed_at = datetime.utcnow()
        sync.metadata_count = len(parsed)
        integration.connection_status = "connected"
        integration.last_synced_at = datetime.utcnow()

    except Exception as e:
        logger.error(f"Sync failed for integration {integration_id}: {e}")
        sync.status = "failed"
        sync.completed_at = datetime.utcnow()
        sync.error_message = str(e)
        integration.connection_status = "error"

    db.commit()
    db.refresh(sync)
    return sync


@contextmanager
def _download_repo(config: dict):
    """Download a GitHub repo tarball and yield the extracted repo root path."""
    repo_url = config["repo_url"]
    branch = config.get("branch", "main")
    auth_token = config.get("auth_token")

    # Extract owner/repo from URL
    # Supports: https://github.com/owner/repo.git, https://github.com/owner/repo
    path = repo_url.rstrip("/").removesuffix(".git")
    parts = path.split("github.com/")
    if len(parts) != 2:
        raise ValueError("Only GitHub repository URLs are supported.")
    owner_repo = parts[1]  # e.g. "owner/repo"

    tarball_url = f"https://api.github.com/repos/{owner_repo}/tarball/{branch}"
    headers = {"Accept": "application/vnd.github+json"}
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"

    with httpx.Client(follow_redirects=True, timeout=120) as client:
        resp = client.get(tarball_url, headers=headers)
        if resp.status_code == 404:
            raise RuntimeError("Repository or branch not found. Check the URL and branch name.")
        if resp.status_code == 401 or resp.status_code == 403:
            raise RuntimeError("Authentication failed. Check your auth token has Contents read access.")
        resp.raise_for_status()

    with tempfile.TemporaryDirectory() as tmpdir:
        with tarfile.open(fileobj=io.BytesIO(resp.content), mode="r:gz") as tar:
            tar.extractall(path=tmpdir)
        # Tarball extracts to a single subdirectory like "owner-repo-sha/"
        extracted_dirs = list(Path(tmpdir).iterdir())
        repo_root = extracted_dirs[0] if extracted_dirs else Path(tmpdir)
        yield repo_root


def _load_dbt_manifest(repo_root: Path) -> dict:
    """Locate and parse a dbt manifest.json inside an extracted repo."""
    manifest = _find_manifest(repo_root)
    if not manifest:
        raise FileNotFoundError(
            "manifest.json not found. Run `dbt compile` or `dbt build` to generate it, "
            "then commit it to the repository."
        )
    with open(manifest, "r") as f:
        return json.load(f)


def _clone_and_find_manifest(config: dict) -> dict:
    """Download a repo and return the parsed dbt manifest.json contents."""
    with _download_repo(config) as repo_root:
        return _load_dbt_manifest(repo_root)


def _clone_and_parse_omni(config: dict) -> list[dict]:
    """Download an Omni repo and return its parsed view/model/topic metadata."""
    with _download_repo(config) as repo_root:
        return parse_omni_repo(repo_root)


def _find_manifest(repo_root: Path) -> Optional[Path]:
    """Search common locations for dbt manifest.json."""
    search_paths = [
        repo_root / "target" / "manifest.json",
        repo_root / "manifest.json",
    ]
    # Also check subdirectories that might contain dbt projects
    for subdir in repo_root.iterdir():
        if subdir.is_dir():
            search_paths.append(subdir / "target" / "manifest.json")

    for path in search_paths:
        if path.exists():
            return path

    return None


def get_latest_sync(db: Session, integration_id: str) -> Optional[IntegrationSync]:
    """Get the latest sync for an integration."""
    return (
        db.query(IntegrationSync)
        .filter(IntegrationSync.integration_id == integration_id)
        .order_by(IntegrationSync.started_at.desc())
        .first()
    )


def _format_metadata_as_markdown(parsed: list[dict]) -> str:
    """Format parsed dbt metadata into markdown for context file storage."""
    if not parsed:
        return ""

    lines = ["# dbt Project Context\n"]

    models = [m for m in parsed if m["metadata_type"] == "model"]
    sources = [m for m in parsed if m["metadata_type"] == "source"]
    metrics = [m for m in parsed if m["metadata_type"] == "metric"]

    if models:
        lines.append("## Models")
        for m in models:
            qualified = ".".join(filter(None, [m.get("database"), m.get("schema_name"), m["name"]]))
            lines.append(f"\n**{qualified}**")
            if m.get("description"):
                lines.append(f"  {m['description']}")
            if m.get("meta", {}).get("materialized"):
                lines.append(f"  Materialization: {m['meta']['materialized']}")
            if m.get("columns"):
                lines.append("  Columns:")
                for col in m["columns"]:
                    desc = f" — {col['description']}" if col.get("description") else ""
                    dtype = f" ({col['data_type']})" if col.get("data_type") else ""
                    lines.append(f"    - {col['name']}{dtype}{desc}")
            if m.get("tags"):
                lines.append(f"  Tags: {', '.join(m['tags'])}")

    if sources:
        lines.append("\n## Sources")
        for s in sources:
            qualified = ".".join(filter(None, [s.get("database"), s.get("schema_name"), s["name"]]))
            lines.append(f"\n**{qualified}**")
            if s.get("description"):
                lines.append(f"  {s['description']}")
            if s.get("columns"):
                lines.append("  Columns:")
                for col in s["columns"]:
                    desc = f" — {col['description']}" if col.get("description") else ""
                    dtype = f" ({col['data_type']})" if col.get("data_type") else ""
                    lines.append(f"    - {col['name']}{dtype}{desc}")

    if metrics:
        lines.append("\n## Metrics")
        for m in metrics:
            lines.append(f"\n**{m['name']}**")
            if m.get("description"):
                lines.append(f"  {m['description']}")

    return "\n".join(lines)


def _format_omni_metadata_as_markdown(parsed: list[dict]) -> str:
    """Format parsed Omni metadata into markdown for context file storage."""
    if not parsed:
        return ""

    lines = ["# Omni Project Context\n"]

    views = [m for m in parsed if m["metadata_type"] == "view"]
    models = [m for m in parsed if m["metadata_type"] == "model"]
    topics = [m for m in parsed if m["metadata_type"] == "topic"]

    if views:
        lines.append("## Views")
        for v in views:
            table = v.get("meta", {}).get("table_name") or v.get("meta", {}).get("sql_table_name")
            qualified = ".".join(filter(None, [v.get("schema_name"), v["name"]]))
            lines.append(f"\n**{qualified or v['name']}**")
            if table:
                lines.append(f"  Table: {table}")
            if v.get("description"):
                lines.append(f"  {v['description']}")
            if v.get("columns"):
                lines.append("  Fields:")
                for col in v["columns"]:
                    kind = f" [{col['kind']}]" if col.get("kind") else ""
                    dtype = f" ({col['data_type']})" if col.get("data_type") else ""
                    desc = f" — {col['description']}" if col.get("description") else ""
                    lines.append(f"    - {col['name']}{kind}{dtype}{desc}")

    if models:
        lines.append("\n## Models")
        for m in models:
            lines.append(f"\n**{m['name']}**")
            if m.get("description"):
                lines.append(f"  {m['description']}")
            referenced = m.get("meta", {}).get("views") or []
            if referenced:
                lines.append(f"  Views: {', '.join(str(v) for v in referenced)}")

    if topics:
        lines.append("\n## Topics")
        for t in topics:
            lines.append(f"\n**{t['name']}**")
            if t.get("description"):
                lines.append(f"  {t['description']}")
            base = t.get("meta", {}).get("base_view")
            if base:
                lines.append(f"  Base view: {base}")

    return "\n".join(lines)
