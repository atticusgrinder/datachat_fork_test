"""Tests for the integrations feature (models, dbt parser, service, API)."""

import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Env vars must be set before importing app modules
os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("ENCRYPTION_KEY", "test-encryption-key")
os.environ.setdefault("DISABLE_AUTH", "false")
os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-test-key")
os.environ.setdefault("CLERK_SECRET_KEY", "")
os.environ.setdefault("CLERK_PUBLISHABLE_KEY", "")

from app.core.security import encrypt_credentials, decrypt_credentials
from app.models.integration import Integration, IntegrationSync
from app.models.context import ContextFile
from app.services.dbt_parser import parse_manifest
from app.services.omni_parser import parse_repo as parse_omni_repo
from app.services import integration_service


FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture()
def sample_manifest():
    with open(FIXTURES_DIR / "sample_manifest.json") as f:
        return json.load(f)


# ─── dbt Parser Tests ───────────────────────────────────────────────────────


class TestDbtParser:
    def test_parse_models(self, sample_manifest):
        results = parse_manifest(sample_manifest)
        models = [r for r in results if r["metadata_type"] == "model"]
        assert len(models) == 3
        names = {m["name"] for m in models}
        assert names == {"customers", "orders", "stg_customers"}

    def test_parse_model_columns(self, sample_manifest):
        results = parse_manifest(sample_manifest)
        customers = next(r for r in results if r["name"] == "customers" and r["metadata_type"] == "model")
        assert len(customers["columns"]) == 7
        col_names = {c["name"] for c in customers["columns"]}
        assert "customer_id" in col_names
        assert "customer_lifetime_value" in col_names

    def test_parse_model_description(self, sample_manifest):
        results = parse_manifest(sample_manifest)
        customers = next(r for r in results if r["name"] == "customers" and r["metadata_type"] == "model")
        assert "basic information about a customer" in customers["description"]

    def test_parse_model_refs(self, sample_manifest):
        results = parse_manifest(sample_manifest)
        customers = next(r for r in results if r["name"] == "customers" and r["metadata_type"] == "model")
        assert len(customers["relationships"]["refs"]) == 3
        assert len(customers["relationships"]["depends_on"]["nodes"]) == 3

    def test_parse_model_tags(self, sample_manifest):
        results = parse_manifest(sample_manifest)
        customers = next(r for r in results if r["name"] == "customers" and r["metadata_type"] == "model")
        assert "pii" in customers["tags"]
        assert "daily" in customers["tags"]

    def test_parse_model_materialization(self, sample_manifest):
        results = parse_manifest(sample_manifest)
        customers = next(r for r in results if r["name"] == "customers" and r["metadata_type"] == "model")
        assert customers["meta"]["materialized"] == "table"

        stg = next(r for r in results if r["name"] == "stg_customers")
        assert stg["meta"]["materialized"] == "view"

    def test_parse_sources(self, sample_manifest):
        results = parse_manifest(sample_manifest)
        sources = [r for r in results if r["metadata_type"] == "source"]
        assert len(sources) == 1
        src = sources[0]
        assert src["name"] == "customers"
        assert src["schema_name"] == "raw_data"
        assert src["database"] == "analytics"
        assert src["meta"]["source_name"] == "raw"
        assert src["meta"]["loader"] == "postgres"

    def test_parse_source_columns(self, sample_manifest):
        results = parse_manifest(sample_manifest)
        src = next(r for r in results if r["metadata_type"] == "source")
        assert len(src["columns"]) == 3

    def test_parse_column_tests(self, sample_manifest):
        results = parse_manifest(sample_manifest)
        orders = next(r for r in results if r["name"] == "orders" and r["metadata_type"] == "model")
        status_col = next(c for c in orders["columns"] if c["name"] == "status")
        assert "accepted_values" in status_col["tests"]

    def test_parse_empty_manifest(self):
        results = parse_manifest({"nodes": {}, "sources": {}})
        assert results == []

    def test_parse_manifest_no_sources_key(self):
        results = parse_manifest({"nodes": {}})
        assert results == []


# ─── Omni Parser Tests ──────────────────────────────────────────────────────


