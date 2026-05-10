"""Service layer for per-user persistent DuckDB instances.

Coordinates:
- creating the per-user DuckDB on first upload
- appending uploads as new tables (DB rows + DuckDB CREATE TABLE)
- dropping tables and the whole DB
"""

import logging
import os
from typing import Optional

from sqlalchemy.orm import Session

from app.core.config import LOCAL_DUCKDB_DIR
from app.connections import local_duckdb_persistent as ldp
from app.models.local_duckdb import LocalDuckDB, LocalDuckDBTable

logger = logging.getLogger(__name__)


def get_user_db(db: Session, user_id: str) -> Optional[LocalDuckDB]:
    """Return the user's LocalDuckDB row, or None if they don't have one yet."""
    return db.query(LocalDuckDB).filter(LocalDuckDB.user_id == user_id).first()


def get_or_create_user_db(db: Session, user_id: str) -> LocalDuckDB:
    """Return the user's LocalDuckDB, creating both the DB row and the on-disk
    file if missing."""
    existing = get_user_db(db, user_id)
    if existing is not None:
        return existing

    ldp.ensure_storage_dir(LOCAL_DUCKDB_DIR)
    file_path = ldp.get_user_db_path(LOCAL_DUCKDB_DIR, user_id)

    local_db = LocalDuckDB(user_id=user_id, file_path=file_path)
    db.add(local_db)
    db.commit()
    db.refresh(local_db)
    return local_db


async def add_uploaded_file(
    db: Session,
    user_id: str,
    upload_path: str,
    filename: str,
    source_type: str,
) -> LocalDuckDBTable:
    """Load an uploaded file as a new table inside the user's persistent DuckDB.

    `source_type` is "excel_csv" or "local_upload" (for UI grouping). Returns the
    persisted LocalDuckDBTable row.
    """
    local_db = get_or_create_user_db(db, user_id)

    existing = ldp.list_existing_table_names(local_db.file_path)
    file_info = await ldp.append_file(local_db.file_path, upload_path, filename, existing)

    table_row = LocalDuckDBTable(
        local_duckdb_id=local_db.id,
        table_name=file_info["table_name"],
        original_filename=filename,
        source_type=source_type,
        row_count=file_info["row_count"],
        columns=file_info["columns"],
    )
    db.add(table_row)
    db.commit()
    db.refresh(table_row)
    return table_row


async def drop_table(db: Session, user_id: str, table_id: str) -> bool:
    """Drop a single table from the user's DuckDB and remove its row.

    Returns True if a table was removed, False if it didn't exist or didn't
    belong to the user.
    """
    table_row = (
        db.query(LocalDuckDBTable)
        .join(LocalDuckDB, LocalDuckDBTable.local_duckdb_id == LocalDuckDB.id)
        .filter(LocalDuckDBTable.id == table_id, LocalDuckDB.user_id == user_id)
        .first()
    )
    if table_row is None:
        return False

    local_db = db.query(LocalDuckDB).filter(LocalDuckDB.id == table_row.local_duckdb_id).first()
    if local_db and os.path.exists(local_db.file_path):
        await ldp.drop_table(local_db.file_path, table_row.table_name)

    db.delete(table_row)
    db.commit()
    return True


def delete_user_db(db: Session, user_id: str) -> bool:
    """Drop the user's entire LocalDuckDB: file + all rows. Returns True if
    something was deleted."""
    local_db = get_user_db(db, user_id)
    if local_db is None:
        return False

    if os.path.exists(local_db.file_path):
        try:
            os.unlink(local_db.file_path)
        except Exception as e:
            logger.warning(f"Failed to delete LocalDuckDB file {local_db.file_path}: {e}")

    db.delete(local_db)
    db.commit()
    return True
