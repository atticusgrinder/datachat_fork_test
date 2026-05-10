"""Auto-attach demo data sources for new users.

On a user's first authenticated request we attach two read-only demos:

  1. A "Demo: RetailFlow" warehouse pointing at the MotherDuck demo (if
     DEMO_MOTHERDUCK_TOKEN / DEMO_MOTHERDUCK_DATABASE are set).
  2. A "Demo: Marketing Spend" CSV loaded into the user's persistent local
     DuckDB so they can immediately try a multi-source chat.

Both are dismissable — the User row carries a `demos_initialized` flag that's
flipped to true after the first attach so that deleting a demo doesn't make it
silently reappear on the next login.
"""

import asyncio
import logging
import os
import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from app.connections import local_duckdb_persistent as ldp
from app.core.config import (
    DEMO_MOTHERDUCK_TOKEN, DEMO_MOTHERDUCK_DATABASE, LOCAL_DUCKDB_DIR,
)
from app.core.security import encrypt_credentials
from app.models.local_duckdb import LocalDuckDB, LocalDuckDBTable
from app.models.user import User
from app.models.warehouse import WarehouseConnection

logger = logging.getLogger(__name__)

DEMO_WAREHOUSE_NAME = "Demo: RetailFlow"
DEMO_WAREHOUSE_TYPE = "motherduck"

DEMO_CSV_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "data",
    "demo_marketing_spend.csv",
)
DEMO_CSV_DISPLAY_NAME = "Demo: Marketing Spend"


def _attach_demo_warehouse(db: Session, user: User) -> bool:
    """Attach the MotherDuck demo warehouse if env is configured. Idempotent —
    no-ops if the user already has a demo warehouse or env isn't configured."""
    if not DEMO_MOTHERDUCK_TOKEN or not DEMO_MOTHERDUCK_DATABASE:
        return False

    existing = db.query(WarehouseConnection).filter(
        WarehouseConnection.user_id == user.id,
        WarehouseConnection.is_demo.is_(True),
    ).first()
    if existing is not None:
        return False

    creds = encrypt_credentials({
        "token": DEMO_MOTHERDUCK_TOKEN,
        "database": DEMO_MOTHERDUCK_DATABASE,
    })
    warehouse = WarehouseConnection(
        id=str(uuid.uuid4()),
        user_id=user.id,
        warehouse_type=DEMO_WAREHOUSE_TYPE,
        name=DEMO_WAREHOUSE_NAME,
        credentials_encrypted=creds,
        connection_status="connected",
        is_read_only=True,
        is_demo=True,
        last_tested_at=datetime.utcnow(),
    )
    db.add(warehouse)
    return True


async def _attach_demo_local_duckdb(db: Session, user: User) -> bool:
    """Append the bundled demo CSV as a table inside the user's local DuckDB.
    Returns True if a row was inserted; False if the CSV file is missing.

    Creates the on-disk DuckDB file (and its row) if the user doesn't have one
    yet — same path the upload service uses.
    """
    if not os.path.exists(DEMO_CSV_PATH):
        logger.warning("Demo CSV not found at %s", DEMO_CSV_PATH)
        return False

    local_db = (
        db.query(LocalDuckDB).filter(LocalDuckDB.user_id == user.id).first()
    )
    if local_db is not None:
        existing_demo = (
            db.query(LocalDuckDBTable)
            .filter(
                LocalDuckDBTable.local_duckdb_id == local_db.id,
                LocalDuckDBTable.is_demo.is_(True),
            )
            .first()
        )
        if existing_demo is not None:
            return False

    if local_db is None:
        ldp.ensure_storage_dir(LOCAL_DUCKDB_DIR)
        local_db = LocalDuckDB(
            user_id=user.id,
            file_path=ldp.get_user_db_path(LOCAL_DUCKDB_DIR, user.id),
        )
        db.add(local_db)
        # Commit + refresh now so we release the SQLite write-lock before the
        # blocking DuckDB append below. Holding both locks on SQLite causes
        # `database is locked` under any concurrent request.
        db.commit()
        db.refresh(local_db)

    # Pass the real basename so append_file can detect the .csv extension.
    # The pretty display name is set on the table row below.
    csv_basename = os.path.basename(DEMO_CSV_PATH)
    existing = ldp.list_existing_table_names(local_db.file_path)
    file_info = await ldp.append_file(
        local_db.file_path, DEMO_CSV_PATH, csv_basename, existing,
    )

    table = LocalDuckDBTable(
        local_duckdb_id=local_db.id,
        table_name=file_info["table_name"],
        original_filename=DEMO_CSV_DISPLAY_NAME,
        source_type="excel_csv",
        row_count=file_info["row_count"],
        columns=file_info["columns"],
        is_demo=True,
    )
    db.add(table)
    return True


_user_locks: dict[str, asyncio.Lock] = {}


def _user_lock(user_id: str) -> asyncio.Lock:
    """Per-user in-process lock so the chat page firing many concurrent
    requests doesn't fan out into multiple parallel demo attaches."""
    lock = _user_locks.get(user_id)
    if lock is None:
        lock = asyncio.Lock()
        _user_locks[user_id] = lock
    return lock


async def ensure_demos(db: Session, user: User) -> None:
    """Attach both demos exactly once per user. No-op if `demos_initialized`
    is already true (e.g. user previously dismissed the demos).

    Commits between stages so we don't hold a SQLite write-lock across the
    blocking DuckDB append. Tracks success per-stage so a transient failure
    in one demo doesn't permanently block the other. Serialized per user to
    keep concurrent requests from racing each other.
    """
    if user.demos_initialized:
        return

    async with _user_lock(user.id):
        # Re-read after acquiring the lock — another request may have already
        # finished the attach while we were waiting.
        db.refresh(user)
        if user.demos_initialized:
            return

        await _ensure_demos_locked(db, user)


async def _ensure_demos_locked(db: Session, user: User) -> None:
    warehouse_ok = False
    duckdb_ok = False

    try:
        _attach_demo_warehouse(db, user)
        db.commit()
        warehouse_ok = True
    except Exception:
        db.rollback()
        logger.exception("Demo warehouse attach failed for user %s", user.id)

    try:
        await _attach_demo_local_duckdb(db, user)
        db.commit()
        duckdb_ok = True
    except Exception:
        db.rollback()
        logger.exception("Demo DuckDB attach failed for user %s", user.id)

    # Only flip the flag once both succeeded — a transient failure (e.g. an
    # SQLite lock during signup) shouldn't permanently strand the user without
    # the missing demo. If only one demo's prerequisites are configured (e.g.
    # self-hoster without DEMO_MOTHERDUCK_TOKEN), the corresponding _attach_*
    # returns silently, so it counts as "ok" for flag purposes.
    if warehouse_ok and duckdb_ok:
        user.demos_initialized = True
        db.commit()
        db.refresh(user)


# Back-compat alias for existing callers.
ensure_demo_warehouse = ensure_demos
