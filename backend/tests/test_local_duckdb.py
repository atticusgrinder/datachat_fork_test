"""Tests for the per-user persistent LocalDuckDB."""

import asyncio
import importlib
import os
import sys

import pytest


@pytest.fixture(autouse=True)
def _real_duckdb_module():
    """Other tests in the suite stub sys.modules['duckdb'] with a MagicMock and
    don't restore it. These tests rely on real DuckDB."""
    sys.modules.pop("duckdb", None)
    importlib.import_module("duckdb")
    yield


@pytest.fixture
def storage_dir(tmp_path, monkeypatch):
    """Point LOCAL_DUCKDB_DIR at a fresh temp directory for each test."""
    storage = tmp_path / "local_duckdb_storage"
    storage.mkdir()
    monkeypatch.setattr("app.services.local_duckdb_service.LOCAL_DUCKDB_DIR", str(storage))
    return str(storage)


@pytest.fixture
def csv_file_factory(tmp_path):
    counter = {"i": 0}

    def _make(name: str, header: list[str], rows: list[list]) -> str:
        counter["i"] += 1
        path = tmp_path / f"{counter['i']:03d}_{name}"
        with open(path, "w", encoding="utf-8") as f:
            f.write(",".join(header) + "\n")
            for row in rows:
                f.write(",".join(str(c) for c in row) + "\n")
        return str(path)

    return _make


class TestLocalDuckDBService:
    def test_first_upload_creates_db_and_table(self, db_session, test_user, storage_dir, csv_file_factory):
        from app.services import local_duckdb_service

        upload = csv_file_factory("customers.csv", ["id", "name"], [[1, "Alice"], [2, "Bob"]])
        table_row = asyncio.run(
            local_duckdb_service.add_uploaded_file(
                db_session, test_user.id, upload, "customers.csv", "excel_csv"
            )
        )

        assert table_row.table_name == "customers"
        assert table_row.row_count == 2
        assert table_row.source_type == "excel_csv"

        local_db = local_duckdb_service.get_user_db(db_session, test_user.id)
        assert local_db is not None
        assert os.path.exists(local_db.file_path)
        assert local_db.file_path.startswith(storage_dir)
        assert len(local_db.tables) == 1

    def test_second_upload_appends_to_same_db(self, db_session, test_user, storage_dir, csv_file_factory):
        from app.services import local_duckdb_service

        first = csv_file_factory("customers.csv", ["id", "name"], [[1, "Alice"]])
        second = csv_file_factory(
            "orders.csv", ["order_id", "customer_id", "amount"], [[100, 1, 50]]
        )

        asyncio.run(local_duckdb_service.add_uploaded_file(
            db_session, test_user.id, first, "customers.csv", "excel_csv"
        ))
        asyncio.run(local_duckdb_service.add_uploaded_file(
            db_session, test_user.id, second, "orders.csv", "excel_csv"
        ))

        local_db = local_duckdb_service.get_user_db(db_session, test_user.id)
        assert len(local_db.tables) == 2
        assert {t.table_name for t in local_db.tables} == {"customers", "orders"}

    def test_filename_collision_uses_unique_table_name(self, db_session, test_user, storage_dir, csv_file_factory):
        from app.services import local_duckdb_service

        first = csv_file_factory("data.csv", ["x"], [[1]])
        second = csv_file_factory("data.csv", ["y"], [[2]])

        asyncio.run(local_duckdb_service.add_uploaded_file(
            db_session, test_user.id, first, "data.csv", "excel_csv"
        ))
        asyncio.run(local_duckdb_service.add_uploaded_file(
            db_session, test_user.id, second, "data.csv", "excel_csv"
        ))

        local_db = local_duckdb_service.get_user_db(db_session, test_user.id)
        names = {t.table_name for t in local_db.tables}
        assert names == {"data", "data_2"}

    def test_drop_table_removes_from_db_and_disk(self, db_session, test_user, storage_dir, csv_file_factory):
        from app.connections.local_duckdb_persistent import list_existing_table_names
        from app.services import local_duckdb_service

        upload = csv_file_factory("customers.csv", ["id"], [[1]])
        table_row = asyncio.run(local_duckdb_service.add_uploaded_file(
            db_session, test_user.id, upload, "customers.csv", "excel_csv"
        ))
        local_db = local_duckdb_service.get_user_db(db_session, test_user.id)

        removed = asyncio.run(local_duckdb_service.drop_table(db_session, test_user.id, table_row.id))
        assert removed is True

        local_db = local_duckdb_service.get_user_db(db_session, test_user.id)
        assert len(local_db.tables) == 0
        assert "customers" not in list_existing_table_names(local_db.file_path)

    def test_delete_user_db_removes_file_and_rows(self, db_session, test_user, storage_dir, csv_file_factory):
        from app.services import local_duckdb_service

        upload = csv_file_factory("customers.csv", ["id"], [[1]])
        asyncio.run(local_duckdb_service.add_uploaded_file(
            db_session, test_user.id, upload, "customers.csv", "excel_csv"
        ))
        local_db = local_duckdb_service.get_user_db(db_session, test_user.id)
        path = local_db.file_path

        deleted = local_duckdb_service.delete_user_db(db_session, test_user.id)
        assert deleted is True
        assert not os.path.exists(path)
        assert local_duckdb_service.get_user_db(db_session, test_user.id) is None


