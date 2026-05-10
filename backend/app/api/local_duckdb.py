"""Endpoints for the per-user persistent local DuckDB."""

import os
import tempfile

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_auth
from app.models.user import User
from app.connections.duckdb_local import (
    ALLOWED_EXCEL_CSV_EXTENSIONS,
    ALLOWED_LOCAL_UPLOAD_EXTENSIONS,
    ALLOWED_UPLOAD_EXTENSIONS,
    MAX_FILE_SIZE_BYTES,
)
from app.schemas.local_duckdb import (
    LocalDuckDBStatus,
    LocalDuckDBTableInfo,
    LocalDuckDBUploadResponse,
)
from app.services import local_duckdb_service

router = APIRouter(tags=["local-duckdb"])


def _table_to_info(t) -> LocalDuckDBTableInfo:
    return LocalDuckDBTableInfo(
        id=t.id,
        table_name=t.table_name,
        original_filename=t.original_filename,
        source_type=t.source_type,
        row_count=t.row_count,
        columns=t.columns or [],
        is_demo=bool(t.is_demo),
        created_at=t.created_at.isoformat() + "Z" if t.created_at else "",
    )


@router.get("/api/local-duckdb", response_model=LocalDuckDBStatus)
async def get_local_duckdb_status(
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Return the current user's persistent DuckDB and its tables."""
    local_db = local_duckdb_service.get_user_db(db, user.id)
    if local_db is None:
        return LocalDuckDBStatus(exists=False)
    return LocalDuckDBStatus(
        exists=True,
        id=local_db.id,
        tables=[_table_to_info(t) for t in local_db.tables],
    )


@router.post("/api/local-duckdb/upload", response_model=LocalDuckDBUploadResponse)
async def upload_local_file(
    file: UploadFile = File(...),
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Append a CSV/Excel/Parquet/JSON file to the user's persistent DuckDB."""
    filename = file.filename or "upload"
    ext = os.path.splitext(filename.lower())[1]

    if ext not in ALLOWED_UPLOAD_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Accepted: {', '.join(sorted(ALLOWED_UPLOAD_EXTENSIONS))}",
        )

    content = await file.read()
    if len(content) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"File is too large ({len(content) / 1024 / 1024:.1f} MB). Maximum size is {MAX_FILE_SIZE_BYTES // 1024 // 1024} MB.",
        )

    source_type = "excel_csv" if ext in ALLOWED_EXCEL_CSV_EXTENSIONS else "local_upload"

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
    try:
        tmp.write(content)
        tmp.close()
        try:
            table_row = await local_duckdb_service.add_uploaded_file(
                db, user.id, tmp.name, filename, source_type
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        finally:
            try:
                os.unlink(tmp.name)
            except Exception:
                pass
    except HTTPException:
        raise
    except Exception as e:
        try:
            os.unlink(tmp.name)
        except Exception:
            pass
        raise HTTPException(status_code=400, detail=str(e))

    return LocalDuckDBUploadResponse(
        local_duckdb_id=table_row.local_duckdb_id,
        table=_table_to_info(table_row),
    )


@router.delete("/api/local-duckdb/tables/{table_id}")
async def delete_local_table(
    table_id: str,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Drop a single table from the user's persistent DuckDB."""
    removed = await local_duckdb_service.drop_table(db, user.id, table_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Table not found")
    return {"success": True}


@router.delete("/api/local-duckdb")
async def delete_local_duckdb(
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Delete the user's entire persistent DuckDB (file + rows)."""
    removed = local_duckdb_service.delete_user_db(db, user.id)
    if not removed:
        raise HTTPException(status_code=404, detail="No local DuckDB found")
    return {"success": True}
