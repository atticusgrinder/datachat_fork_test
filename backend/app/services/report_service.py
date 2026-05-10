"""Report CRUD + scheduling + email-rendering business logic.

Pure functions and helpers that the API routes, scheduler loop, and chat tools
all call into. No FastAPI imports here.
"""

import calendar
import html
import json
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.connections.local_duckdb_persistent import LocalDuckDBExecutor
from app.core.config import FRONTEND_URL
from app.core.security import decrypt_credentials
from app.models.local_duckdb import LocalDuckDB
from app.models.report import Report, ReportItem, ReportSchedule
from app.models.user import User
from app.models.visualization import SavedVisualization
from app.models.warehouse import WarehouseConnection
from app.services.warehouse_service import get_or_create_executor
from app.services import email_service

logger = logging.getLogger(__name__)


# ---------- CRUD ----------

def create_report(
    db: Session,
    *,
    user: User,
    name: str,
    description: Optional[str] = None,
    warehouse_id: Optional[str] = None,
    local_duckdb_id: Optional[str] = None,
) -> Report:
    if warehouse_id:
        warehouse = db.query(WarehouseConnection).filter(
            WarehouseConnection.id == warehouse_id,
            WarehouseConnection.user_id == user.id,
        ).first()
        if not warehouse:
            raise ValueError("Warehouse not found")

    if local_duckdb_id:
        local_db = db.query(LocalDuckDB).filter(
            LocalDuckDB.id == local_duckdb_id,
            LocalDuckDB.user_id == user.id,
        ).first()
        if not local_db:
            raise ValueError("Local data source not found")

    report = Report(
        id=str(uuid.uuid4()),
        user_id=user.id,
        name=name,
        description=description,
        warehouse_id=warehouse_id,
        local_duckdb_id=local_duckdb_id,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


def add_visualization_to_report(
    db: Session,
    *,
    user: User,
    report_id: str,
    saved_visualization_id: str,
) -> ReportItem:
    report = db.query(Report).filter(
        Report.id == report_id, Report.user_id == user.id,
    ).first()
    if not report:
        raise ValueError("Report not found")

    viz = db.query(SavedVisualization).filter(
        SavedVisualization.id == saved_visualization_id,
        SavedVisualization.user_id == user.id,
    ).first()
    if not viz:
        raise ValueError("Visualization not found")

    # Idempotency: if already in report, return existing item
    existing = db.query(ReportItem).filter(
        ReportItem.report_id == report_id,
        ReportItem.saved_visualization_id == saved_visualization_id,
    ).first()
    if existing:
        return existing

    max_pos = db.query(ReportItem).filter(
        ReportItem.report_id == report_id,
    ).count()

    item = ReportItem(
        id=str(uuid.uuid4()),
        report_id=report_id,
        saved_visualization_id=saved_visualization_id,
        position=max_pos,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def remove_item_from_report(db: Session, *, user: User, item_id: str) -> None:
    item = (
        db.query(ReportItem)
        .join(Report, Report.id == ReportItem.report_id)
        .filter(ReportItem.id == item_id, Report.user_id == user.id)
        .first()
    )
    if not item:
        raise ValueError("Report item not found")
    db.delete(item)
    db.commit()


def delete_report(db: Session, *, user: User, report_id: str) -> None:
    report = db.query(Report).filter(
        Report.id == report_id, Report.user_id == user.id,
    ).first()
    if not report:
        raise ValueError("Report not found")
    db.delete(report)
    db.commit()


# ---------- Schedule ----------

VALID_CADENCES = {"daily", "weekly", "monthly"}


def set_schedule(
    db: Session,
    *,
    user: User,
    report_id: str,
    cadence: str,
    time_of_day: str = "08:00",
    timezone_name: str = "UTC",
    day_of_week: Optional[int] = None,
    day_of_month: Optional[int] = None,
    enabled: bool = True,
) -> ReportSchedule:
    if cadence not in VALID_CADENCES:
        raise ValueError(f"Invalid cadence '{cadence}'. Must be one of {sorted(VALID_CADENCES)}.")
    if cadence == "weekly" and day_of_week is None:
        raise ValueError("day_of_week is required for weekly cadence (0=Monday..6=Sunday)")
    if cadence == "monthly" and day_of_month is None:
        raise ValueError("day_of_month is required for monthly cadence (1..28)")
    if day_of_week is not None and not (0 <= day_of_week <= 6):
        raise ValueError("day_of_week must be 0..6")
    if day_of_month is not None and not (1 <= day_of_month <= 28):
        raise ValueError("day_of_month must be 1..28 (to avoid month-length surprises)")

    # Validate time + tz
    _parse_time_of_day(time_of_day)
    try:
        ZoneInfo(timezone_name)
    except Exception as e:
        raise ValueError(f"Invalid timezone '{timezone_name}': {e}")

    report = db.query(Report).filter(
        Report.id == report_id, Report.user_id == user.id,
    ).first()
    if not report:
        raise ValueError("Report not found")

    schedule = report.schedule
    if schedule is None:
        schedule = ReportSchedule(
            id=str(uuid.uuid4()),
            report_id=report_id,
        )
        db.add(schedule)

    schedule.cadence = cadence
    schedule.day_of_week = day_of_week
    schedule.day_of_month = day_of_month
    schedule.time_of_day = time_of_day
    schedule.timezone = timezone_name
    schedule.enabled = enabled
    schedule.next_send_at = compute_next_send_at(schedule, after=datetime.utcnow())

    db.commit()
    db.refresh(schedule)
    return schedule


def disable_schedule(db: Session, *, user: User, report_id: str) -> None:
    report = db.query(Report).filter(
        Report.id == report_id, Report.user_id == user.id,
    ).first()
    if not report or report.schedule is None:
        raise ValueError("Schedule not found")
    report.schedule.enabled = False
    db.commit()


def _parse_time_of_day(time_of_day: str) -> tuple[int, int]:
    try:
        parts = time_of_day.split(":")
        hh, mm = int(parts[0]), int(parts[1])
    except (ValueError, IndexError):
        raise ValueError(f"Invalid time_of_day '{time_of_day}'. Use HH:MM (24h).")
    if not (0 <= hh <= 23 and 0 <= mm <= 59):
        raise ValueError(f"Invalid time_of_day '{time_of_day}'. Hours 0-23, minutes 0-59.")
    return hh, mm


def compute_next_send_at(schedule: ReportSchedule, *, after: datetime) -> datetime:
    """Return UTC-naive datetime of next send strictly after `after` (UTC-naive)."""
    tz = ZoneInfo(schedule.timezone)
    after_utc = after.replace(tzinfo=timezone.utc)
    after_local = after_utc.astimezone(tz)
    hh, mm = _parse_time_of_day(schedule.time_of_day)

    candidate = after_local.replace(hour=hh, minute=mm, second=0, microsecond=0)

    if schedule.cadence == "daily":
        if candidate <= after_local:
            candidate = candidate + timedelta(days=1)
    elif schedule.cadence == "weekly":
        # weekday: Mon=0..Sun=6
        target_dow = schedule.day_of_week
        days_ahead = (target_dow - candidate.weekday()) % 7
        candidate = candidate + timedelta(days=days_ahead)
        if candidate <= after_local:
            candidate = candidate + timedelta(days=7)
    elif schedule.cadence == "monthly":
        target_dom = schedule.day_of_month
        candidate = candidate.replace(day=min(target_dom, calendar.monthrange(candidate.year, candidate.month)[1]))
        if candidate <= after_local:
            # roll to next month
            year = candidate.year + (1 if candidate.month == 12 else 0)
            month = 1 if candidate.month == 12 else candidate.month + 1
            last_day = calendar.monthrange(year, month)[1]
            candidate = candidate.replace(year=year, month=month, day=min(target_dom, last_day))
    else:
        raise ValueError(f"Unknown cadence: {schedule.cadence}")

    return candidate.astimezone(timezone.utc).replace(tzinfo=None)


# ---------- Sending ----------

async def send_report_now(db: Session, *, report_id: str) -> str:
    """Render and email a report. Returns the email message id.

    Resolves the warehouse, executes each visualization's SQL, builds an HTML
    digest, and sends it to the report owner's email. Updates last_sent_at and
    advances next_send_at when called by the scheduler.
    """
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise ValueError("Report not found")

    user = db.query(User).filter(User.id == report.user_id).first()
    if not user or not user.email:
        raise ValueError("Report owner has no email on file")

    # Resolve a data source — either warehouse or local DuckDB
    warehouse_id = report.warehouse_id
    local_duckdb_id = report.local_duckdb_id

    if not warehouse_id and not local_duckdb_id:
        # Fall back to the source on the first item's saved visualization
        first_item = report.items[0] if report.items else None
        if first_item and first_item.visualization:
            warehouse_id = first_item.visualization.warehouse_id
            local_duckdb_id = first_item.visualization.local_duckdb_id

    if not warehouse_id and not local_duckdb_id:
        raise ValueError("Report has no data source to query against")

    executor = None
    local_executor: Optional[LocalDuckDBExecutor] = None
    try:
        if local_duckdb_id:
            local_db = db.query(LocalDuckDB).filter(
                LocalDuckDB.id == local_duckdb_id,
            ).first()
            if not local_db:
                raise ValueError("Local data source no longer exists")
            local_executor = LocalDuckDBExecutor(local_db.file_path)
            run_sql = local_executor.execute_sql
        else:
            warehouse = db.query(WarehouseConnection).filter(
                WarehouseConnection.id == warehouse_id,
            ).first()
            if not warehouse:
                raise ValueError("Warehouse no longer exists")
            credentials = decrypt_credentials(warehouse.credentials_encrypted)
            executor, is_new = get_or_create_executor(
                warehouse.id, warehouse.warehouse_type, credentials,
            )
            if is_new:
                await executor.connect()
            run_sql = executor.execute_sql

        sections_html: list[str] = []
        is_single_viz = len([i for i in report.items if i.visualization is not None]) == 1
        for item in report.items:
            viz = item.visualization
            if viz is None:
                continue
            try:
                result_text = await run_sql(viz.sql_query)
                rows = _parse_pretty_table(result_text)
                section = _render_viz_section(viz, rows, hide_header=is_single_viz)
            except Exception as e:
                logger.exception("Failed to execute report viz %s", viz.id)
                section = _render_error_section(viz, str(e))
            sections_html.append(section)
    finally:
        if local_executor is not None:
            local_executor.close()

    if not sections_html:
        sections_html.append('<p style="color:#666">This report has no visualizations yet.</p>')

    full_html = _render_email_shell(report, sections_html)

    message_id = await email_service.send_html(
        to=user.email,
        subject=f"[datachat] {report.name}",
        html=full_html,
    )

    # Update schedule timestamps if this report has a schedule
    if report.schedule is not None:
        report.schedule.last_sent_at = datetime.utcnow()
        if report.schedule.enabled:
            report.schedule.next_send_at = compute_next_send_at(
                report.schedule, after=datetime.utcnow(),
            )
        db.commit()

    return message_id


# ---------- HTML rendering ----------

def _render_email_shell(report: Report, sections: list[str]) -> str:
    deep_link = f"{FRONTEND_URL.rstrip('/')}/reports/{report.id}"
    desc_html = (
        f'<p style="color:#555;margin:0 0 16px 0;">{html.escape(report.description)}</p>'
        if report.description else ""
    )
    body = "\n".join(sections)
    return f"""<!doctype html>
<html><body style="font-family:-apple-system,Segoe UI,Helvetica,Arial,sans-serif;background:#f7f7f8;padding:24px;color:#222;">
  <div style="max-width:720px;margin:0 auto;background:#fff;padding:32px;border-radius:8px;border:1px solid #e5e7eb;">
    <h1 style="margin:0 0 4px 0;font-size:22px;">{html.escape(report.name)}</h1>
    <p style="color:#888;margin:0 0 20px 0;font-size:13px;">datachat report · {datetime.utcnow().strftime('%Y-%m-%d')}</p>
    {desc_html}
    {body}
    <hr style="border:none;border-top:1px solid #e5e7eb;margin:28px 0 16px 0;" />
    <p style="font-size:13px;color:#666;margin:0;">
      <a href="{deep_link}" style="color:#2563eb;text-decoration:none;">Open this report in Datachat &rarr;</a>
    </p>
  </div>
</body></html>"""


def _render_viz_section(
    viz: SavedVisualization, rows: list[dict], *, hide_header: bool = False,
) -> str:
    header = ""
    if not hide_header:
        title = html.escape(viz.name)
        desc = f'<p style="color:#555;margin:0 0 8px 0;">{html.escape(viz.description)}</p>' if viz.description else ""
        header = f'<h2 style="margin:0 0 6px 0;font-size:16px;">{title}</h2>{desc}'

    if not rows:
        body = '<p style="color:#888;font-style:italic;">No rows returned.</p>'
    else:
        chart_html = _render_email_chart(viz, rows)
        table = _render_html_table(rows[:50])
        more = (
            f'<p style="color:#888;font-size:12px;margin-top:6px;">Showing first 50 of {len(rows)} rows.</p>'
            if len(rows) > 50 else ""
        )
        body = chart_html + table + more

    return f'<section style="margin:24px 0;">{header}{body}</section>'


# Email-safe palette mirroring the in-app chart colors.
_EMAIL_CHART_COLORS = [
    "#3b82f6", "#06b6d4", "#8b5cf6", "#f59e0b",
    "#10b981", "#f43f5e", "#6366f1", "#14b8a6",
]


def _render_email_chart(viz: SavedVisualization, rows: list[dict]) -> str:
    """Render an email-safe HTML chart (bars or pie-style legend) for a viz.

    Keeps it dependency-free and works across Gmail/Apple Mail/Outlook by using
    table layouts with width percentages instead of SVG.
    """
    try:
        cfg = json.loads(viz.chart_config or "{}")
    except Exception:
        cfg = {}
    x_col = cfg.get("x_column")
    y_col = cfg.get("y_column")
    if not x_col or not y_col or not rows:
        return ""

    # Coerce y values to numbers; skip non-numeric rows for the chart.
    plot_rows: list[tuple[str, float]] = []
    for r in rows:
        label = str(r.get(x_col, ""))
        try:
            val = float(r.get(y_col))
        except (TypeError, ValueError):
            continue
        plot_rows.append((label, val))

    if not plot_rows:
        return ""

    chart_type = (viz.chart_type or "bar").lower()
    if chart_type == "pie":
        return _render_email_pie(plot_rows)
    # bar / line / area / scatter / fallback all render as horizontal bars in email.
    return _render_email_bars(plot_rows)


def _render_email_bars(plot_rows: list[tuple[str, float]]) -> str:
    max_val = max((abs(v) for _, v in plot_rows), default=0)
    if max_val == 0:
        return ""
    rows_html = []
    for i, (label, val) in enumerate(plot_rows[:20]):
        pct = max(2, int(round(abs(val) / max_val * 100)))
        color = _EMAIL_CHART_COLORS[i % len(_EMAIL_CHART_COLORS)]
        rows_html.append(
            f'<tr>'
            f'<td style="padding:4px 8px 4px 0;font-size:12px;color:#444;white-space:nowrap;width:30%;">{html.escape(label)}</td>'
            f'<td style="padding:4px 0;width:55%;">'
            f'<div style="background:{color};height:14px;width:{pct}%;border-radius:3px;"></div>'
            f'</td>'
            f'<td style="padding:4px 0 4px 8px;font-size:12px;color:#222;text-align:right;white-space:nowrap;">{_fmt_num(val)}</td>'
            f'</tr>'
        )
    return (
        '<table role="presentation" style="border-collapse:collapse;width:100%;'
        'margin:8px 0 14px 0;table-layout:fixed;">'
        f'{"".join(rows_html)}'
        '</table>'
    )


def _render_email_pie(plot_rows: list[tuple[str, float]]) -> str:
    total = sum(abs(v) for _, v in plot_rows) or 1.0

    # Proportional stacked bar — gives the email a visible chart shape since
    # SVG/canvas can't be relied on across email clients.
    seg_cells = []
    for i, (_, val) in enumerate(plot_rows):
        pct = max(0.5, abs(val) / total * 100)
        color = _EMAIL_CHART_COLORS[i % len(_EMAIL_CHART_COLORS)]
        seg_cells.append(
            f'<td style="background:{color};height:18px;width:{pct:.2f}%;"></td>'
        )
    stacked_bar = (
        '<table role="presentation" style="border-collapse:collapse;width:100%;'
        'border-radius:6px;overflow:hidden;margin:8px 0 12px 0;table-layout:fixed;">'
        f'<tr>{"".join(seg_cells)}</tr>'
        '</table>'
    )

    legend_rows = []
    for i, (label, val) in enumerate(plot_rows):
        pct = abs(val) / total * 100
        color = _EMAIL_CHART_COLORS[i % len(_EMAIL_CHART_COLORS)]
        legend_rows.append(
            f'<tr>'
            f'<td style="padding:4px 8px 4px 0;width:14px;">'
            f'<div style="width:10px;height:10px;border-radius:50%;background:{color};"></div>'
            f'</td>'
            f'<td style="padding:4px 8px 4px 0;font-size:12px;color:#444;">{html.escape(label)}</td>'
            f'<td style="padding:4px 8px 4px 0;font-size:12px;color:#222;text-align:right;width:80px;">{_fmt_num(val)}</td>'
            f'<td style="padding:4px 0;font-size:12px;color:#888;text-align:right;width:50px;">{pct:.0f}%</td>'
            f'</tr>'
        )
    legend = (
        '<table role="presentation" style="border-collapse:collapse;'
        'margin:0 0 14px 0;">'
        f'{"".join(legend_rows)}'
        '</table>'
    )

    return stacked_bar + legend


def _fmt_num(v: float) -> str:
    if v == int(v):
        return f"{int(v):,}"
    return f"{v:,.2f}"


def _render_error_section(viz: SavedVisualization, error: str) -> str:
    return f"""<section style="margin:24px 0;">
  <h2 style="margin:0 0 6px 0;font-size:16px;">{html.escape(viz.name)}</h2>
  <p style="color:#b91c1c;background:#fef2f2;padding:10px;border-radius:4px;font-size:13px;">
    Could not render this visualization: {html.escape(error[:300])}
  </p>
</section>"""


def _render_html_table(rows: list[dict]) -> str:
    if not rows:
        return ""
    headers = list(rows[0].keys())
    th = "".join(
        f'<th style="text-align:left;padding:6px 10px;background:#f3f4f6;border:1px solid #e5e7eb;font-size:13px;">{html.escape(str(h))}</th>'
        for h in headers
    )
    body_rows = []
    for r in rows:
        tds = "".join(
            f'<td style="padding:6px 10px;border:1px solid #e5e7eb;font-size:13px;">{html.escape(str(r.get(h, "")))}</td>'
            for h in headers
        )
        body_rows.append(f"<tr>{tds}</tr>")
    return (
        '<table style="border-collapse:collapse;width:100%;margin-top:6px;">'
        f"<thead><tr>{th}</tr></thead><tbody>{''.join(body_rows)}</tbody></table>"
    )


def _parse_pretty_table(result_text: str) -> list[dict]:
    """Parse tabulate 'pretty' output into list of dicts.

    Mirrors the parser in api/conversations.py and api/visualizations.py — kept
    inline to avoid a circular import between services and api.
    """
    lines = result_text.strip().split("\n")
    if not lines:
        return []
    if lines[0].startswith("+") or lines[0].startswith("|"):
        data_lines = [l for l in lines if l.startswith("|")]
        if len(data_lines) < 2:
            return []
        headers = [h.strip() for h in data_lines[0].split("|") if h.strip()]
        rows: list[dict] = []
        for line in data_lines[1:]:
            raw_parts = line.split("|")[1:-1]
            values = [v.strip() for v in raw_parts]
            if len(values) == len(headers):
                row: dict = {}
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
    # Tab fallback
    headers = [h.strip() for h in lines[0].split("\t")]
    rows = []
    for line in lines[1:]:
        values = [v.strip() for v in line.split("\t")]
        if len(values) == len(headers):
            rows.append({h: v for h, v in zip(headers, values)})
    return rows


# ---------- Helpers used by chat tools ----------

def find_reports_by_name(db: Session, *, user: User, query: str) -> list[Report]:
    """Case-insensitive substring search over the user's reports."""
    rows = (
        db.query(Report)
        .filter(Report.user_id == user.id)
        .order_by(Report.updated_at.desc())
        .all()
    )
    q = (query or "").strip().lower()
    if not q:
        return list(rows)
    return [r for r in rows if q in (r.name or "").lower()]


def create_visualization_for_report(
    db: Session,
    *,
    user: User,
    name: str,
    sql_query: str,
    chart_type: str,
    chart_config: str,
    warehouse_id: Optional[str],
    local_duckdb_id: Optional[str] = None,
    description: Optional[str] = None,
) -> SavedVisualization:
    """Persist a SavedVisualization. Used when creating a report from chat."""
    if warehouse_id:
        warehouse = db.query(WarehouseConnection).filter(
            WarehouseConnection.id == warehouse_id,
            WarehouseConnection.user_id == user.id,
        ).first()
        if not warehouse:
            raise ValueError("Warehouse not found")

    if local_duckdb_id:
        local_db = db.query(LocalDuckDB).filter(
            LocalDuckDB.id == local_duckdb_id,
            LocalDuckDB.user_id == user.id,
        ).first()
        if not local_db:
            raise ValueError("Local data source not found")

    # Reuse existing viz for the same SQL + source if present, to avoid duplicates
    existing = db.query(SavedVisualization).filter(
        SavedVisualization.user_id == user.id,
        SavedVisualization.sql_query == sql_query,
        SavedVisualization.warehouse_id == warehouse_id,
        SavedVisualization.local_duckdb_id == local_duckdb_id,
    ).first()
    if existing:
        return existing

    viz = SavedVisualization(
        id=str(uuid.uuid4()),
        user_id=user.id,
        name=name,
        description=description,
        chart_type=chart_type,
        chart_config=chart_config,
        sql_query=sql_query,
        warehouse_id=warehouse_id,
        local_duckdb_id=local_duckdb_id,
    )
    db.add(viz)
    db.commit()
    db.refresh(viz)
    return viz
