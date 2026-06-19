"""Tests for data warehouse layered builder."""
from bilianalysis.warehouse import WarehouseReport
from bilianalysis.warehouse.report import SkippedWeek


def test_warehouse_report_empty():
    report = WarehouseReport()
    assert report.weeks_processed == 0
    assert report.weeks_skipped == 0
    assert report.skipped_details == []
    assert report.tables_written == []
    assert report.duration_seconds == 0.0


def test_warehouse_report_with_data():
    report = WarehouseReport(
        weeks_processed=4,
        weeks_skipped=1,
        skipped_details=[SkippedWeek(week_number=3, error="JSON decode error")],
        tables_written=["dwd_fact_video.parquet"],
        duration_seconds=1.5,
    )
    assert report.weeks_processed == 4
    assert len(report.skipped_details) == 1
    assert report.skipped_details[0].week_number == 3
