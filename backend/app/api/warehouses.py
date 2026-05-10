"""Warehouse connection endpoints."""

import json
import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.config import WAREHOUSE_CONFIGS
from app.core.security import encrypt_credentials, decrypt_credentials
from app.core.dependencies import require_auth
from app.models.user import User
from app.models.warehouse import WarehouseConnection
from app.models.conversation import Conversation
from app.schemas.warehouse import WarehouseConfigRequest, WarehouseResponse, AllowlistRequest
from app.services.warehouse_service import (
    test_warehouse_connection, get_or_create_executor, get_or_fetch_schema, evict_executor,
)

router = APIRouter(prefix="/api/warehouse", tags=["warehouses"])


@router.get("/types")
async def get_warehouse_types():
    """Get available warehouse types and their configuration requirements."""
    return {
        warehouse_type: {
            "name": config["name"],
            "description": config["description"],
            "required_fields": config["required_fields"],
            "auth_type": config["auth_type"],
            **({"auth_modes": config["auth_modes"]} if "auth_modes" in config else {}),
        }
        for warehouse_type, config in WAREHOUSE_CONFIGS.items()
    }


@router.post("/configure", response_model=WarehouseResponse)
async def configure_warehouse(
    request: WarehouseConfigRequest,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Create a new warehouse connection."""
    if request.warehouse_type not in WAREHOUSE_CONFIGS:
        raise HTTPException(status_code=400, detail=f"Invalid warehouse type: {request.warehouse_type}")

    config = WAREHOUSE_CONFIGS[request.warehouse_type]
    # Determine which fields to validate based on auth mode
    required_fields = config["required_fields"]
    if "auth_modes" in config:
        # Detect auth mode from credentials
        for mode_key, mode_config in config["auth_modes"].items():
            mode_fields = mode_config["required_fields"]
            if all(request.credentials.get(f) for f in mode_fields):
                required_fields = mode_fields
                break
    for field in required_fields:
        if field not in request.credentials or not request.credentials[field]:
            raise HTTPException(status_code=400, detail=f"Missing required field: {field}")

    test_result = await test_warehouse_connection(request.warehouse_type, request.credentials)
    if not test_result["success"]:
        raise HTTPException(status_code=400, detail=f"Connection failed: {test_result['error']}")

    encrypted_creds = encrypt_credentials(request.credentials)

    warehouse = WarehouseConnection(
        id=str(uuid.uuid4()),
        user_id=user.id,
        warehouse_type=request.warehouse_type,
        name=request.name,
        credentials_encrypted=encrypted_creds,
        connection_status="connected",
        last_tested_at=datetime.utcnow(),
    )
    db.add(warehouse)
    db.commit()
    db.refresh(warehouse)

    return WarehouseResponse(
        id=warehouse.id,
        warehouse_type=warehouse.warehouse_type,
        name=warehouse.name,
        connection_status=warehouse.connection_status,
        is_read_only=warehouse.is_read_only,
        is_demo=bool(warehouse.is_demo),
        last_tested_at=warehouse.last_tested_at.isoformat() + "Z" if warehouse.last_tested_at else None,
        created_at=warehouse.created_at.isoformat() + "Z",
    )


@router.get("/list", response_model=List[WarehouseResponse])
async def list_warehouses(
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """List all warehouse connections for the user."""
    warehouses = db.query(WarehouseConnection).filter(
        WarehouseConnection.user_id == user.id
    ).order_by(WarehouseConnection.created_at.desc()).all()

    return [
        WarehouseResponse(
            id=w.id,
            warehouse_type=w.warehouse_type,
            name=w.name,
            connection_status=w.connection_status,
            is_read_only=w.is_read_only,
            is_demo=bool(w.is_demo),
            last_tested_at=w.last_tested_at.isoformat() + "Z" if w.last_tested_at else None,
            created_at=w.created_at.isoformat() + "Z",
        )
        for w in warehouses
    ]


@router.get("/{warehouse_id}/status")
async def get_warehouse_status(
    warehouse_id: str,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Get status of a specific warehouse connection."""
    warehouse = db.query(WarehouseConnection).filter(
        WarehouseConnection.id == warehouse_id,
        WarehouseConnection.user_id == user.id,
    ).first()

    if not warehouse:
        raise HTTPException(status_code=404, detail="Warehouse not found")

    return {
        "id": warehouse.id,
        "warehouse_type": warehouse.warehouse_type,
        "name": warehouse.name,
        "connection_status": warehouse.connection_status,
        "last_tested_at": warehouse.last_tested_at.isoformat() + "Z" if warehouse.last_tested_at else None,
    }


@router.post("/{warehouse_id}/test")
async def test_warehouse(
    warehouse_id: str,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Test a warehouse connection."""
    warehouse = db.query(WarehouseConnection).filter(
        WarehouseConnection.id == warehouse_id,
        WarehouseConnection.user_id == user.id,
    ).first()

    if not warehouse:
        raise HTTPException(status_code=404, detail="Warehouse not found")

    evict_executor(warehouse_id)
    credentials = decrypt_credentials(warehouse.credentials_encrypted)
    test_result = await test_warehouse_connection(warehouse.warehouse_type, credentials)

    warehouse.connection_status = "connected" if test_result["success"] else "error"
    warehouse.last_tested_at = datetime.utcnow()
    db.commit()

    return {
        "success": test_result["success"],
        "message": test_result.get("message", ""),
        "error": test_result.get("error", ""),
    }


@router.delete("/{warehouse_id}")
async def delete_warehouse(
    warehouse_id: str,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Delete a warehouse connection."""
    warehouse = db.query(WarehouseConnection).filter(
        WarehouseConnection.id == warehouse_id,
        WarehouseConnection.user_id == user.id,
    ).first()

    if not warehouse:
        raise HTTPException(status_code=404, detail="Warehouse not found")

    evict_executor(warehouse.id)

    db.query(Conversation).filter(
        Conversation.warehouse_connection_id == warehouse_id
    ).update({Conversation.warehouse_connection_id: None})

    db.delete(warehouse)
    db.commit()

    return {"success": True}


@router.get("/{warehouse_id}/schema")
async def get_warehouse_schema(
    warehouse_id: str,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Return structured schema preview for a warehouse."""
    warehouse = db.query(WarehouseConnection).filter(
        WarehouseConnection.id == warehouse_id,
        WarehouseConnection.user_id == user.id,
    ).first()
    if not warehouse:
        raise HTTPException(status_code=404, detail="Warehouse not found")

    credentials = decrypt_credentials(warehouse.credentials_encrypted)
    executor, is_new = get_or_create_executor(warehouse.id, warehouse.warehouse_type, credentials)
    if is_new:
        await executor.connect()
    schema_text = await get_or_fetch_schema(warehouse.id, executor)

    tables_list = []
    datasets_set = set()
    for line in schema_text.strip().splitlines():
        if line.startswith("--") or not line.strip():
            continue
        if ": " not in line:
            continue
        table_path, cols_str = line.split(": ", 1)
        parts = table_path.split(".")
        if len(parts) >= 3:
            dataset = parts[-2]
            table = parts[-1]
        elif len(parts) == 2:
            dataset = parts[0]
            table = parts[1]
        else:
            dataset = ""
            table = parts[0]
        datasets_set.add(dataset)

        columns = []
        for col_part in cols_str.split("), "):
            col_part = col_part.strip().rstrip(")")
            if " (" in col_part:
                col_name, col_type = col_part.split(" (", 1)
                columns.append({"name": col_name.strip(), "data_type": col_type.strip()})

        tables_list.append({
            "dataset": dataset,
            "table": table,
            "columns": columns,
        })

    return {
        "datasets_count": len(datasets_set),
        "tables_count": len(tables_list),
        "tables": tables_list,
    }


@router.post("/{warehouse_id}/verify-readonly")
async def verify_warehouse_readonly(
    warehouse_id: str,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Verify whether a warehouse connection is read-only."""
    warehouse = db.query(WarehouseConnection).filter(
        WarehouseConnection.id == warehouse_id,
        WarehouseConnection.user_id == user.id,
    ).first()
    if not warehouse:
        raise HTTPException(status_code=404, detail="Warehouse not found")

    credentials = decrypt_credentials(warehouse.credentials_encrypted)
    executor, is_new = get_or_create_executor(warehouse.id, warehouse.warehouse_type, credentials)
    if is_new:
        await executor.connect()

    is_read_only = await executor.verify_read_only()
    warehouse.is_read_only = is_read_only
    db.commit()

    return {"is_read_only": is_read_only}


@router.get("/{warehouse_id}/allowlist")
async def get_warehouse_allowlist(
    warehouse_id: str,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Get the current table allowlist for a warehouse."""
    warehouse = db.query(WarehouseConnection).filter(
        WarehouseConnection.id == warehouse_id,
        WarehouseConnection.user_id == user.id,
    ).first()
    if not warehouse:
        raise HTTPException(status_code=404, detail="Warehouse not found")

    allowed = warehouse.allowed_tables
    if isinstance(allowed, str):
        allowed = json.loads(allowed)

    return {"allowed_tables": allowed}


@router.put("/{warehouse_id}/allowlist")
async def update_warehouse_allowlist(
    warehouse_id: str,
    request: AllowlistRequest,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Update the table allowlist for a warehouse."""
    warehouse = db.query(WarehouseConnection).filter(
        WarehouseConnection.id == warehouse_id,
        WarehouseConnection.user_id == user.id,
    ).first()
    if not warehouse:
        raise HTTPException(status_code=404, detail="Warehouse not found")

    warehouse.allowed_tables = json.dumps(request.allowed_tables) if request.allowed_tables is not None else None
    db.commit()

    return {"success": True, "allowed_tables": request.allowed_tables}
