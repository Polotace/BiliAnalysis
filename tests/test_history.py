"""Tests for CSV execution history persistence."""

from datetime import datetime, timezone

from api import history
from bilianalysis.scheduler.models import RunRecord
from bilianalysis.scheduler.task import TaskResult


def test_save_record_quotes_and_flattens_csv_fields(tmp_path, monkeypatch):
    history_file = tmp_path / "run_history.csv"
    monkeypatch.setattr(history, "HISTORY_FILE", history_file)

    record = RunRecord(
        pipeline='full, "daily"\ncheck',
        trigger="manual",
        started_at=datetime(2026, 6, 23, 2, 0, tzinfo=timezone.utc),
        finished_at=datetime(2026, 6, 23, 2, 1, tzinfo=timezone.utc),
        status="failed",
        step_results=[
            TaskResult(
                task_name='spark step\nname',
                status="failed",
                duration_seconds=1.0,
                error='bad,\n"input"\r\nline',
            )
        ],
    )

    history.save_record(record)

    raw = history_file.read_text(encoding="utf-8")
    assert raw.splitlines() == [
        '"run_id","pipeline","trigger","started_at","finished_at","status","step_count","failed_step","error"',
        f'"{record.run_id}","full, ""daily"" check","manual","2026-06-23T02:00:00+00:00","2026-06-23T02:01:00+00:00","failed","1","spark step name","bad, ""input"" line"',
    ]


def test_load_records_reads_back_saved_rows(tmp_path, monkeypatch):
    history_file = tmp_path / "run_history.csv"
    monkeypatch.setattr(history, "HISTORY_FILE", history_file)

    history_file.write_text(
        '"run_id","pipeline","trigger","started_at","finished_at","status","step_count","failed_step","error"\n'
        '"a1","pipeline","manual","","","success","1","",""\n'
        '"b2","pipeline","manual","","","failed","2","step","oops"\n',
        encoding="utf-8",
    )

    rows = history.load_records()

    assert [row["run_id"] for row in rows] == ["b2", "a1"]
