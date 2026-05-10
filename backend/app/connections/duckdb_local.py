"""Local DuckDB executor for file uploads and .duckdb files."""

import asyncio
import logging
import os
import re
import time
import uuid
from typing import Optional

from tabulate import tabulate

from app.connections.base import WarehouseExecutor, MAX_ROWS, MAX_CHARS

logger = logging.getLogger("warehouse_executor")

# In-memory session store: session_id -> DuckDBFileSession
_file_sessions: dict[str, "DuckDBFileSession"] = {}

SESSION_TIMEOUT_SECONDS = 2 * 60 * 60  # 2 hours
MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB
MAX_SAMPLE_ROWS = 5
QUERY_TIMEOUT_SECONDS = 30

ALLOWED_EXCEL_CSV_EXTENSIONS = {".csv", ".tsv", ".xlsx", ".xls"}
ALLOWED_LOCAL_UPLOAD_EXTENSIONS = {".parquet", ".json", ".ndjson"}
ALLOWED_UPLOAD_EXTENSIONS = ALLOWED_EXCEL_CSV_EXTENSIONS | ALLOWED_LOCAL_UPLOAD_EXTENSIONS
ALLOWED_DUCKDB_EXTENSIONS = {".duckdb", ".db"}


def _filename_to_table_name(filename: str, taken: set[str]) -> str:
    """Convert a filename to a safe DuckDB table identifier, unique within `taken`."""
    base = os.path.splitext(os.path.basename(filename))[0]
    sanitized = re.sub(r"[^a-zA-Z0-9_]", "_", base).lower()
    sanitized = re.sub(r"_+", "_", sanitized).strip("_")
    if not sanitized:
        sanitized = "data"
    if sanitized[0].isdigit():
        sanitized = f"t_{sanitized}"

    candidate = sanitized
    suffix = 2
    while candidate in taken:
        candidate = f"{sanitized}_{suffix}"
        suffix += 1
    return candidate


class DuckDBFileSession:
    """Holds an in-memory DuckDB connection. Supports multiple uploaded files,
    each loaded as its own table within the same connection so cross-file joins work."""

    def __init__(
        self,
        session_id: str,
        user_id: str,
        filename: str,
        source_type: str,  # "file_upload" or "duckdb"
    ):
        self.session_id = session_id
        self.user_id = user_id
        self.filename = filename  # primary/first file (kept for display)
        self.source_type = source_type
        self.created_at = time.time()
        self.last_accessed = time.time()
        self._conn = None
        self._duckdb_file_path: Optional[str] = None  # for .duckdb files on disk
        # files: list of {"filename": str, "table_name": str, "row_count": int, "columns": [...]}
        self._files: list[dict] = []
        self._metadata: Optional[dict] = None  # cached for .duckdb sessions

    @property
    def is_expired(self) -> bool:
        return (time.time() - self.last_accessed) > SESSION_TIMEOUT_SECONDS

    def touch(self):
        self.last_accessed = time.time()

    def close(self):
        if self._conn is not None:
            try:
                self._conn.close()
            except Exception:
                pass
            self._conn = None
        if self._duckdb_file_path and os.path.exists(self._duckdb_file_path):
            try:
                os.unlink(self._duckdb_file_path)
            except Exception:
                pass

    @property
    def metadata(self) -> Optional[dict]:
        # For .duckdb sessions, return cached metadata; for file sessions build from _files.
        if self.source_type == "duckdb":
            return self._metadata
        if not self._files:
            return None
        # Single-file convenience: keep top-level row_count / columns for the primary file
        primary = self._files[0]
        return {
            "filename": self.filename,
            "row_count": primary["row_count"],
            "column_count": len(primary["columns"]),
            "columns": primary["columns"],
            "tables": [
                {
                    "filename": f["filename"],
                    "name": f["table_name"],
                    "row_count": f["row_count"],
                    "columns": f["columns"],
                }
                for f in self._files
            ],
        }

    @property
    def loaded_table_names(self) -> set[str]:
        return {f["table_name"] for f in self._files}


def _load_file_into_table(conn, file_path: str, filename: str, table_name: str):
    """Load a data file into `conn` as a new table named `table_name`."""
    ext = os.path.splitext(filename.lower())[1]
    quoted = f'"{table_name}"'

    if ext in (".csv", ".tsv"):
        conn.execute(
            f"CREATE TABLE {quoted} AS SELECT * FROM read_csv_auto(?)",
            [file_path],
        )
    elif ext == ".parquet":
        conn.execute(
            f"CREATE TABLE {quoted} AS SELECT * FROM read_parquet(?)",
            [file_path],
        )
    elif ext in (".json", ".ndjson"):
        conn.execute(
            f"CREATE TABLE {quoted} AS SELECT * FROM read_json_auto(?)",
            [file_path],
        )
    elif ext in (".xlsx", ".xls"):
        import pandas as pd
        import io

        df = pd.read_excel(file_path, sheet_name=0, engine="openpyxl" if ext == ".xlsx" else "xlrd")
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False)
        csv_buffer.seek(0)
        csv_bytes = csv_buffer.getvalue().encode("utf-8")
        import tempfile as _tmpfile
        with _tmpfile.NamedTemporaryFile(delete=False, suffix=".csv", mode="wb") as tmp_csv:
            tmp_csv.write(csv_bytes)
            tmp_csv_path = tmp_csv.name
        try:
            conn.execute(
                f"CREATE TABLE {quoted} AS SELECT * FROM read_csv_auto(?)",
                [tmp_csv_path],
            )
        finally:
            os.unlink(tmp_csv_path)
    else:
        raise ValueError(f"Unsupported file type: {ext}")

    row_count = conn.execute(f"SELECT COUNT(*) FROM {quoted}").fetchone()[0]
    columns_info = conn.execute(
        "SELECT column_name, data_type FROM information_schema.columns "
        "WHERE table_name = ? ORDER BY ordinal_position",
        [table_name],
    ).fetchall()
    columns = [{"name": c[0], "type": c[1]} for c in columns_info]

    return {
        "filename": filename,
        "table_name": table_name,
        "row_count": row_count,
        "columns": columns,
    }


