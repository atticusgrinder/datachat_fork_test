"""Tests for unified context files (replaces test_memory.py)."""

from unittest.mock import patch

import pytest

from app.services import context_service


# Enable DISABLE_AUTH for API tests
@pytest.fixture(autouse=True)
def enable_disable_auth():
    with patch("app.core.dependencies.DISABLE_AUTH", True):
        yield


class TestContextService:
    """Unit tests for context_service functions."""

    def test_list_files_empty(self, db_session, test_user):
        result = context_service.list_files(db_session, test_user.id)
        assert result == []

    def test_write_and_read_file(self, db_session, test_user):
        cf = context_service.write_file(db_session, test_user.id, "context.md", "hello world")
        assert cf.filename == "context.md"
        assert cf.content == "hello world"
        assert cf.source == "user"

        read = context_service.read_file(db_session, test_user.id, "context.md")
        assert read is not None
        assert read.content == "hello world"

    def test_write_file_update_existing(self, db_session, test_user):
        context_service.write_file(db_session, test_user.id, "context.md", "v1")
        cf = context_service.write_file(db_session, test_user.id, "context.md", "v2")
        assert cf.content == "v2"

        files = context_service.list_files(db_session, test_user.id)
        assert len(files) == 1

    def test_write_file_size_limit(self, db_session, test_user):
        big_content = "x" * (100 * 1024 + 1)
        with pytest.raises(ValueError, match="maximum size"):
            context_service.write_file(db_session, test_user.id, "big.md", big_content)

    def test_write_file_count_limit(self, db_session, test_user):
        for i in range(10):
            context_service.write_file(db_session, test_user.id, f"file{i}.md", f"content {i}")

        with pytest.raises(ValueError, match="Maximum of 10"):
            context_service.write_file(db_session, test_user.id, "file10.md", "too many")

    def test_write_file_count_limit_update_ok(self, db_session, test_user):
        for i in range(10):
            context_service.write_file(db_session, test_user.id, f"file{i}.md", f"content {i}")

        cf = context_service.write_file(db_session, test_user.id, "file0.md", "updated")
        assert cf.content == "updated"

    def test_delete_file(self, db_session, test_user):
        context_service.write_file(db_session, test_user.id, "test.md", "hello")
        assert context_service.delete_file(db_session, test_user.id, "test.md") is True
        assert context_service.read_file(db_session, test_user.id, "test.md") is None

    def test_delete_nonexistent(self, db_session, test_user):
        assert context_service.delete_file(db_session, test_user.id, "nope.md") is False

    def test_cannot_edit_integration_file(self, db_session, test_user):
        """User files with source='integration' cannot be edited via write_file."""
        from app.models.context import ContextFile
        import uuid
        cf = ContextFile(
            id=str(uuid.uuid4()),
            user_id=test_user.id,
            filename="dbt-project.yml",
            content="# dbt",
            source="integration",
        )
        db_session.add(cf)
        db_session.commit()

        with pytest.raises(ValueError, match="integration-synced"):
            context_service.write_file(db_session, test_user.id, "dbt-project.yml", "edited")

    def test_cannot_delete_integration_file(self, db_session, test_user):
        from app.models.context import ContextFile
        import uuid
        cf = ContextFile(
            id=str(uuid.uuid4()),
            user_id=test_user.id,
            filename="dbt-project.yml",
            content="# dbt",
            source="integration",
        )
        db_session.add(cf)
        db_session.commit()

        with pytest.raises(ValueError, match="integration-synced"):
            context_service.delete_file(db_session, test_user.id, "dbt-project.yml")

    def test_get_context_empty(self, db_session, test_user):
        result = context_service.get_context(db_session, test_user.id)
        assert result == ""

    def test_get_context_combines_all(self, db_session, test_user):
        context_service.write_file(db_session, test_user.id, "context.md", "User context")
        # Add an integration file directly
        from app.models.context import ContextFile
        import uuid
        cf = ContextFile(
            id=str(uuid.uuid4()),
            user_id=test_user.id,
            filename="dbt-myproject.yml",
            content="# dbt models",
            source="integration",
        )
        db_session.add(cf)
        db_session.commit()

        result = context_service.get_context(db_session, test_user.id)
        assert "### context.md" in result
        assert "User context" in result
        assert "### dbt-myproject.yml" in result
        assert "# dbt models" in result

    def test_ensure_default_context_creates_single(self, db_session, test_user):
        files = context_service.ensure_default_context(db_session, test_user.id)
        user_files = [f for f in files if f.source == "user"]
        assert len(user_files) == 1
        assert user_files[0].filename == "context.md"

    def test_ensure_default_context_noop_if_exists(self, db_session, test_user):
        context_service.write_file(db_session, test_user.id, "custom.md", "my file")
        files = context_service.ensure_default_context(db_session, test_user.id)
        user_files = [f for f in files if f.source == "user"]
        assert len(user_files) == 1
        assert user_files[0].filename == "custom.md"

    def test_upsert_integration_context(self, db_session, test_user):
        cf = context_service.upsert_integration_context(
            db_session, test_user.id, "int-123", "dbt", "myproject", "# dbt content"
        )
        assert cf.filename == "dbt-myproject.yml"
        assert cf.source == "integration"
        assert cf.integration_id == "int-123"

        # Update
        cf2 = context_service.upsert_integration_context(
            db_session, test_user.id, "int-123", "dbt", "myproject", "# updated"
        )
        assert cf2.id == cf.id
        assert cf2.content == "# updated"

    def test_upsert_integration_context_omni(self, db_session, test_user):
        cf = context_service.upsert_integration_context(
            db_session, test_user.id, "int-456", "omni", "myshop", "# omni content"
        )
        assert cf.filename == "omni-myshop.yml"
        assert cf.source == "integration"
        assert cf.integration_id == "int-456"

    def test_upsert_integration_context_strips_redundant_type(self, db_session, test_user):
        # Trailing -omni in the name should be stripped
        cf = context_service.upsert_integration_context(
            db_session, test_user.id, "int-7", "omni", "retailflow-omni", "# content"
        )
        assert cf.filename == "omni-retailflow.yml"

        # Leading dbt_ prefix should also be stripped
        cf2 = context_service.upsert_integration_context(
            db_session, test_user.id, "int-8", "dbt", "dbt_retailflow", "# content"
        )
        assert cf2.filename == "dbt-retailflow.yml"

        # Names without the prefix/suffix are left alone
        cf3 = context_service.upsert_integration_context(
            db_session, test_user.id, "int-9", "omni", "shop", "# content"
        )
        assert cf3.filename == "omni-shop.yml"

    def test_delete_integration_context(self, db_session, test_user):
        context_service.upsert_integration_context(
            db_session, test_user.id, "int-123", "dbt", "myproject", "# dbt"
        )
        context_service.delete_integration_context(db_session, "int-123")

        files = context_service.list_files(db_session, test_user.id)
        assert len(files) == 0

    def test_user_isolation(self, db_session, test_user, admin_user):
        context_service.write_file(db_session, test_user.id, "context.md", "user data")
        context_service.write_file(db_session, admin_user.id, "context.md", "admin data")

        user_file = context_service.read_file(db_session, test_user.id, "context.md")
        admin_file = context_service.read_file(db_session, admin_user.id, "context.md")
        assert user_file.content == "user data"
        assert admin_file.content == "admin data"


