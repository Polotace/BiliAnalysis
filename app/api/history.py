"""Execution history persistence to CSV."""
import csv
from pathlib import Path

from bilianalysis.scheduler.models import RunRecord

HISTORY_FILE = Path("data/run_history.csv")
FIELDS = ["run_id", "pipeline", "trigger", "started_at", "finished_at", "status", "step_count", "failed_step", "error"]


def save_record(record: RunRecord) -> None:
    """Append a RunRecord to the history CSV file."""
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    exists = HISTORY_FILE.exists()
    failed = ""
    error_msg = ""
    for sr in record.step_results:
        if sr.status == "failed":
            # sanitize to single-line to avoid embedding newlines in CSV fields
            failed = " ".join(str(sr.task_name).split())
            error_msg = " ".join(str(sr.error or "").split())
            break
    row = {
        "run_id": record.run_id,
        "pipeline": " ".join(str(record.pipeline).split()),
        "trigger": record.trigger,
        "started_at": record.started_at.isoformat() if record.started_at else "",
        "finished_at": record.finished_at.isoformat() if record.finished_at else "",
        "status": record.status if record.status else "running",
        "step_count": len(record.step_results),
        "failed_step": failed,
        "error": error_msg,
    }
    with open(HISTORY_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS, quoting=csv.QUOTE_ALL)
        if not exists:
            writer.writeheader()
        writer.writerow(row)


def load_records() -> list[dict]:
    """Load all records from CSV, newest first. Returns list of dicts."""
    if not HISTORY_FILE.exists():
        return []
    with open(HISTORY_FILE, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    rows.reverse()
    return rows
