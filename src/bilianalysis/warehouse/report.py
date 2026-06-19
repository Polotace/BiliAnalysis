"""WarehouseReport model for build_warehouse() output."""
from pydantic import BaseModel, Field


class SkippedWeek(BaseModel):
    week_number: int
    error: str


class WarehouseReport(BaseModel):
    weeks_processed: int = Field(default=0, ge=0)
    weeks_skipped: int = Field(default=0, ge=0)
    skipped_details: list[SkippedWeek] = []
    tables_written: list[str] = []
    duration_seconds: float = Field(default=0.0, ge=0)