class TestContextAPI:
    """Integration tests for context API endpoints."""

    async def test_list_creates_defaults(self, authed_client):
        resp = await authed_client.get("/api/context")
        assert resp.status_code == 200
        data = resp.json()
        user_files = [f for f in data["files"] if f["source"] == "user"]
        assert len(user_files) == 1
        assert user_files[0]["filename"] == "context.md"

    async def test_get_file(self, authed_client):
        await authed_client.get("/api/context")
        resp = await authed_client.get("/api/context/context.md")
        assert resp.status_code == 200
        assert resp.json()["filename"] == "context.md"
        assert resp.json()["source"] == "user"

    async def test_get_nonexistent(self, authed_client):
        resp = await authed_client.get("/api/context/nope.md")
        assert resp.status_code == 404

    async def test_put_create_file(self, authed_client):
        resp = await authed_client.put("/api/context/notes.md", json={"content": "my notes"})
        assert resp.status_code == 200
        assert resp.json()["filename"] == "notes.md"
        assert resp.json()["content"] == "my notes"

    async def test_put_update_file(self, authed_client):
        await authed_client.put("/api/context/notes.md", json={"content": "v1"})
        resp = await authed_client.put("/api/context/notes.md", json={"content": "v2"})
        assert resp.status_code == 200
        assert resp.json()["content"] == "v2"

    async def test_put_invalid_filename(self, authed_client):
        resp = await authed_client.put("/api/context/bad file!.md", json={"content": "x"})
        assert resp.status_code == 400

    async def test_put_too_large(self, authed_client):
        big = "x" * (100 * 1024 + 1)
        resp = await authed_client.put("/api/context/big.md", json={"content": big})
        assert resp.status_code == 400

    async def test_delete_file(self, authed_client):
        await authed_client.put("/api/context/temp.md", json={"content": "tmp"})
        resp = await authed_client.delete("/api/context/temp.md")
        assert resp.status_code == 200
        assert resp.json()["success"] is True

        resp = await authed_client.get("/api/context/temp.md")
        assert resp.status_code == 404

    async def test_delete_nonexistent(self, authed_client):
        resp = await authed_client.delete("/api/context/nope.md")
        assert resp.status_code == 404

    async def test_yml_filename_accepted(self, authed_client):
        resp = await authed_client.put("/api/context/dbt-project.yml", json={"content": "# dbt"})
        assert resp.status_code == 200
        assert resp.json()["filename"] == "dbt-project.yml"

    async def test_filename_validation(self, authed_client):
        resp = await authed_client.put("/api/context/noext", json={"content": "x"})
        assert resp.status_code == 400

        resp = await authed_client.put("/api/context/has space.md", json={"content": "x"})
        assert resp.status_code == 400

        resp = await authed_client.put("/api/context/bad@file.md", json={"content": "x"})
        assert resp.status_code == 400
