"""File upload endpoints for DuckDB-backed data sources."""

import os
import tempfile

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File

from app.core.dependencies import require_auth
from app.models.user import User
from app.connections.duckdb_local import (
    append_file_to_session,
    create_file_upload_session,
    create_duckdb_upload_session,
    get_file_session,
    remove_file_session,
    ALLOWED_UPLOAD_EXTENSIONS,
    ALLOWED_EXCEL_CSV_EXTENSIONS,
    ALLOWED_DUCKDB_EXTENSIONS,
    MAX_FILE_SIZE_BYTES,
)

router = APIRouter(tags=["files"])

ALL_ALLOWED_EXTENSIONS = ALLOWED_UPLOAD_EXTENSIONS | ALLOWED_DUCKDB_EXTENSIONS


@router.post("/api/files/upload")
async def upload_file(
    file: UploadFile = File(...),
    user: User = Depends(require_auth),
):
    """Upload a data file (CSV, Excel, Parquet, JSON) and create a DuckDB session."""
    filename = file.filename or "upload"
    ext = os.path.splitext(filename.lower())[1]

    if ext not in ALL_ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Accepted: {', '.join(sorted(ALL_ALLOWED_EXTENSIONS))}",
        )

    # Read file content with size check
    content = await file.read()
    if len(content) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"File is too large ({len(content) / 1024 / 1024:.1f} MB). Maximum size is {MAX_FILE_SIZE_BYTES // 1024 // 1024} MB.",
        )

    # Write to temp file
    suffix = ext
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    try:
        tmp.write(content)
        tmp.close()

        if ext in ALLOWED_DUCKDB_EXTENSIONS:
            source_type = "duckdb"
            session = await create_duckdb_upload_session(
                user_id=user.id,
                file_path=tmp.name,
                filename=filename,
            )
        else:
            source_type = "excel_csv" if ext in ALLOWED_EXCEL_CSV_EXTENSIONS else "local_upload"
            session = await create_file_upload_session(
                user_id=user.id,
                file_path=tmp.name,
                filename=filename,
                source_type=source_type,
            )

        return {
            "session_id": session.session_id,
            "source_type": session.source_type,
            "metadata": session.metadata,
        }

    except Exception as e:
        # Clean up temp file on error
        try:
            os.unlink(tmp.name)
        except Exception:
            pass
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/api/files/{session_id}/append")
async def append_file(
    session_id: str,
    file: UploadFile = File(...),
    user: User = Depends(require_auth),
):
    """Append another data file to an existing file-upload session as a new table.

    Enables cross-file joins within the same DuckDB connection. Only works for
    file-upload sessions (excel/csv/parquet/json), not .duckdb-backed sessions.
    """
    session = get_file_session(session_id, user.id)
    if session is None:
        raise HTTPException(status_code=404, detail="File session not found or expired")

    if session.source_type == "duckdb":
        raise HTTPException(
            status_code=400,
            detail="Cannot append files to a .duckdb-backed session. Start a new session instead.",
        )

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

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
    try:
        tmp.write(content)
        tmp.close()

        try:
            await append_file_to_session(session, tmp.name, filename)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        return {
            "session_id": session.session_id,
            "source_type": session.source_type,
            "metadata": session.metadata,
        }

    except HTTPException:
        try:
            os.unlink(tmp.name)
        except Exception:
            pass
        raise
    except Exception as e:
        try:
            os.unlink(tmp.name)
        except Exception:
            pass
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/api/files/{session_id}")
async def get_file_session_info(
    session_id: str,
    user: User = Depends(require_auth),
):
    """Get metadata for an active file session."""
    session = get_file_session(session_id, user.id)
    if session is None:
        raise HTTPException(status_code=404, detail="File session not found or expired")

    return {
        "session_id": session.session_id,
        "source_type": session.source_type,
        "filename": session.filename,
        "metadata": session.metadata,
    }


@router.delete("/api/files/{session_id}")
async def delete_file_session(
    session_id: str,
    user: User = Depends(require_auth),
):
    """Remove a file session and free resources."""
    removed = remove_file_session(session_id, user.id)
    if not removed:
        raise HTTPException(status_code=404, detail="File session not found")
    return {"success": True}