class TestOmniParser:
    def test_parse_view(self, tmp_path):
        views_dir = tmp_path / "views"
        views_dir.mkdir()
        (views_dir / "customers.view").write_text(
            "name: customers\n"
            "table_name: customers\n"
            "description: Customer records\n"
            "dimensions:\n"
            "  - name: id\n"
            "    type: number\n"
            "  - name: email\n"
            "    type: string\n"
            "measures:\n"
            "  - name: count\n"
            "    aggregate_type: count\n"
        )
        results = parse_omni_repo(tmp_path)
        assert len(results) == 1
        view = results[0]
        assert view["metadata_type"] == "view"
        assert view["name"] == "customers"
        assert view["description"] == "Customer records"
        assert view["meta"]["table_name"] == "customers"
        assert len(view["columns"]) == 3
        kinds = {c["name"]: c["kind"] for c in view["columns"]}
        assert kinds == {"id": "dimension", "email": "dimension", "count": "measure"}

    def test_parse_model_and_topic(self, tmp_path):
        (tmp_path / "models").mkdir()
        (tmp_path / "topics").mkdir()
        (tmp_path / "models" / "shop.model").write_text(
            "name: shop\nconnection: warehouse\nviews:\n  - customers\n  - orders\n"
        )
        (tmp_path / "topics" / "orders.topic").write_text(
            "name: orders\nbase_view: orders\n"
        )
        results = parse_omni_repo(tmp_path)
        types = {r["metadata_type"] for r in results}
        assert types == {"model", "topic"}

    def test_skip_non_omni_files(self, tmp_path):
        (tmp_path / "README.md").write_text("# Repo")
        (tmp_path / "random.yml").write_text("foo: bar")
        results = parse_omni_repo(tmp_path)
        assert results == []

    def test_empty_repo(self, tmp_path):
        assert parse_omni_repo(tmp_path) == []


# ─── Integration Service Tests ──────────────────────────────────────────────


class TestIntegrationService:
    def test_create_integration(self, db_session, test_user):
        config = {"repo_url": "https://github.com/test/repo.git", "branch": "main"}
        integration = integration_service.create_integration(
            db=db_session,
            user_id=test_user.id,
            integration_type="dbt",
            name="Test dbt",
            config=config,
        )
        assert integration.id
        assert integration.user_id == test_user.id
        assert integration.integration_type == "dbt"
        assert integration.name == "Test dbt"
        assert integration.connection_status == "pending"
        # Verify config is encrypted
        decrypted = decrypt_credentials(integration.config_encrypted)
        assert decrypted["repo_url"] == config["repo_url"]

    def test_create_integration_unsupported_type(self, db_session, test_user):
        with pytest.raises(ValueError, match="Unsupported"):
            integration_service.create_integration(
                db=db_session, user_id=test_user.id,
                integration_type="unknown", name="Test", config={"repo_url": "https://x.com"},
            )

    def test_create_integration_missing_repo_url(self, db_session, test_user):
        with pytest.raises(ValueError, match="repo_url"):
            integration_service.create_integration(
                db=db_session, user_id=test_user.id,
                integration_type="dbt", name="Test", config={},
            )

    def test_list_integrations(self, db_session, test_user):
        config = {"repo_url": "https://github.com/test/repo.git"}
        integration_service.create_integration(db_session, test_user.id, "dbt", "First", config)
        integration_service.create_integration(db_session, test_user.id, "dbt", "Second", config)
        result = integration_service.list_integrations(db_session, test_user.id)
        assert len(result) == 2

    def test_list_integrations_user_isolation(self, db_session, test_user, admin_user):
        config = {"repo_url": "https://github.com/test/repo.git"}
        integration_service.create_integration(db_session, test_user.id, "dbt", "User1", config)
        integration_service.create_integration(db_session, admin_user.id, "dbt", "Admin1", config)
        user_list = integration_service.list_integrations(db_session, test_user.id)
        admin_list = integration_service.list_integrations(db_session, admin_user.id)
        assert len(user_list) == 1
        assert user_list[0].name == "User1"
        assert len(admin_list) == 1
        assert admin_list[0].name == "Admin1"

    def test_get_integration(self, db_session, test_user):
        config = {"repo_url": "https://github.com/test/repo.git"}
        created = integration_service.create_integration(db_session, test_user.id, "dbt", "Test", config)
        fetched = integration_service.get_integration(db_session, test_user.id, created.id)
        assert fetched is not None
        assert fetched.id == created.id

    def test_get_integration_wrong_user(self, db_session, test_user, admin_user):
        config = {"repo_url": "https://github.com/test/repo.git"}
        created = integration_service.create_integration(db_session, test_user.id, "dbt", "Test", config)
        fetched = integration_service.get_integration(db_session, admin_user.id, created.id)
        assert fetched is None

    def test_delete_integration(self, db_session, test_user):
        config = {"repo_url": "https://github.com/test/repo.git"}
        created = integration_service.create_integration(db_session, test_user.id, "dbt", "Test", config)
        assert integration_service.delete_integration(db_session, test_user.id, created.id)
        assert integration_service.get_integration(db_session, test_user.id, created.id) is None

    def test_delete_integration_not_found(self, db_session, test_user):
        assert not integration_service.delete_integration(db_session, test_user.id, "nonexistent")

    def test_delete_integration_cascades_context_files(self, db_session, test_user):
        config = {"repo_url": "https://github.com/test/repo.git"}
        created = integration_service.create_integration(db_session, test_user.id, "dbt", "Test", config)
        # Manually add a context file for this integration
        cf = ContextFile(
            id=str(uuid.uuid4()),
            user_id=test_user.id,
            filename="dbt-Test.yml",
            content="# dbt",
            source="integration",
            integration_id=created.id,
        )
        db_session.add(cf)
        db_session.commit()
        assert db_session.query(ContextFile).filter(ContextFile.integration_id == created.id).count() == 1
        integration_service.delete_integration(db_session, test_user.id, created.id)
        assert db_session.query(ContextFile).filter(ContextFile.integration_id == created.id).count() == 0