class TestLocalDuckDBExecutor:
    def test_query_works(self, db_session, test_user, storage_dir, csv_file_factory):
        from app.connections.local_duckdb_persistent import LocalDuckDBExecutor
        from app.services import local_duckdb_service

        upload = csv_file_factory("nums.csv", ["n"], [[1], [2], [3]])
        asyncio.run(local_duckdb_service.add_uploaded_file(
            db_session, test_user.id, upload, "nums.csv", "excel_csv"
        ))
        local_db = local_duckdb_service.get_user_db(db_session, test_user.id)

        ex = LocalDuckDBExecutor(local_db.file_path)
        try:
            result = asyncio.run(ex.execute_sql("SELECT SUM(n) AS total FROM nums"))
            assert "6" in result
        finally:
            ex.close()

    def test_cross_file_join(self, db_session, test_user, storage_dir, csv_file_factory):
        from app.connections.local_duckdb_persistent import LocalDuckDBExecutor
        from app.services import local_duckdb_service

        cust = csv_file_factory("customers.csv", ["id", "name"], [[1, "Alice"], [2, "Bob"]])
        ords = csv_file_factory(
            "orders.csv", ["order_id", "customer_id", "amount"],
            [[100, 1, 50], [101, 2, 75], [102, 1, 25]],
        )

        asyncio.run(local_duckdb_service.add_uploaded_file(
            db_session, test_user.id, cust, "customers.csv", "excel_csv"
        ))
        asyncio.run(local_duckdb_service.add_uploaded_file(
            db_session, test_user.id, ords, "orders.csv", "excel_csv"
        ))
        local_db = local_duckdb_service.get_user_db(db_session, test_user.id)

        ex = LocalDuckDBExecutor(local_db.file_path)
        try:
            result = asyncio.run(ex.execute_sql(
                "SELECT c.name, SUM(o.amount) AS total "
                "FROM customers c JOIN orders o ON c.id = o.customer_id "
                "GROUP BY c.name ORDER BY c.name"
            ))
            assert "Alice" in result and "75" in result
            assert "Bob" in result
        finally:
            ex.close()

    def test_persistence_across_executor_instances(self, db_session, test_user, storage_dir, csv_file_factory):
        """Open the same on-disk DuckDB twice with a fresh executor each time —
        the table loaded by the first run is still queryable by the second."""
        from app.connections.local_duckdb_persistent import LocalDuckDBExecutor
        from app.services import local_duckdb_service

        upload = csv_file_factory("p.csv", ["v"], [[42]])
        asyncio.run(local_duckdb_service.add_uploaded_file(
            db_session, test_user.id, upload, "p.csv", "excel_csv"
        ))
        local_db = local_duckdb_service.get_user_db(db_session, test_user.id)
        path = local_db.file_path

        ex1 = LocalDuckDBExecutor(path)
        ex1.close()

        ex2 = LocalDuckDBExecutor(path)
        try:
            result = asyncio.run(ex2.execute_sql("SELECT v FROM p"))
            assert "42" in result
        finally:
            ex2.close()

    def test_schema_summary_includes_all_tables(self, db_session, test_user, storage_dir, csv_file_factory):
        from app.connections.local_duckdb_persistent import LocalDuckDBExecutor
        from app.services import local_duckdb_service

        for name, header, rows in [
            ("customers.csv", ["id", "name"], [[1, "Alice"]]),
            ("orders.csv", ["oid", "cid"], [[10, 1]]),
        ]:
            upload = csv_file_factory(name, header, rows)
            asyncio.run(local_duckdb_service.add_uploaded_file(
                db_session, test_user.id, upload, name, "excel_csv"
            ))

        local_db = local_duckdb_service.get_user_db(db_session, test_user.id)
        ex = LocalDuckDBExecutor(local_db.file_path)
        try:
            summary = asyncio.run(ex.get_schema_summary())
            assert "customers" in summary
            assert "orders" in summary
        finally:
            ex.close()
