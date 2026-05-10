"""Unified context file service — user files + integration-synced files."""

import uuid
from typing import Optional

from sqlalchemy.orm import Session

from app.models.context import ContextFile

MAX_FILE_SIZE_BYTES = 100 * 1024  # 100KB
MAX_USER_FILES = 10

DEFAULT_CONTEXT = """\
# Context

Add background information about your data, team, and business that helps the assistant give better answers.

## Preferences
- Preferred date formats
- Default chart styles
- SQL dialect preferences

## Glossary
- MRR = Monthly Recurring Revenue
- DAU = Daily Active Users
"""


def list_files(db: Session, user_id: str) -> list[ContextFile]:
    """List all context files for a user (user + integration)."""
    return (
        db.query(ContextFile)
        .filter(ContextFile.user_id == user_id)
        .order_by(ContextFile.source, ContextFile.filename)
        .all()
    )


def read_file(db: Session, user_id: str, filename: str) -> Optional[ContextFile]:
    """Read a single context file by filename."""
    return (
        db.query(ContextFile)
        .filter(ContextFile.user_id == user_id, ContextFile.filename == filename)
        .first()
    )


def write_file(db: Session, user_id: str, filename: str, content: str) -> ContextFile:
    """Create or update a user context file. Enforces size limit."""
    if len(content.encode("utf-8")) > MAX_FILE_SIZE_BYTES:
        raise ValueError(f"File content exceeds maximum size of {MAX_FILE_SIZE_BYTES // 1024}KB")

    existing = read_file(db, user_id, filename)
    if existing:
        if existing.source != "user":
            raise ValueError("Cannot edit integration-synced files")
        existing.content = content
        db.commit()
        db.refresh(existing)
        return existing

    # Check file count limit
    count = db.query(ContextFile).filter(
        ContextFile.user_id == user_id, ContextFile.source == "user"
    ).count()
    if count >= MAX_USER_FILES:
        raise ValueError(f"Maximum of {MAX_USER_FILES} user context files allowed")

    context_file = ContextFile(
        id=str(uuid.uuid4()),
        user_id=user_id,
        filename=filename,
        content=content,
        source="user",
    )
    db.add(context_file)
    db.commit()
    db.refresh(context_file)
    return context_file


def delete_file(db: Session, user_id: str, filename: str) -> bool:
    """Delete a user context file. Returns True if deleted, False if not found."""
    existing = read_file(db, user_id, filename)
    if not existing:
        return False
    if existing.source != "user":
        raise ValueError("Cannot delete integration-synced files")
    db.delete(existing)
    db.commit()
    return True


def get_context(db: Session, user_id: str) -> str:
    """Get concatenated content of all context files for system prompt injection."""
    files = list_files(db, user_id)
    if not files:
        return ""

    sections = []
    for f in files:
        if f.content.strip():
            sections.append(f"### {f.filename}\n{f.content.strip()}")

    if not sections:
        return ""

    return "\n\n".join(sections)


def ensure_default_context(db: Session, user_id: str) -> list[ContextFile]:
    """Create default context.md if user has no user context files."""
    count = db.query(ContextFile).filter(
        ContextFile.user_id == user_id, ContextFile.source == "user"
    ).count()
    if count > 0:
        return list_files(db, user_id)

    context_file = ContextFile(
        id=str(uuid.uuid4()),
        user_id=user_id,
        filename="context.md",
        content=DEFAULT_CONTEXT,
        source="user",
    )
    db.add(context_file)
    db.commit()
    db.refresh(context_file)
    return list_files(db, user_id)


def _integration_filename(integration_type: str, name: str) -> str:
    """Build a context filename, stripping a redundant type prefix/suffix from the name."""
    stripped = name.strip()
    lower_type = integration_type.lower()
    if stripped.lower().startswith(f"{lower_type}-") or stripped.lower().startswith(f"{lower_type}_"):
        stripped = stripped[len(lower_type) + 1 :]
    if stripped.lower().endswith(f"-{lower_type}") or stripped.lower().endswith(f"_{lower_type}"):
        stripped = stripped[: -(len(lower_type) + 1)]
    stripped = stripped.strip() or name.strip()
    return f"{integration_type}-{stripped}.yml"


def upsert_integration_context(
    db: Session,
    user_id: str,
    integration_id: str,
    integration_type: str,
    name: str,
    content: str,
) -> ContextFile:
    """Write or update a context file for an integration (e.g. dbt-myproject.yml, omni-myproject.yml)."""
    filename = _integration_filename(integration_type, name)

    existing = (
        db.query(ContextFile)
        .filter(
            ContextFile.user_id == user_id,
            ContextFile.integration_id == integration_id,
        )
        .first()
    )

    if existing:
        existing.filename = filename
        existing.content = content
        db.commit()
        db.refresh(existing)
        return existing

    context_file = ContextFile(
        id=str(uuid.uuid4()),
        user_id=user_id,
        filename=filename,
        content=content,
        source="integration",
        integration_id=integration_id,
    )
    db.add(context_file)
    db.commit()
    db.refresh(context_file)
    return context_file


def delete_integration_context(db: Session, integration_id: str) -> None:
    """Delete all context files tied to an integration."""
    db.query(ContextFile).filter(
        ContextFile.integration_id == integration_id
    ).delete()
    db.commit()
