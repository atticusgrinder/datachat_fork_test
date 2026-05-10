"""Report CRUD + schedule endpoints."""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_auth
from app.models.report import Report
from app.models.user import User
from app.schemas.report import (
    AddReportItemRequest,
    CreateReportRequest,
    ReportItemResponse,
    ReportResponse,
    ScheduleResponse,
    SetScheduleRequest,
    UpdateReportRequest,
)
from app.services import email_service, report_service

router = APIRouter(tags=["reports"])


def _to_response(report: Report) -> ReportResponse:
    schedule = None
    if report.schedule is not None:
        schedule = ScheduleResponse(
            cadence=report.schedule.cadence,
            time_of_day=report.schedule.time_of_day,
            timezone=report.schedule.timezone,
            day_of_week=report.schedule.day_of_week,
            day_of_month=report.schedule.day_of_month,
            enabled=report.schedule.enabled,
            last_sent_at=(
                report.schedule.last_sent_at.isoformat() + "Z"
                if report.schedule.last_sent_at else None
            ),
            next_send_at=(
                report.schedule.next_send_at.isoformat() + "Z"
                if report.schedule.next_send_at else None
            ),
        )
    return ReportResponse(
        id=report.id,
        name=report.name,
        description=report.description,
        warehouse_id=report.warehouse_id,
        local_duckdb_id=report.local_duckdb_id,
        created_at=report.created_at.isoformat() + "Z",
        updated_at=report.updated_at.isoformat() + "Z",
        items=[
            ReportItemResponse(
                id=item.id,
                saved_visualization_id=item.saved_visualization_id,
                position=item.position,
            )
            for item in report.items
        ],
        schedule=schedule,
    )


@router.get("/api/reports", response_model=list[ReportResponse])
async def list_reports(
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    reports = (
        db.query(Report)
        .filter(Report.user_id == user.id)
        .order_by(Report.updated_at.desc())
        .all()
    )
    return [_to_response(r) for r in reports]


@router.post("/api/reports", response_model=ReportResponse)
async def create_report(
    request: CreateReportRequest,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    try:
        report = report_service.create_report(
            db,
            user=user,
            name=request.name,
            description=request.description,
            warehouse_id=request.warehouse_id,
            local_duckdb_id=request.local_duckdb_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _to_response(report)


@router.get("/api/reports/{report_id}", response_model=ReportResponse)
async def get_report(
    report_id: str,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    report = db.query(Report).filter(
        Report.id == report_id, Report.user_id == user.id,
    ).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return _to_response(report)


@router.put("/api/reports/{report_id}", response_model=ReportResponse)
async def update_report(
    report_id: str,
    request: UpdateReportRequest,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    report = db.query(Report).filter(
        Report.id == report_id, Report.user_id == user.id,
    ).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    if request.name is not None:
        report.name = request.name
    if request.description is not None:
        report.description = request.description
    db.commit()
    db.refresh(report)
    return _to_response(report)


@router.delete("/api/reports/{report_id}")
async def delete_report(
    report_id: str,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    try:
        report_service.delete_report(db, user=user, report_id=report_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"success": True}


@router.post("/api/reports/{report_id}/items", response_model=ReportResponse)
async def add_report_item(
    report_id: str,
    request: AddReportItemRequest,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    try:
        report_service.add_visualization_to_report(
            db, user=user, report_id=report_id,
            saved_visualization_id=request.saved_visualization_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    report = db.query(Report).filter(Report.id == report_id).first()
    return _to_response(report)


@router.delete("/api/reports/{report_id}/items/{item_id}", response_model=ReportResponse)
async def delete_report_item(
    report_id: str,
    item_id: str,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    try:
        report_service.remove_item_from_report(db, user=user, item_id=item_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    report = db.query(Report).filter(
        Report.id == report_id, Report.user_id == user.id,
    ).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return _to_response(report)


@router.put("/api/reports/{report_id}/schedule", response_model=ReportResponse)
async def set_schedule(
    report_id: str,
    request: SetScheduleRequest,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    try:
        report_service.set_schedule(
            db, user=user, report_id=report_id,
            cadence=request.cadence,
            time_of_day=request.time_of_day,
            timezone_name=request.timezone,
            day_of_week=request.day_of_week,
            day_of_month=request.day_of_month,
            enabled=request.enabled,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    report = db.query(Report).filter(Report.id == report_id).first()
    return _to_response(report)


@router.delete("/api/reports/{report_id}/schedule", response_model=ReportResponse)
async def disable_schedule(
    report_id: str,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    try:
        report_service.disable_schedule(db, user=user, report_id=report_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    report = db.query(Report).filter(
        Report.id == report_id, Report.user_id == user.id,
    ).first()
    return _to_response(report)


@router.post("/api/reports/{report_id}/send-now")
async def send_now(
    report_id: str,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    report = db.query(Report).filter(
        Report.id == report_id, Report.user_id == user.id,
    ).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    try:
        message_id = await report_service.send_report_now(db, report_id=report_id)
    except email_service.EmailNotConfiguredError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except email_service.EmailSendError as e:
        raise HTTPException(status_code=502, detail=f"Email provider rejected the send: {e.message}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"success": True, "message_id": message_id}