# ─── Metadata and Context Tests ─────────────────────────────────────────────


class TestMetadataFormatting:
    def test_format_metadata_as_markdown(self, sample_manifest):
        parsed = parse_manifest(sample_manifest)
        context = integration_service._format_metadata_as_markdown(parsed)
        assert "# dbt Project Context" in context
        assert "## Models" in context
        assert "## Sources" in context
        assert "customers" in context
        assert "orders" in context

    def test_format_metadata_includes_columns(self, sample_manifest):
        parsed = parse_manifest(sample_manifest)
        context = integration_service._format_metadata_as_markdown(parsed)
        assert "customer_id" in context
        assert "customer_lifetime_value" in context

    def test_format_metadata_includes_descriptions(self, sample_manifest):
        parsed = parse_manifest(sample_manifest)
        context = integration_service._format_metadata_as_markdown(parsed)
        assert "basic information about a customer" in context

    def test_format_metadata_empty(self):
        context = integration_service._format_metadata_as_markdown([])
        assert context == ""


# ─── Sync Tests ──────────────────────────────────────────────────────────────


class TestSyncIntegration:
    @patch("app.services.integration_service._clone_and_find_manifest")
    def test_sync_success(self, mock_clone, db_session, test_user, sample_manifest):
        mock_clone.return_value = sample_manifest
        config = {"repo_url": "https://github.com/test/repo.git"}
        integration = integration_service.create_integration(
            db_session, test_user.id, "dbt", "Test", config,
        )
        sync = integration_service.sync_integration(db_session, test_user.id, integration.id)
        assert sync.status == "completed"
        assert sync.metadata_count == 4  # 3 models + 1 source
        assert sync.error_message is None

        # Check integration status updated
        db_session.refresh(integration)
        assert integration.connection_status == "connected"
        assert integration.last_synced_at is not None

    @patch("app.services.integration_service._clone_and_find_manifest")
    def test_sync_failure(self, mock_clone, db_session, test_user):
        mock_clone.side_effect = RuntimeError("Repository or branch not found. Check the URL and branch name.")
        config = {"repo_url": "https://github.com/test/nonexistent.git"}
        integration = integration_service.create_integration(
            db_session, test_user.id, "dbt", "Bad", config,
        )
        sync = integration_service.sync_integration(db_session, test_user.id, integration.id)
        assert sync.status == "failed"
        assert "not found" in sync.error_message

        db_session.refresh(integration)
        assert integration.connection_status == "error"

    def test_sync_not_found(self, db_session, test_user):
        with pytest.raises(ValueError, match="not found"):
            integration_service.sync_integration(db_session, test_user.id, "nonexistent")

    @patch("app.services.integration_service._clone_and_find_manifest")
    def test_sync_creates_context_file(self, mock_clone, db_session, test_user, sample_manifest):
        mock_clone.return_value = sample_manifest
        config = {"repo_url": "https://github.com/test/repo.git"}
        integration = integration_service.create_integration(
            db_session, test_user.id, "dbt", "Test", config,
        )
        sync = integration_service.sync_integration(db_session, test_user.id, integration.id)
        assert sync.status == "completed"

        # Should have created a context file
        cf = db_session.query(ContextFile).filter(
            ContextFile.integration_id == integration.id
        ).first()
        assert cf is not None
        assert cf.filename == "dbt-Test.yml"
        assert cf.source == "integration"
        assert "customers" in cf.content

    @patch("app.services.integration_service._clone_and_find_manifest")
    def test_sync_replaces_old_context(self, mock_clone, db_session, test_user, sample_manifest):
        mock_clone.return_value = sample_manifest
        config = {"repo_url": "https://github.com/test/repo.git"}
        integration = integration_service.create_integration(
            db_session, test_user.id, "dbt", "Test", config,
        )
        # First sync
        integration_service.sync_integration(db_session, test_user.id, integration.id)
        # Second sync should update, not duplicate
        integration_service.sync_integration(db_session, test_user.id, integration.id)

        total = db_session.query(ContextFile).filter(
            ContextFile.integration_id == integration.id
        ).count()
        assert total == 1

    @patch("app.services.integration_service._clone_and_parse_omni")
    def test_sync_omni_success(self, mock_clone, db_session, test_user):
        mock_clone.return_value = [
            {
                "metadata_type": "view",
                "name": "customers",
                "schema_name": "public",
                "database": "",
                "description": "Customer table",
                "columns": [
                    {"name": "id", "description": "", "data_type": "number", "tests": [], "kind": "dimension"},
                ],
                "tags": [],
                "meta": {"table_name": "customers"},
                "relationships": {},
                "raw_definition": {"path": "customers.view"},
            }
        ]
        config = {"repo_url": "https://github.com/test/omni-repo.git"}
        integration = integration_service.create_integration(
            db_session, test_user.id, "omni", "Shop", config,
        )
        sync = integration_service.sync_integration(db_session, test_user.id, integration.id)
        assert sync.status == "completed"
        assert sync.metadata_count == 1

        cf = db_session.query(ContextFile).filter(
            ContextFile.integration_id == integration.id
        ).first()
        assert cf is not None
        assert cf.filename == "omni-Shop.yml"
        assert "customers" in cf.content

    def test_get_latest_sync(self, db_session, test_user):
        config = {"repo_url": "https://github.com/test/repo.git"}
        integration = integration_service.create_integration(
            db_session, test_user.id, "dbt", "Test", config,
        )
        # No syncs yet
        assert integration_service.get_latest_sync(db_session, integration.id) is None

        # Add syncs with distinct timestamps
        from datetime import timedelta
        now = datetime.utcnow()
        s1 = IntegrationSync(
            id=str(uuid.uuid4()), integration_id=integration.id,
            status="completed", started_at=now - timedelta(minutes=5),
        )
        s2 = IntegrationSync(
            id=str(uuid.uuid4()), integration_id=integration.id,
            status="failed", started_at=now,
        )
        db_session.add_all([s1, s2])
        db_session.commit()

        latest = integration_service.get_latest_sync(db_session, integration.id)
        assert latest.id == s2.id


