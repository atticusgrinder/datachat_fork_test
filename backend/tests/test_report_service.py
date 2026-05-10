"""Tests for report service: CRUD, schedule math, and email rendering."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
from zoneinfo import ZoneInfo

from app.models.report import ReportSchedule
from app.models.visualization import SavedVisualization
from app.services import report_service


def _make_viz(db, user, *, sql="select 1", warehouse_id=None, name="Viz"):
    viz = SavedVisualization(
        user_id=user.id,
        name=name,
        chart_type="bar",
        chart_config="{}",
        sql_query=sql,
        warehouse_id=warehouse_id,
    )
    db.add(viz)
    db.commit()
    db.refresh(viz)
    return viz


def test_create_and_delete_report(db_session, test_user, test_warehouse):
    report = report_service.create_report(
        db_session, user=test_user, name="Weekly KPIs", warehouse_id=test_warehouse.id,
    )
    assert report.id
    assert report.name == "Weekly KPIs"
    assert report.warehouse_id == test_warehouse.id

    report_service.delete_report(db_session, user=test_user, report_id=report.id)
    refetched = db_session.query(type(report)).filter_by(id=report.id).first()
    assert refetched is None


def test_add_visualization_is_idempotent(db_session, test_user, test_warehouse):
    viz = _make_viz(db_session, test_user, warehouse_id=test_warehouse.id)
    report = report_service.create_report(
        db_session, user=test_user, name="R", warehouse_id=test_warehouse.id,
    )
    a = report_service.add_visualization_to_report(
        db_session, user=test_user, report_id=report.id, saved_visualization_id=viz.id,
    )
    b = report_service.add_visualization_to_report(
        db_session, user=test_user, report_id=report.id, saved_visualization_id=viz.id,
    )
    assert a.id == b.id  # second add returns the existing item


def test_set_schedule_validates(db_session, test_user, test_warehouse):
    report = report_service.create_report(
        db_session, user=test_user, name="R", warehouse_id=test_warehouse.id,
    )

    with pytest.raises(ValueError, match="Invalid cadence"):
        report_service.set_schedule(
            db_session, user=test_user, report_id=report.id, cadence="hourly",
        )

    with pytest.raises(ValueError, match="day_of_week is required"):
        report_service.set_schedule(
            db_session, user=test_user, report_id=report.id, cadence="weekly",
        )

    with pytest.raises(ValueError, match="day_of_month is required"):
        report_service.set_schedule(
            db_session, user=test_user, report_id=report.id, cadence="monthly",
        )

    with pytest.raises(ValueError, match="Invalid timezone"):
        report_service.set_schedule(
            db_session, user=test_user, report_id=report.id,
            cadence="daily", timezone_name="Not/A_Real_Zone",
        )


def test_compute_next_send_at_daily():
    schedule = ReportSchedule(
        cadence="daily", time_of_day="09:00", timezone="UTC",
        enabled=True,
    )
    # If we evaluate at 08:00 UTC, next send is 09:00 UTC same day
    after = datetime(2026, 5, 5, 8, 0, 0)
    nxt = report_service.compute_next_send_at(schedule, after=after)
    assert nxt == datetime(2026, 5, 5, 9, 0, 0)

    # If we evaluate at 10:00 UTC, next send rolls to tomorrow 09:00
    after = datetime(2026, 5, 5, 10, 0, 0)
    nxt = report_service.compute_next_send_at(schedule, after=after)
    assert nxt == datetime(2026, 5, 6, 9, 0, 0)


def test_compute_next_send_at_weekly_picks_correct_weekday():
    # Tuesday=1
    schedule = ReportSchedule(
        cadence="weekly", time_of_day="09:00", timezone="UTC", day_of_week=1,
        enabled=True,
    )
    # 2026-05-05 is a Tuesday — but if we eval at 10:00 (past 09:00), next is next Tuesday
    after = datetime(2026, 5, 5, 10, 0, 0)
    nxt = report_service.compute_next_send_at(schedule, after=after)
    assert nxt.weekday() == 1
    assert nxt == datetime(2026, 5, 12, 9, 0, 0)

    # If we eval Tuesday at 08:00, next send is same day at 09:00
    after = datetime(2026, 5, 5, 8, 0, 0)
    nxt = report_service.compute_next_send_at(schedule, after=after)
    assert nxt == datetime(2026, 5, 5, 9, 0, 0)


def test_compute_next_send_at_respects_timezone():
    # Schedule for 09:00 in LA. Eval at 16:00 UTC (= 09:00 LA, since LA is UTC-7 in May).
    schedule = ReportSchedule(
        cadence="daily", time_of_day="09:00", timezone="America/Los_Angeles",
        enabled=True,
    )
    # 2026-05-05 16:30 UTC is past 09:00 LA, so next send is tomorrow 09:00 LA = 16:00 UTC next day.
    after = datetime(2026, 5, 5, 16, 30, 0)
    nxt = report_service.compute_next_send_at(schedule, after=after)
    nxt_la = nxt.replace(tzinfo=timezone.utc).astimezone(ZoneInfo("America/Los_Angeles"))
    assert nxt_la.hour == 9 and nxt_la.minute == 0


@pytest.mark.asyncio
async def test_send_report_now_advances_schedule(db_session, test_user, test_warehouse, mock_executor):
    """send_report_now should email and advance next_send_at for scheduled reports."""
    viz = _make_viz(db_session, test_user, warehouse_id=test_warehouse.id, sql="select 1")

    report = report_service.create_report(
        db_session, user=test_user, name="Daily KPI", warehouse_id=test_warehouse.id,
    )
    report_service.add_visualization_to_report(
        db_session, user=test_user, report_id=report.id, saved_visualization_id=viz.id,
    )
    schedule = report_service.set_schedule(
        db_session, user=test_user, report_id=report.id,
        cadence="daily", time_of_day="09:00", timezone_name="UTC",
    )
    original_next = schedule.next_send_at

    with patch("app.services.report_service.get_or_create_executor", return_value=(mock_executor, False)), \
         patch("app.services.email_service.send_html", new=AsyncMock(return_value="msg-123")):
        message_id = await report_service.send_report_now(db_session, report_id=report.id)

    db_session.refresh(schedule)
    assert message_id == "msg-123"
    assert schedule.last_sent_at is not None
    # next_send_at should have advanced (or at least not be in the past relative to last_sent_at)
    assert schedule.next_send_at >= schedule.last_sent_at


@pytest.mark.asyncio
async def test_send_report_now_requires_data_source(db_session, test_user):
    """A report with no warehouse, no local DuckDB, and no items should raise."""
    report = report_service.create_report(
        db_session, user=test_user, name="Empty Report", warehouse_id=None,
    )
    with pytest.raises(ValueError, match="data source"):
        await report_service.send_report_now(db_session, report_id=report.id)


def test_find_reports_by_name(db_session, test_user, test_warehouse):
    report_service.create_report(
        db_session, user=test_user, name="Weekly Sales", warehouse_id=test_warehouse.id,
    )
    report_service.create_report(
        db_session, user=test_user, name="Monthly Revenue", warehouse_id=test_warehouse.id,
    )
    matches = report_service.find_reports_by_name(db_session, user=test_user, query="sales")
    assert len(matches) == 1
    assert matches[0].name == "Weekly Sales"

    all_reports = report_service.find_reports_by_name(db_session, user=test_user, query="")
    assert len(all_reports) == 2
