"""Orchestration: scan raw JSON → transform → DWD → DWS → ADS → write Parquet."""
import json
import time
from pathlib import Path

from bilianalysis.etl.transform import transform_week
from bilianalysis.warehouse.dwd import build_dwd
from bilianalysis.warehouse.dws import build_dws
from bilianalysis.warehouse.ads import build_ads
from bilianalysis.warehouse.report import WarehouseReport, SkippedWeek


def build_warehouse(raw_dir: Path, warehouse_dir: Path) -> WarehouseReport:
    """Full rebuild of the data warehouse from raw JSON files.

    Args:
        raw_dir: Directory containing week_*.json files.
        warehouse_dir: Directory to write Parquet files to.

    Returns:
        WarehouseReport with processing statistics.
    """
    start = time.monotonic()
    warehouse_dir.mkdir(parents=True, exist_ok=True)

    json_files = sorted(raw_dir.glob("week_*.json"))
    if not json_files:
        return WarehouseReport(duration_seconds=round(time.monotonic() - start, 2))

    all_records = []
    skipped = []
    for json_path in json_files:
        try:
            week_number = int(json_path.stem.split("_")[1])
            raw = json.loads(json_path.read_text(encoding="utf-8"))
            records = transform_week(raw)
            all_records.append(records)
        except Exception as exc:
            skipped.append(SkippedWeek(
                week_number=week_number if "week_number" in dir() else -1,
                error=str(exc),
            ))

    if not all_records:
        return WarehouseReport(
            weeks_skipped=len(skipped),
            skipped_details=skipped,
            duration_seconds=round(time.monotonic() - start, 2),
        )

    dwd_df = build_dwd(all_records)
    tables_written = []
    _write_parquet(dwd_df, warehouse_dir / "dwd_fact_video.parquet")
    tables_written.append("dwd_fact_video.parquet")

    dws_dict = build_dws(dwd_df)
    for name in ["dws_creator", "dws_category", "dws_weekly"]:
        _write_parquet(dws_dict[name], warehouse_dir / f"{name}.parquet")
        tables_written.append(f"{name}.parquet")

    ads_dict = build_ads(dws_dict, dwd_df)
    for name in ["ads_hot_videos", "ads_top_creators", "ads_category_trend", "ads_weekly_kpi"]:
        _write_parquet(ads_dict[name], warehouse_dir / f"{name}.parquet")
        tables_written.append(f"{name}.parquet")

    return WarehouseReport(
        weeks_processed=len(all_records),
        weeks_skipped=len(skipped),
        skipped_details=skipped,
        tables_written=tables_written,
        duration_seconds=round(time.monotonic() - start, 2),
    )


def _write_parquet(df, path: Path) -> None:
    """Write DataFrame to Parquet with atomic tmp→rename."""
    tmp_path = path.with_suffix(".tmp.parquet")
    df.to_parquet(tmp_path, index=False)
    tmp_path.rename(path)
