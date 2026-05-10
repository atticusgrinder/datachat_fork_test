"""Tests for the chat-side report tool dispatcher."""

import pytest

from app.models.report import Report
from app.services import report_service
from app.utils.report_tools import (
    REPORT_TOOL_DEFINITIONS,
    ReportToolContext,
    execute_report_tool,
    update_chart_state,
)


def test_tool_definitions_have_required_shape():
    names = {t["name"] for t in REPORT_TOOL_DEFINITIONS}
    assert names == {"create_report", "list_reports", "add_to_report", "set_report_schedule"}
    for tool in REPORT_TOOL_DEFINITIONS:
        assert "description" in tool and tool["description"]
        assert "input_schema" in tool


@pytest.mark.asyncio
async def test_create_report_without_recent_sql_returns_error(db_session, test_user, test_warehouse):
    ctx = ReportToolContext(db=db_session, user=test_user, warehouse_id=test_warehouse.id)
    text, is_error = await execute_report_tool(
        "create_report", {"name": "X"}, ctx,
    )
    assert is_error
    assert "no sql query" in text.lower()


@pytest.mark.asyncio
async def test_create_report_without_data_source_returns_error(db_session, test_user):
    ctx = ReportToolContext(db=db_session, user=test_user, warehouse_id=None,
                            last_sql_query="select 1")
    text, is_error = await execute_report_tool(
        "create_report", {"name": "X"}, ctx,
    )
    assert is_error
    assert "data source" in text.lower()


@pytest.mark.asyncio
async def test_create_report_with_schedule_persists(db_session, test_user, test_warehouse):
    ctx = ReportToolContext(
        db=db_session, user=test_user, warehouse_id=test_warehouse.id,
        last_sql_query="select count(*) as n from users",
        last_sql_result_text="| n |\n| 5 |",
        last_chart_data=[{"n": 5}],
        last_visualization={"chart_type": "bar", "title": "n", "x_column": "n", "y_column": "n"},
    )
    text, is_error = await execute_report_tool(
        "create_report",
        {"name": "User count", "cadence": "daily", "time_of_day": "08:00", "timezone": "UTC"},
        ctx,
    )
    assert not is_error, text
    assert "Created report" in text

    reports = db_session.query(Report).filter(Report.user_id == test_user.id).all()
    assert len(reports) == 1
    assert reports[0].schedule is not None
    assert reports[0].schedule.cadence == "daily"
    assert len(reports[0].items) == 1


@pytest.mark.asyncio
async def test_list_reports_filters_by_query(db_session, test_user, test_warehouse):
    report_service.create_report(db_session, user=test_user, name="Weekly Sales",
                                 warehouse_id=test_warehouse.id)
    report_service.create_report(db_session, user=test_user, name="Monthly Revenue",
                                 warehouse_id=test_warehouse.id)
    ctx = ReportToolContext(db=db_session, user=test_user, warehouse_id=test_warehouse.id)

    text, is_error = await execute_report_tool("list_reports", {"query": "sales"}, ctx)
    assert not is_error
    assert "Weekly Sales" in text
    assert "Monthly Revenue" not in text

    text, is_error = await execute_report_tool("list_reports", {}, ctx)
    assert "Weekly Sales" in text and "Monthly Revenue" in text


@pytest.mark.asyncio
async def test_add_to_report_unknown_id_errors(db_session, test_user, test_warehouse):
    ctx = ReportToolContext(
        db=db_session, user=test_user, warehouse_id=test_warehouse.id,
        last_sql_query="select 1",
        last_chart_data=[{"a": 1}],
    )
    text, is_error = await execute_report_tool(
        "add_to_report",
        {"report_id": "does-not-exist", "viz_name": "x"},
        ctx,
    )
    assert is_error
    assert "not found" in text.lower()


def test_update_chart_state_parses_pretty_table():
    ctx = ReportToolContext(db=None, user=None, warehouse_id=None)
    update_chart_state(
        ctx,
        sql_query="select * from t",
        sql_result_text="| col | val |\n| a   | 10  |\n| b   | 20  |",
    )
    assert ctx.last_sql_query == "select * from t"
    assert ctx.last_chart_data == [{"col": "a", "val": 10}, {"col": "b", "val": 20}]


@pytest.mark.asyncio
async def test_create_report_with_local_duckdb_persists(db_session, test_user, test_local_duckdb):
    """Local DuckDB chats should be able to create scheduled reports without a warehouse."""
    ctx = ReportToolContext(
        db=db_session, user=test_user,
        warehouse_id=None,
        local_duckdb_id=test_local_duckdb.id,
        last_sql_query="select count(*) as n from sales",
        last_sql_result_text="| n |\n| 7 |",
        last_chart_data=[{"n": 7}],
        last_visualization={"chart_type": "bar", "title": "n", "x_column": "n", "y_column": "n"},
    )
    text, is_error = await execute_report_tool(
        "create_report",
        {"name": "Local sales", "cadence": "daily", "time_of_day": "09:00", "timezone": "UTC"},
        ctx,
    )
    assert not is_error, text

    reports = db_session.query(Report).filter(Report.user_id == test_user.id).all()
    assert len(reports) == 1
    assert reports[0].local_duckdb_id == test_local_duckdb.id
    assert reports[0].warehouse_id is None
    assert len(reports[0].items) == 1
    saved_viz = reports[0].items[0].visualization
    assert saved_viz.local_duckdb_id == test_local_duckdb.id
    assert saved_viz.warehouse_id is None
