"""WarehouseReport model for build_warehouse() output."""
from pydantic import BaseModel


class SkippedWeek(BaseModel):
    week_number: int
    error: str


class WarehouseReport(BaseModel):
    weeks_processed: int = 0
    weeks_skipped: int = 0
    skipped_details: list[SkippedWeek] = []
    tables_written: list[str] = []
    duration_seconds: float = 0.0
