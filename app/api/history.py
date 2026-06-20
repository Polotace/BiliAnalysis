"""Execution history persistence to CSV."""
import csv
from pathlib import Path

from bilianalysis.scheduler.models import RunRecord

HISTORY_FILE = Path("data/run_history.csv")
FIELDS = ["run_id", "pipeline", "trigger", "started_at", "finished_at", "status", "step_count", "failed_step"]


def save_record(record: RunRecord) -> None:
    """Append a RunRecord to the history CSV file."""
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    exists = HISTORY_FILE.exists()
    failed = ""
    for sr in record.step_results:
        if sr.status == "failed":
            failed = sr.task_name
            break
    row = {
        "run_id": record.run_id,
        "pipeline": record.pipeline,
        "trigger": record.trigger,
        "started_at": record.started_at.isoformat() if record.started_at else "",
        "finished_at": record.finished_at.isoformat() if record.finished_at else "",
        "status": record.status if record.status else "running",
        "step_count": len(record.step_results),
        "failed_step": failed,
    }
    with open(HISTORY_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
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
