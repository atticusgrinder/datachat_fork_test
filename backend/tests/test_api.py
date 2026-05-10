"""Tests for API routes using FastAPI TestClient."""

import os
from unittest.mock import patch, MagicMock, AsyncMock

import pytest


# Enable DISABLE_AUTH for API tests so we don't need real Clerk tokens
@pytest.fixture(autouse=True)
def enable_disable_auth():
    with patch("app.core.dependencies.DISABLE_AUTH", True):
        yield


class TestHealthEndpoints:
    async def test_root(self, client):
        resp = await client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "online"
        assert "version" in data

    async def test_health(self, client):
        resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "healthy"

    async def test_models(self, client):
        resp = await client.get("/api/models")
        assert resp.status_code == 200
        data = resp.json()
        assert "models" in data
        assert "default" in data
        assert len(data["models"]) > 0
        model_ids = [m["id"] for m in data["models"]]
        assert data["default"] in model_ids


class TestWarehouseEndpoints:
    async def test_get_warehouse_types(self, authed_client):
        resp = await authed_client.get("/api/warehouse/types")
        assert resp.status_code == 200
        data = resp.json()
        assert "motherduck" in data
        assert "bigquery" in data
        assert "snowflake" in data
        assert "postgresql" in data
        assert "redshift" in data

    async def test_list_warehouses_empty(self, authed_client):
        resp = await authed_client.get("/api/warehouse/list")
        assert resp.status_code == 200
        assert resp.json() == []

    @patch("app.api.warehouses.test_warehouse_connection")
    async def test_configure_warehouse(self, mock_test, authed_client):
        mock_test.return_value = {"success": True, "message": "Connected"}
        resp = await authed_client.post("/api/warehouse/configure", json={
            "warehouse_type": "postgresql",
            "name": "My PG",
            "credentials": {
                "host": "localhost", "port": "5432",
                "database": "testdb", "username": "user", "password": "pass",
            },
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["warehouse_type"] == "postgresql"
        assert data["name"] == "My PG"
        assert data["connection_status"] == "connected"

    async def test_configure_invalid_type(self, authed_client):
        resp = await authed_client.post("/api/warehouse/configure", json={
            "warehouse_type": "oracle",
            "name": "Bad",
            "credentials": {},
        })
        assert resp.status_code == 400

    @patch("app.api.warehouses.test_warehouse_connection")
    async def test_configure_missing_field(self, mock_test, authed_client):
        mock_test.return_value = {"success": True}
        resp = await authed_client.post("/api/warehouse/configure", json={
            "warehouse_type": "postgresql",
            "name": "Missing fields",
            "credentials": {"host": "localhost"},
        })
        assert resp.status_code == 400

    @patch("app.api.warehouses.test_warehouse_connection")
    async def test_configure_connection_failure(self, mock_test, authed_client):
        mock_test.return_value = {"success": False, "error": "Connection refused"}
        resp = await authed_client.post("/api/warehouse/configure", json={
            "warehouse_type": "postgresql",
            "name": "Bad conn",
            "credentials": {
                "host": "badhost", "port": "5432",
                "database": "db", "username": "u", "password": "p",
            },
        })
        assert resp.status_code == 400
        assert "Connection refused" in resp.json()["detail"]

    async def test_get_nonexistent_warehouse(self, authed_client):
        resp = await authed_client.get("/api/warehouse/nonexistent-id/status")
        assert resp.status_code == 404

    async def test_delete_nonexistent_warehouse(self, authed_client):
        resp = await authed_client.delete("/api/warehouse/nonexistent-id")
        assert resp.status_code == 404

    @patch("app.api.warehouses.test_warehouse_connection")
    async def test_full_crud_flow(self, mock_test, authed_client):
        mock_test.return_value = {"success": True, "message": "Connected"}

        # Create
        resp = await authed_client.post("/api/warehouse/configure", json={
            "warehouse_type": "postgresql",
            "name": "CRUD Test",
            "credentials": {
                "host": "localhost", "port": "5432",
                "database": "testdb", "username": "user", "password": "pass",
            },
        })
        assert resp.status_code == 200
        wh_id = resp.json()["id"]

        # List
        resp = await authed_client.get("/api/warehouse/list")
        assert resp.status_code == 200
        assert any(w["id"] == wh_id for w in resp.json())

        # Status
        resp = await authed_client.get(f"/api/warehouse/{wh_id}/status")
        assert resp.status_code == 200
        assert resp.json()["id"] == wh_id

        # Delete
        resp = await authed_client.delete(f"/api/warehouse/{wh_id}")
        assert resp.status_code == 200

        # Verify deleted
        resp = await authed_client.get(f"/api/warehouse/{wh_id}/status")
        assert resp.status_code == 404


class TestConversationEndpoints:
    async def test_list_conversations_empty(self, authed_client):
        resp = await authed_client.get("/api/conversations")
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_create_conversation(self, authed_client):
        resp = await authed_client.post("/api/conversations", json={
            "title": "Test Chat",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "Test Chat"
        assert "id" in data

    async def test_get_conversation_messages_empty(self, authed_client):
        # Create a conversation first
        resp = await authed_client.post("/api/conversations", json={"title": "Msg Test"})
        conv_id = resp.json()["id"]

        resp = await authed_client.get(f"/api/conversations/{conv_id}/messages")
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_get_nonexistent_conversation(self, authed_client):
        resp = await authed_client.get("/api/conversations/fake-id/messages")
        assert resp.status_code == 404

    async def test_delete_conversation(self, authed_client):
        resp = await authed_client.post("/api/conversations", json={"title": "To Delete"})
        conv_id = resp.json()["id"]

        resp = await authed_client.delete(f"/api/conversations/{conv_id}")
        assert resp.status_code == 200

        resp = await authed_client.get(f"/api/conversations/{conv_id}/messages")
        assert resp.status_code == 404

    async def test_rename_conversation(self, authed_client):
        resp = await authed_client.post("/api/conversations", json={"title": "Original"})
        conv_id = resp.json()["id"]

        resp = await authed_client.patch(f"/api/conversations/{conv_id}", json={"title": "Renamed"})
        assert resp.status_code == 200
        assert resp.json()["success"] is True


class TestAuthMiddleware:
    async def test_unauthenticated_warehouse_list(self, client):
        """Without DISABLE_AUTH and no token, protected routes should 401."""
        with patch("app.core.dependencies.DISABLE_AUTH", False):
            resp = await client.get("/api/warehouse/list")
            assert resp.status_code == 401

    async def test_unauthenticated_conversations(self, client):
        with patch("app.core.dependencies.DISABLE_AUTH", False):
            resp = await client.get("/api/conversations")
            assert resp.status_code == 401

    async def test_public_endpoints_no_auth(self, client):
        """Public endpoints should work without auth."""
        with patch("app.core.dependencies.DISABLE_AUTH", False):
            resp = await client.get("/health")
            assert resp.status_code == 200

            resp = await client.get("/api/models")
            assert resp.status_code == 200

            resp = await client.get("/")
            assert resp.status_code == 200


class TestErrorResponses:
    async def test_404_on_missing_resource(self, authed_client):
        resp = await authed_client.get("/api/warehouse/nonexistent/status")
        assert resp.status_code == 404
        assert "detail" in resp.json()

    async def test_400_on_bad_input(self, authed_client):
        resp = await authed_client.post("/api/warehouse/configure", json={
            "warehouse_type": "invalid_type",
            "name": "bad",
            "credentials": {},
        })
        assert resp.status_code == 400

    async def test_422_on_missing_body(self, authed_client):
        resp = await authed_client.post("/api/warehouse/configure")
        assert resp.status_code == 422
