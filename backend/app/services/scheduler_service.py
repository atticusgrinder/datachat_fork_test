"""Polling-loop scheduler for report email sends.

A single asyncio task wakes every POLL_INTERVAL_SECONDS, finds report_schedules
where enabled=true and next_send_at <= utcnow(), and dispatches send_report_now
for each. Run state is in the DB — restarts pick up where they left off.
"""

import asyncio
import logging
from datetime import datetime

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.report import ReportSchedule
from app.services import report_service

logger = logging.getLogger(__name__)

POLL_INTERVAL_SECONDS = 60

_task: asyncio.Task | None = None
_stopping = asyncio.Event()


async def _process_due_schedules() -> None:
    """One pass: find due schedules, send each, log failures and continue."""
    db: Session = SessionLocal()
    try:
        now = datetime.utcnow()
        due = (
            db.query(ReportSchedule)
            .filter(ReportSchedule.enabled.is_(True))
            .filter(ReportSchedule.next_send_at.isnot(None))
            .filter(ReportSchedule.next_send_at <= now)
            .all()
        )
        if not due:
            return
        logger.info("Scheduler: %d due schedule(s) to process", len(due))
        for schedule in due:
            try:
                await report_service.send_report_now(db, report_id=schedule.report_id)
            except Exception:
                logger.exception(
                    "Scheduler: failed to send report %s; advancing next_send_at to avoid hot-looping",
                    schedule.report_id,
                )
                # Advance next_send_at even on failure so we don't retry every poll.
                schedule.next_send_at = report_service.compute_next_send_at(
                    schedule, after=now,
                )
                db.commit()
    finally:
        db.close()


async def _scheduler_loop() -> None:
    logger.info("Report scheduler started (poll interval %ds)", POLL_INTERVAL_SECONDS)
    try:
        while not _stopping.is_set():
            try:
                await _process_due_schedules()
            except Exception:
                logger.exception("Scheduler tick failed; continuing")
            try:
                await asyncio.wait_for(_stopping.wait(), timeout=POLL_INTERVAL_SECONDS)
            except asyncio.TimeoutError:
                pass
    finally:
        logger.info("Report scheduler stopped")


def start_scheduler() -> None:
    global _task
    if _task is not None and not _task.done():
        return
    _stopping.clear()
    _task = asyncio.create_task(_scheduler_loop(), name="report-scheduler")


async def stop_scheduler() -> None:
    global _task
    _stopping.set()
    if _task is not None:
        try:
            await _task
        except Exception:
            pass
        _task = None
