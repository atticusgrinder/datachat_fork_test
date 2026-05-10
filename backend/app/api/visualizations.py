"""Saved visualization CRUD endpoints."""

import json
import uuid as uuid_mod

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from app.connections.local_duckdb_persistent import LocalDuckDBExecutor
from app.core.database import get_db
from app.core.dependencies import require_auth
from app.core.security import decrypt_credentials
from app.models.local_duckdb import LocalDuckDB
from app.models.user import User
from app.models.warehouse import WarehouseConnection
from app.models.visualization import SavedVisualization
from app.schemas.visualization import (
    SaveVisualizationRequest,
    UpdateVisualizationRequest,
    VisualizationResponse,
    VisualizationRefreshResponse,
)
from app.services.warehouse_service import get_or_create_executor

router = APIRouter(tags=["visualizations"])


def _to_response(viz: SavedVisualization) -> VisualizationResponse:
    return VisualizationResponse(
        id=viz.id,
        name=viz.name,
        description=viz.description,
        chart_type=viz.chart_type,
        chart_config=viz.chart_config,
        sql_query=viz.sql_query,
        warehouse_id=viz.warehouse_id,
        local_duckdb_id=viz.local_duckdb_id,
        created_at=viz.created_at.isoformat() + "Z",
        updated_at=viz.updated_at.isoformat() + "Z",
    )