def _new_in_memory_conn():
    import duckdb
    conn = duckdb.connect(":memory:")
    conn.execute("INSTALL json; LOAD json;")
    return conn


def _open_duckdb_file(file_path: str):
    """Open a .duckdb file read-only. Returns (conn, metadata)."""
    import duckdb

    conn = duckdb.connect(file_path, read_only=True)

    # Get all tables and views
    tables_result = conn.execute(
        "SELECT table_schema, table_name, table_type "
        "FROM information_schema.tables "
        "WHERE table_schema NOT IN ('information_schema', 'pg_catalog') "
        "ORDER BY table_schema, table_name"
    ).fetchall()

    tables = []
    for schema_name, table_name, table_type in tables_result:
        columns = conn.execute(
            "SELECT column_name, data_type FROM information_schema.columns "
            "WHERE table_schema = ? AND table_name = ? ORDER BY ordinal_position",
            [schema_name, table_name],
        ).fetchall()
        try:
            fqn = f'"{schema_name}"."{table_name}"' if schema_name != "main" else f'"{table_name}"'
            row_count = conn.execute(f"SELECT COUNT(*) FROM {fqn}").fetchone()[0]
        except Exception:
            row_count = None
        tables.append({
            "schema": schema_name,
            "name": table_name,
            "type": table_type,
            "row_count": row_count,
            "columns": [{"name": c[0], "type": c[1]} for c in columns],
        })

    metadata = {
        "filename": os.path.basename(file_path),
        "table_count": len(tables),
        "tables": tables,
    }

    return conn, metadata


async def create_file_upload_session(
    user_id: str, file_path: str, filename: str, source_type: str = "file_upload"
) -> DuckDBFileSession:
    """Load a data file into DuckDB and create a session."""
    _cleanup_expired_sessions()

    session_id = str(uuid.uuid4())
    session = DuckDBFileSession(
        session_id=session_id,
        user_id=user_id,
        filename=filename,
        source_type=source_type,
    )

    def _load():
        conn = _new_in_memory_conn()
        table_name = _filename_to_table_name(filename, set())
        file_info = _load_file_into_table(conn, file_path, filename, table_name)
        session._conn = conn
        session._files.append(file_info)

    await asyncio.to_thread(_load)

    # Clean up temp file after loading into memory
    try:
        os.unlink(file_path)
    except Exception:
        pass

    _file_sessions[session_id] = session
    return session


async def append_file_to_session(
    session: DuckDBFileSession, file_path: str, filename: str
) -> dict:
    """Load an additional file into an existing session as a new table.

    Returns the new file's info dict. Raises ValueError if the session is a
    .duckdb-backed session (those are read-only and not designed to be extended)."""
    if session.source_type == "duckdb":
        raise ValueError("Cannot append additional files to a .duckdb session.")

    def _append():
        table_name = _filename_to_table_name(filename, session.loaded_table_names)
        file_info = _load_file_into_table(session._conn, file_path, filename, table_name)
        session._files.append(file_info)
        return file_info

    file_info = await asyncio.to_thread(_append)

    try:
        os.unlink(file_path)
    except Exception:
        pass

    session.touch()
    return file_info


async def create_duckdb_upload_session(
    user_id: str, file_path: str, filename: str
) -> DuckDBFileSession:
    """Open a .duckdb file and create a session."""
    _cleanup_expired_sessions()

    session_id = str(uuid.uuid4())
    session = DuckDBFileSession(
        session_id=session_id,
        user_id=user_id,
        filename=filename,
        source_type="duckdb",
    )
    session._duckdb_file_path = file_path

    def _open():
        conn, metadata = _open_duckdb_file(file_path)
        session._conn = conn
        session._metadata = metadata

    await asyncio.to_thread(_open)

    _file_sessions[session_id] = session
    return session


def get_file_session(session_id: str, user_id: str) -> Optional[DuckDBFileSession]:
    """Get a session if it exists and belongs to the user."""
    session = _file_sessions.get(session_id)
    if session is None:
        return None
    if session.user_id != user_id:
        return None
    if session.is_expired:
        session.close()
        _file_sessions.pop(session_id, None)
        return None
    session.touch()
    return session