# ─── API Route Tests ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestIntegrationAPI:
    async def test_create_integration_requires_auth(self, client):
        response = await client.post("/api/integrations", json={
            "integration_type": "dbt",
            "name": "Test",
            "config": {"repo_url": "https://github.com/test/repo.git"},
        })
        assert response.status_code == 401

    @patch("app.core.dependencies.DISABLE_AUTH", True)
    async def test_create_integration(self, authed_client):
        response = await authed_client.post("/api/integrations", json={
            "integration_type": "dbt",
            "name": "My dbt Project",
            "config": {"repo_url": "https://github.com/test/repo.git", "branch": "main"},
        })
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "My dbt Project"
        assert data["integration_type"] == "dbt"
        assert data["connection_status"] == "pending"

    @patch("app.core.dependencies.DISABLE_AUTH", True)
    async def test_list_integrations(self, authed_client):
        await authed_client.post("/api/integrations", json={
            "integration_type": "dbt",
            "name": "Test1",
            "config": {"repo_url": "https://github.com/test/repo.git"},
        })
        response = await authed_client.get("/api/integrations")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1

    @patch("app.core.dependencies.DISABLE_AUTH", True)
    async def test_get_integration(self, authed_client):
        create_resp = await authed_client.post("/api/integrations", json={
            "integration_type": "dbt",
            "name": "Get Test",
            "config": {"repo_url": "https://github.com/test/repo.git"},
        })
        integration_id = create_resp.json()["id"]
        response = await authed_client.get(f"/api/integrations/{integration_id}")
        assert response.status_code == 200
        assert response.json()["name"] == "Get Test"

    @patch("app.core.dependencies.DISABLE_AUTH", True)
    async def test_get_integration_not_found(self, authed_client):
        response = await authed_client.get("/api/integrations/nonexistent")
        assert response.status_code == 404

    @patch("app.core.dependencies.DISABLE_AUTH", True)
    async def test_delete_integration(self, authed_client):
        create_resp = await authed_client.post("/api/integrations", json={
            "integration_type": "dbt",
            "name": "Delete Test",
            "config": {"repo_url": "https://github.com/test/repo.git"},
        })
        integration_id = create_resp.json()["id"]
        response = await authed_client.delete(f"/api/integrations/{integration_id}")
        assert response.status_code == 200
        assert response.json()["success"] is True

        # Confirm deleted
        get_resp = await authed_client.get(f"/api/integrations/{integration_id}")
        assert get_resp.status_code == 404

    @patch("app.core.dependencies.DISABLE_AUTH", True)
    async def test_create_invalid_type(self, authed_client):
        response = await authed_client.post("/api/integrations", json={
            "integration_type": "unknown",
            "name": "Bad",
            "config": {"repo_url": "https://github.com/test/repo.git"},
        })
        assert response.status_code == 400

