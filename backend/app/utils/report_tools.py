"""Claude tools for creating and scheduling reports from chat.

These tools mutate DB state and depend on chat-loop context (the most recent
execute_sql call, the active warehouse, the user). They're dispatched separately
from the read-only warehouse tools.
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Optional, Tuple

from sqlalchemy.orm import Session

from app.models.report import Report
from app.models.user import User
from app.services import report_service
from app.services.visualization_service import suggest_visualization

logger = logging.getLogger(__name__)


REPORT_TOOL_DEFINITIONS = [
    {
        "name": "create_report",
        "description": (
            "Save the most recent SQL query as a new report. Call this when the user asks to save, "
            "schedule, or email a query result. The most recent execute_sql query is captured automatically. "
            "If the user mentions a schedule (daily/weekly/monthly + a time/day), pass it via the schedule fields. "
            "If they just say 'save this as a report' without a schedule, omit the schedule fields. "
            "Email recipients are always the current user — you cannot specify other recipients."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "A short, descriptive name for the report.",
                },
                "description": {
                    "type": "string",
                    "description": "Optional one-sentence description.",
                },
                "cadence": {
                    "type": "string",
                    "enum": ["daily", "weekly", "monthly"],
                    "description": "Send cadence. Omit if user did not request a schedule.",
                },
                "day_of_week": {
                    "type": "integer",
                    "description": "Required for weekly cadence. 0=Monday..6=Sunday.",
                },
                "day_of_month": {
                    "type": "integer",
                    "description": "Required for monthly cadence. 1..28 (avoid 29-31 for safety).",
                },
                "time_of_day": {
                    "type": "string",
                    "description": "24h time HH:MM (e.g. '09:00'). Defaults to '08:00' if omitted.",
                },
                "timezone": {
                    "type": "string",
                    "description": "IANA timezone name (e.g. 'America/Los_Angeles'). Defaults to UTC.",
                },
            },
            "required": ["name"],
        },
    },
    {
        "name": "list_reports",
        "description": (
            "List the user's existing reports by name. Call this when you need to disambiguate which "
            "report the user is referring to (e.g. they say 'add this to my weekly sales report'). "
            "Always call this before add_to_report if you're not certain which report they mean."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Optional case-insensitive substring filter on report names.",
                },
            },
        },
    },
    {
        "name": "add_to_report",
        "description": (
            "Add the most recent SQL query as a new visualization in an existing report. "
            "Use this when the user asks to add a chart/query to a report they already have. "
            "If you are unsure which report the user means, ALWAYS call list_reports first and ask the "
            "user to confirm before calling this tool."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "report_id": {
                    "type": "string",
                    "description": "The id of the existing report to add to (from list_reports).",
                },
                "viz_name": {
                    "type": "string",
                    "description": "A short name for this visualization within the report.",
                },
            },
            "required": ["report_id", "viz_name"],
        },
    },
    {
        "name": "set_report_schedule",
        "description": (
            "Set or update the email send schedule for an existing report. Use this if the user wants "
            "to change when an existing report is sent, or add a schedule to a report that doesn't have one yet."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "report_id": {"type": "string"},
                "cadence": {"type": "string", "enum": ["daily", "weekly", "monthly"]},
                "day_of_week": {"type": "integer"},
                "day_of_month": {"type": "integer"},
                "time_of_day": {"type": "string"},
                "timezone": {"type": "string"},
                "enabled": {"type": "boolean"},
            },
            "required": ["report_id", "cadence"],
        },
    },
]


@dataclass
class ReportToolContext:
    """State the report tools need from the chat loop."""
    db: Session
    user: User
    warehouse_id: Optional[str] = None
    local_duckdb_id: Optional[str] = None
    last_sql_query: Optional[str] = None
    last_sql_result_text: Optional[str] = None
    last_chart_data: Optional[list] = None  # parsed rows
    last_visualization: Optional[dict] = None  # suggest_visualization output


def _is_report_tool(name: str) -> bool:
    return name in {"create_report", "list_reports", "add_to_report", "set_report_schedule"}


def _build_chart_config(viz_suggestion: dict, chart_data: list[dict]) -> str:
    """Compose the chart_config JSON string saved on SavedVisualization."""
    config = {
        "title": viz_suggestion.get("title", ""),
        "x_column": viz_suggestion.get("x_column", ""),
        "y_column": viz_suggestion.get("y_column", ""),
        "reasoning": viz_suggestion.get("reasoning", ""),
        "data": chart_data or [],
    }
    return json.dumps(config)


async def execute_report_tool(
    tool_name: str,
    tool_input: dict,
    ctx: ReportToolContext,
) -> Tuple[str, bool]:
    """Dispatch a report tool. Returns (result_text, is_error)."""
    try:
        if tool_name == "list_reports":
            query = tool_input.get("query", "")
            reports = report_service.find_reports_by_name(ctx.db, user=ctx.user, query=query)
            if not reports:
                return ("No reports found." if query else "You have no reports yet."), False
            lines = [f"- id={r.id}  name={r.name!r}" for r in reports]
            return "Existing reports:\n" + "\n".join(lines), False

        if tool_name == "create_report":
            if not ctx.last_sql_query:
                return (
                    "Cannot create a report: no SQL query has been executed yet in this conversation. "
                    "Run an execute_sql call first, then try again.",
                    True,
                )
            if not ctx.warehouse_id and not ctx.local_duckdb_id:
                return (
                    "Cannot create a scheduled report: this conversation isn't connected to a data source.",
                    True,
                )

            name = tool_input.get("name") or "Untitled report"
            description = tool_input.get("description")

            viz_suggestion = ctx.last_visualization
            if not viz_suggestion:
                # Fall back to a minimal config so saving doesn't fail
                cols = list((ctx.last_chart_data or [{}])[0].keys()) if ctx.last_chart_data else []
                viz_suggestion = {
                    "chart_type": "bar",
                    "title": name,
                    "x_column": cols[0] if cols else "",
                    "y_column": cols[1] if len(cols) > 1 else (cols[0] if cols else ""),
                    "reasoning": "auto-generated from chat",
                }

            chart_config = _build_chart_config(viz_suggestion, ctx.last_chart_data or [])

            viz = report_service.create_visualization_for_report(
                ctx.db,
                user=ctx.user,
                name=name,
                sql_query=ctx.last_sql_query,
                chart_type=viz_suggestion.get("chart_type", "bar"),
                chart_config=chart_config,
                warehouse_id=ctx.warehouse_id,
                local_duckdb_id=ctx.local_duckdb_id,
                description=description,
            )

            report = report_service.create_report(
                ctx.db,
                user=ctx.user,
                name=name,
                description=description,
                warehouse_id=ctx.warehouse_id,
                local_duckdb_id=ctx.local_duckdb_id,
            )
            report_service.add_visualization_to_report(
                ctx.db,
                user=ctx.user,
                report_id=report.id,
                saved_visualization_id=viz.id,
            )

            schedule_msg = "no schedule set"
            cadence = tool_input.get("cadence")
            if cadence:
                try:
                    schedule = report_service.set_schedule(
                        ctx.db,
                        user=ctx.user,
                        report_id=report.id,
                        cadence=cadence,
                        time_of_day=tool_input.get("time_of_day", "08:00"),
                        timezone_name=tool_input.get("timezone", "UTC"),
                        day_of_week=tool_input.get("day_of_week"),
                        day_of_month=tool_input.get("day_of_month"),
                        enabled=True,
                    )
                    schedule_msg = (
                        f"scheduled {schedule.cadence} at {schedule.time_of_day} {schedule.timezone}; "
                        f"next send {schedule.next_send_at.isoformat()}Z"
                    )
                except ValueError as e:
                    return (
                        f"Report created (id={report.id}) but schedule was rejected: {e}. "
                        "You can set the schedule later from the Reports page.",
                        False,
                    )

            return (
                f"Created report '{report.name}' (id={report.id}); {schedule_msg}. "
                f"Visible at /reports/{report.id}.",
                False,
            )

        if tool_name == "add_to_report":
            if not ctx.last_sql_query:
                return ("No recent SQL to add. Run an execute_sql call first.", True)
            if not ctx.warehouse_id and not ctx.local_duckdb_id:
                return (
                    "Adding to a report requires a connected data source.",
                    True,
                )
            report_id = tool_input.get("report_id")
            viz_name = tool_input.get("viz_name") or "Untitled chart"

            report = ctx.db.query(Report).filter(
                Report.id == report_id, Report.user_id == ctx.user.id,
            ).first()
            if not report:
                return (f"Report {report_id} not found. Call list_reports to see available reports.", True)

            viz_suggestion = ctx.last_visualization or {}
            cols = list((ctx.last_chart_data or [{}])[0].keys()) if ctx.last_chart_data else []
            if not viz_suggestion:
                viz_suggestion = {
                    "chart_type": "bar",
                    "title": viz_name,
                    "x_column": cols[0] if cols else "",
                    "y_column": cols[1] if len(cols) > 1 else (cols[0] if cols else ""),
                    "reasoning": "auto-generated from chat",
                }
            chart_config = _build_chart_config(viz_suggestion, ctx.last_chart_data or [])

            viz = report_service.create_visualization_for_report(
                ctx.db,
                user=ctx.user,
                name=viz_name,
                sql_query=ctx.last_sql_query,
                chart_type=viz_suggestion.get("chart_type", "bar"),
                chart_config=chart_config,
                warehouse_id=ctx.warehouse_id,
                local_duckdb_id=ctx.local_duckdb_id,
            )
            report_service.add_visualization_to_report(
                ctx.db,
                user=ctx.user,
                report_id=report.id,
                saved_visualization_id=viz.id,
            )
            return (f"Added '{viz_name}' to report '{report.name}'.", False)

        if tool_name == "set_report_schedule":
            try:
                schedule = report_service.set_schedule(
                    ctx.db,
                    user=ctx.user,
                    report_id=tool_input["report_id"],
                    cadence=tool_input["cadence"],
                    time_of_day=tool_input.get("time_of_day", "08:00"),
                    timezone_name=tool_input.get("timezone", "UTC"),
                    day_of_week=tool_input.get("day_of_week"),
                    day_of_month=tool_input.get("day_of_month"),
                    enabled=tool_input.get("enabled", True),
                )
            except ValueError as e:
                return (str(e), True)
            return (
                f"Schedule updated: {schedule.cadence} at {schedule.time_of_day} {schedule.timezone}; "
                f"next send {schedule.next_send_at.isoformat()}Z. Enabled={schedule.enabled}.",
                False,
            )

        return (f"Unknown report tool: {tool_name}", True)

    except Exception as e:
        logger.exception("Report tool %s failed", tool_name)
        return (f"Error: {e}", True)


def update_chart_state(ctx: ReportToolContext, *, sql_query: str, sql_result_text: str) -> None:
    """Refresh ctx with the latest SQL run so subsequent tools have it.

    Called by the chat loop after each successful execute_sql.
    """
    from app.api.conversations import _parse_query_result  # avoid circular import at module load

    ctx.last_sql_query = sql_query
    ctx.last_sql_result_text = sql_result_text
    rows = _parse_query_result(sql_result_text)
    ctx.last_chart_data = rows
    if rows:
        cols = list(rows[0].keys())
        ctx.last_visualization = suggest_visualization(cols, rows)
    else:
        ctx.last_visualization = None