def remove_file_session(session_id: str, user_id: str) -> bool:
    """Remove and close a session."""
    session = _file_sessions.get(session_id)
    if session is None or session.user_id != user_id:
        return False
    session.close()
    _file_sessions.pop(session_id, None)
    return True


def _cleanup_expired_sessions():
    """Remove expired sessions."""
    expired = [
        sid for sid, s in _file_sessions.items() if s.is_expired
    ]
    for sid in expired:
        _file_sessions[sid].close()
        del _file_sessions[sid]


class DuckDBLocalExecutor(WarehouseExecutor):
    """Execute queries against a local DuckDB session (file upload or .duckdb)."""

    def __init__(self, session: DuckDBFileSession):
        self._session = session

    def _run_query(self, sql: str) -> str:
        conn = self._session._conn
        if conn is None:
            raise RuntimeError("DuckDB session is closed")

        q = conn.execute(sql)
        if q.description is None:
            return "Query executed successfully (no results)."

        rows = q.fetchmany(MAX_ROWS)
        has_more = q.fetchone() is not None
        headers = [d[0] for d in q.description]

        out = tabulate(rows, headers=headers, tablefmt="pretty")

        if len(out) > MAX_CHARS:
            out = out[:MAX_CHARS]
            out += f"\n\n-- Output truncated at {MAX_CHARS:,} characters."
        elif has_more:
            out += f"\n\n-- Showing first {len(rows)} rows."

        return out

    def _run_query_raw(self, sql: str) -> list[tuple]:
        conn = self._session._conn
        if conn is None:
            raise RuntimeError("DuckDB session is closed")
        q = conn.execute(sql)
        return q.fetchall()

    async def execute_sql(self, sql: str) -> str:
        return await asyncio.to_thread(self._run_query, sql)

    async def list_datasets(self) -> str:
        return await asyncio.to_thread(
            self._run_query,
            "SELECT DISTINCT table_schema FROM information_schema.tables "
            "WHERE table_schema NOT IN ('information_schema', 'pg_catalog') "
            "ORDER BY table_schema",
        )

    async def list_tables(self, dataset: str) -> str:
        sql = (
            "SELECT table_name, table_type FROM information_schema.tables "
            f"WHERE table_schema = '{dataset}' ORDER BY table_name"
        )
        return await asyncio.to_thread(self._run_query, sql)

    async def get_table_schema(self, dataset: str, table: str) -> str:
        sql = (
            "SELECT column_name, data_type, is_nullable FROM information_schema.columns "
            f"WHERE table_schema = '{dataset}' AND table_name = '{table}' "
            "ORDER BY ordinal_position"
        )
        return await asyncio.to_thread(self._run_query, sql)

    async def get_schema_summary(self) -> str:
        """Build rich schema summary with sample data for prompt injection."""
        try:
            return await asyncio.to_thread(self._build_schema_summary)
        except Exception as e:
            logger.warning(f"DuckDB schema summary failed: {e}")
            return ""

    def _build_schema_summary(self) -> str:
        conn = self._session._conn
        if conn is None:
            return ""

        tables = conn.execute(
            "SELECT table_schema, table_name FROM information_schema.tables "
            "WHERE table_schema NOT IN ('information_schema', 'pg_catalog') "
            "ORDER BY table_schema, table_name"
        ).fetchall()

        parts = []

        for schema_name, table_name in tables[:50]:  # cap at 50 tables
            fqn = f'"{schema_name}"."{table_name}"' if schema_name != "main" else f'"{table_name}"'

            # Row count
            try:
                row_count = conn.execute(f"SELECT COUNT(*) FROM {fqn}").fetchone()[0]
            except Exception:
                row_count = "unknown"

            # Columns
            columns = conn.execute(
                "SELECT column_name, data_type FROM information_schema.columns "
                "WHERE table_schema = ? AND table_name = ? ORDER BY ordinal_position",
                [schema_name, table_name],
            ).fetchall()

            col_lines = "\n".join(f"  - {c[0]} ({c[1]})" for c in columns[:30])

            # Sample data
            sample_lines = ""
            try:
                sample = conn.execute(f"SELECT * FROM {fqn} LIMIT {MAX_SAMPLE_ROWS}").fetchall()
                if sample:
                    headers = [c[0] for c in columns[:30]]
                    header_line = " | ".join(headers)
                    data_lines = []
                    for row in sample:
                        vals = []
                        for v in row[:30]:
                            s = str(v) if v is not None else "NULL"
                            if len(s) > 50:
                                s = s[:47] + "..."
                            vals.append(s)
                        data_lines.append(" | ".join(vals))
                    sample_lines = (
                        f"\nSample data (first {len(sample)} rows):\n"
                        f"{header_line}\n" + "\n".join(data_lines)
                    )
            except Exception:
                pass

            display_name = f"{schema_name}.{table_name}" if schema_name != "main" else table_name
            parts.append(
                f"Table: {display_name} ({row_count:,} rows)\n"
                f"Columns:\n{col_lines}{sample_lines}"
            )

        return "\n\n".join(parts)
