"""Tests for multi-file DuckDB sessions and the file-backed system prompt."""

import asyncio
import importlib
import os
import sys
import tempfile

import pytest


@pytest.fixture(autouse=True)
def _real_duckdb_module():
    """Other tests in the suite (test_connections.py) replace sys.modules['duckdb']
    with a MagicMock and don't restore it. These tests rely on real DuckDB, so
    re-import the real module before each test."""
    sys.modules.pop("duckdb", None)
    importlib.import_module("duckdb")
    yield


@pytest.fixture
def csv_file_factory(tmp_path):
    """Factory: create a CSV file with given header + rows; return path.

    Writes to a unique temp path per call so that callers can pass the same
    logical filename (e.g. "data.csv") twice without one overwriting the other.
    """
    counter = {"i": 0}

    def _make(name: str, header: list[str], rows: list[list]) -> str:
        counter["i"] += 1
        # Caller may pass the same `name` twice (testing collision handling);
        # disambiguate the on-disk path so neither file clobbers the other.
        path = tmp_path / f"{counter['i']:03d}_{name}"
        with open(path, "w", encoding="utf-8") as f:
            f.write(",".join(header) + "\n")
            for row in rows:
                f.write(",".join(str(c) for c in row) + "\n")
        return str(path)

    return _make


class TestFilenameToTableName:
    def test_basic(self):
        from app.connections.duckdb_local import _filename_to_table_name
        assert _filename_to_table_name("Sales Q1.xlsx", set()) == "sales_q1"

    def test_strips_special_chars(self):
        from app.connections.duckdb_local import _filename_to_table_name
        assert _filename_to_table_name("My-File @2024!.csv", set()) == "my_file_2024"

    def test_handles_leading_digits(self):
        from app.connections.duckdb_local import _filename_to_table_name
        assert _filename_to_table_name("2024_report.csv", set()) == "t_2024_report"

    def test_uniqueness(self):
        from app.connections.duckdb_local import _filename_to_table_name
        assert _filename_to_table_name("data.csv", {"data"}) == "data_2"
        assert _filename_to_table_name("data.csv", {"data", "data_2"}) == "data_3"

    def test_only_special_chars(self):
        from app.connections.duckdb_local import _filename_to_table_name
        # All non-alphanumeric → falls back to "data"
        assert _filename_to_table_name("---.csv", set()) == "data"


class TestMultiFileSession:
    def test_single_file_creates_one_table(self, csv_file_factory):
        from app.connections.duckdb_local import create_file_upload_session

        path = csv_file_factory(
            "customers.csv",
            ["id", "name"],
            [[1, "Alice"], [2, "Bob"]],
        )
        session = asyncio.run(
            create_file_upload_session("user-1", path, "customers.csv", "excel_csv")
        )
        try:
            assert len(session._files) == 1
            assert session._files[0]["table_name"] == "customers"
            assert session._files[0]["row_count"] == 2
            md = session.metadata
            assert md is not None
            assert md["filename"] == "customers.csv"
            assert md["row_count"] == 2
            assert len(md["tables"]) == 1
        finally:
            session.close()

    def test_append_creates_second_table(self, csv_file_factory):
        from app.connections.duckdb_local import (
            append_file_to_session,
            create_file_upload_session,
        )

        customers = csv_file_factory(
            "customers.csv",
            ["id", "name"],
            [[1, "Alice"], [2, "Bob"]],
        )
        orders = csv_file_factory(
            "orders.csv",
            ["order_id", "customer_id", "amount"],
            [[100, 1, 50], [101, 2, 75], [102, 1, 25]],
        )
        session = asyncio.run(
            create_file_upload_session("user-1", customers, "customers.csv", "excel_csv")
        )
        try:
            asyncio.run(append_file_to_session(session, orders, "orders.csv"))
            assert len(session._files) == 2
            assert {f["table_name"] for f in session._files} == {"customers", "orders"}

            # Cross-file join works
            result = session._conn.execute(
                "SELECT c.name, SUM(o.amount) "
                "FROM customers c JOIN orders o ON c.id = o.customer_id "
                "GROUP BY c.name ORDER BY c.name"
            ).fetchall()
            assert result == [("Alice", 75), ("Bob", 75)]
        finally:
            session.close()

    def test_append_collision_uses_unique_name(self, csv_file_factory):
        from app.connections.duckdb_local import (
            append_file_to_session,
            create_file_upload_session,
        )

        first = csv_file_factory("data.csv", ["x"], [[1]])
        second = csv_file_factory("data.csv", ["y"], [[2]])
        session = asyncio.run(
            create_file_upload_session("user-1", first, "data.csv", "excel_csv")
        )
        try:
            asyncio.run(append_file_to_session(session, second, "data.csv"))
            names = {f["table_name"] for f in session._files}
            assert names == {"data", "data_2"}
        finally:
            session.close()

    def test_append_to_duckdb_session_rejected(self, tmp_path, csv_file_factory):
        """Cannot append to a .duckdb-backed session — they're read-only file-mounts."""
        import duckdb

        from app.connections.duckdb_local import (
            DuckDBFileSession,
            append_file_to_session,
        )

        # Build a real .duckdb file to back the session
        db_path = str(tmp_path / "fixture.duckdb")
        c = duckdb.connect(db_path)
        c.execute("CREATE TABLE t (a INT)")
        c.execute("INSERT INTO t VALUES (1)")
        c.close()

        session = DuckDBFileSession(
            session_id="s",
            user_id="u",
            filename="fixture.duckdb",
            source_type="duckdb",
        )
        # Don't bother fully wiring the .duckdb open — we just need source_type="duckdb"
        new_csv = csv_file_factory("more.csv", ["x"], [[1]])
        with pytest.raises(ValueError):
            asyncio.run(append_file_to_session(session, new_csv, "more.csv"))


class TestFileSystemPrompt:
    def test_single_file_prompt(self):
        from app.services.chat_service import build_file_system_prompt

        prompt = build_file_system_prompt(
            filename="sales.csv",
            source_type="excel_csv",
            schema_summary="Table: sales (10 rows)\nColumns:\n  - id (INT)",
            filenames=["sales.csv"],
        )
        assert "Cross-file JOIN" not in prompt
        assert "sales.csv" in prompt

    def test_multi_file_prompt_mentions_joins(self):
        from app.services.chat_service import build_file_system_prompt

        prompt = build_file_system_prompt(
            filename="customers.csv",
            source_type="excel_csv",
            schema_summary="Table: customers ...\nTable: orders ...",
            filenames=["customers.csv", "orders.csv"],
        )
        assert "Cross-file JOIN" in prompt
        assert "customers.csv" in prompt
        assert "orders.csv" in prompt
        assert "2 uploaded files" in prompt


class TestModelsRegistry:
    def test_opus_4_7_registered(self):
        from app.core.config import MODELS, ALLOWED_MODELS, CLAUDE_PRICING

        assert "claude-opus-4-7" in MODELS
        assert MODELS["claude-opus-4-7"]["display_name"] == "Opus 4.7"
        assert "claude-opus-4-7" in ALLOWED_MODELS
        assert "claude-opus-4-7" in CLAUDE_PRICING

    def test_default_remains_sonnet_4_6(self):
        from app.core.config import DEFAULT_MODEL
        assert DEFAULT_MODEL == "claude-sonnet-4-6"

    def test_existing_models_preserved(self):
        from app.core.config import MODELS
        assert "claude-sonnet-4-6" in MODELS
        assert "claude-opus-4-6" in MODELS