@router.get("/api/visualizations", response_model=list[VisualizationResponse])
async def list_visualizations(
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """List user's saved visualizations."""
    vizs = db.query(SavedVisualization).filter(
        SavedVisualization.user_id == user.id,
    ).order_by(SavedVisualization.updated_at.desc()).all()
    return [_to_response(v) for v in vizs]


@router.post("/api/visualizations", response_model=VisualizationResponse)
async def create_visualization(
    request: SaveVisualizationRequest,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Save a new visualization."""
    # Validate warehouse belongs to user if provided
    if request.warehouse_id:
        warehouse = db.query(WarehouseConnection).filter(
            WarehouseConnection.id == request.warehouse_id,
            WarehouseConnection.user_id == user.id,
        ).first()
        if not warehouse:
            raise HTTPException(status_code=404, detail="Warehouse not found")

    # Validate local DuckDB belongs to user if provided
    if request.local_duckdb_id:
        local_db = db.query(LocalDuckDB).filter(
            LocalDuckDB.id == request.local_duckdb_id,
            LocalDuckDB.user_id == user.id,
        ).first()
        if not local_db:
            raise HTTPException(status_code=404, detail="Local data source not found")

    # Prevent duplicate saves (same SQL + source)
    existing = db.query(SavedVisualization).filter(
        SavedVisualization.user_id == user.id,
        SavedVisualization.sql_query == request.sql_query,
        SavedVisualization.warehouse_id == request.warehouse_id,
        SavedVisualization.local_duckdb_id == request.local_duckdb_id,
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="This visualization has already been saved")

    viz = SavedVisualization(
        id=str(uuid_mod.uuid4()),
        user_id=user.id,
        name=request.name,
        description=request.description,
        chart_type=request.chart_type,
        chart_config=request.chart_config,
        sql_query=request.sql_query,
        warehouse_id=request.warehouse_id,
        local_duckdb_id=request.local_duckdb_id,
    )
    db.add(viz)
    db.commit()
    db.refresh(viz)
    return _to_response(viz)


@router.get("/api/visualizations/{viz_id}", response_model=VisualizationResponse)
async def get_visualization(
    viz_id: str,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Get a single saved visualization."""
    viz = db.query(SavedVisualization).filter(
        SavedVisualization.id == viz_id,
        SavedVisualization.user_id == user.id,
    ).first()
    if not viz:
        raise HTTPException(status_code=404, detail="Visualization not found")
    return _to_response(viz)


@router.put("/api/visualizations/{viz_id}", response_model=VisualizationResponse)
async def update_visualization(
    viz_id: str,
    request: UpdateVisualizationRequest,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Update a saved visualization."""
    viz = db.query(SavedVisualization).filter(
        SavedVisualization.id == viz_id,
        SavedVisualization.user_id == user.id,
    ).first()
    if not viz:
        raise HTTPException(status_code=404, detail="Visualization not found")

    if request.name is not None:
        viz.name = request.name
    if request.description is not None:
        viz.description = request.description
    db.commit()
    db.refresh(viz)
    return _to_response(viz)


@router.delete("/api/visualizations/{viz_id}")
async def delete_visualization(
    viz_id: str,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Delete a saved visualization."""
    viz = db.query(SavedVisualization).filter(
        SavedVisualization.id == viz_id,
        SavedVisualization.user_id == user.id,
    ).first()
    if not viz:
        raise HTTPException(status_code=404, detail="Visualization not found")
    db.delete(viz)
    db.commit()
    return {"success": True}


@router.post("/api/visualizations/{viz_id}/refresh", response_model=VisualizationRefreshResponse)
async def refresh_visualization(
    viz_id: str,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Re-execute the SQL query for a saved visualization and return fresh data."""
    viz = db.query(SavedVisualization).filter(
        SavedVisualization.id == viz_id,
        SavedVisualization.user_id == user.id,
    ).first()
    if not viz:
        raise HTTPException(status_code=404, detail="Visualization not found")

    if viz.local_duckdb_id:
        local_db = db.query(LocalDuckDB).filter(
            LocalDuckDB.id == viz.local_duckdb_id,
            LocalDuckDB.user_id == user.id,
        ).first()
        if not local_db:
            raise HTTPException(status_code=404, detail="Local data source not found or deleted")
        local_executor = LocalDuckDBExecutor(local_db.file_path)
        try:
            result_text = await local_executor.execute_sql(viz.sql_query)
        finally:
            local_executor.close()
    elif viz.warehouse_id:
        warehouse = db.query(WarehouseConnection).filter(
            WarehouseConnection.id == viz.warehouse_id,
            WarehouseConnection.user_id == user.id,
        ).first()
        if not warehouse:
            raise HTTPException(status_code=404, detail="Warehouse not found or deleted")
        credentials = decrypt_credentials(warehouse.credentials_encrypted)
        executor, is_new = get_or_create_executor(warehouse.id, warehouse.warehouse_type, credentials)
        if is_new:
            await executor.connect()
        result_text = await executor.execute_sql(viz.sql_query)
    else:
        raise HTTPException(status_code=400, detail="No data source associated with this visualization")

    # Parse the result text back into rows
    chart_data = _parse_query_result(result_text)

    return VisualizationRefreshResponse(id=viz.id, chart_data=chart_data)


def _parse_query_result(result_text: str) -> list[dict]:
    """Parse tabulate 'pretty' format query result into list of dicts.

    Pretty format looks like:
    +---------+-------+
    | col1    | col2  |
    +---------+-------+
    | value1  |   123 |
    +---------+-------+
    """
    lines = result_text.strip().split("\n")
    # Filter to only rows containing '|' (skip border lines like +---+---+)
    data_lines = [l for l in lines if "|" in l]
    if len(data_lines) < 2:
        return []

    # First data line is headers
    headers = [h.strip() for h in data_lines[0].split("|") if h.strip()]
    rows = []
    for line in data_lines[1:]:
        values = [v.strip() for v in line.split("|") if v.strip() != ""]
        # Handle lines where an empty cell produces an empty string between pipes
        raw_parts = line.split("|")[1:-1]  # skip first/last empty from leading/trailing |
        values = [v.strip() for v in raw_parts]
        if len(values) == len(headers):
            row = {}
            for h, v in zip(headers, values):
                try:
                    row[h] = int(v)
                except ValueError:
                    try:
                        row[h] = float(v)
                    except ValueError:
                        row[h] = v
            rows.append(row)
    return rows
