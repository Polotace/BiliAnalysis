"""Database loader: read raw JSON from data/raw/, transform, write to PostgreSQL."""
import json
import logging
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from bilianalysis.etl import transform_week
from app.api.db.schema import (
    WeeklyModel, CreatorModel, CategoryModel, VideoModel,
    VideoStatModel, WeeklyVideoModel,
    WeeklyEntity, CreatorEntity, CategoryEntity, VideoEntity,
    VideoStatEntity, WeeklyVideoEntity,
)

logger = logging.getLogger(__name__)


def load_raw_weeks(raw_dir: str | Path) -> list[dict[str, list[dict]]]:
    """Read all week_*.json files from data/raw/, apply transform_week to each.

    Returns a list in week-number ascending order.
    """
    raw_dir = Path(raw_dir)
    files = sorted(raw_dir.glob("week_*.json"),
                   key=lambda p: int(p.stem.split("_")[1]))
    results: list[dict[str, list[dict]]] = []
    for fp in files:
        raw = json.loads(fp.read_text(encoding="utf-8"))
        results.append(transform_week(raw))
    return results


async def load_week(
    pg_session: AsyncSession,
    records: dict[str, list[dict]],
) -> None:
    """Insert one week's records into all 6 tables within a single transaction.

    Insert order respects FK dependencies:
    weekly → creator → category → video → video_stat → weekly_video
    """
    async with pg_session.begin():
        # 1. weekly (single row, immutable)
        w = WeeklyEntity.model_validate(records["weekly"][0])
        await pg_session.execute(
            pg_insert(WeeklyModel).values(w.model_dump()).on_conflict_do_nothing()
        )

        # 2. creators (immutable after first insert)
        for c in records["creators"]:
            ce = CreatorEntity.model_validate(c)
            await pg_session.execute(
                pg_insert(CreatorModel).values(ce.model_dump()).on_conflict_do_nothing()
            )

        # 3. categories (immutable after first insert)
        for c in records["categories"]:
            ce = CategoryEntity.model_validate(c)
            await pg_session.execute(
                pg_insert(CategoryModel).values(ce.model_dump()).on_conflict_do_nothing()
            )

        # 4. videos (update on conflict — same video may reappear with changes)
        for v in records["videos"]:
            ve = VideoEntity.model_validate(v)
            values = ve.model_dump()
            await pg_session.execute(
                pg_insert(VideoModel).values(values).on_conflict_do_update(
                    index_elements=["aid"],
                    set_={k: v for k, v in values.items() if k != "aid"},
                )
            )

        # 5. video_stats (update on conflict — stats change across weeks)
        for vs in records["video_stats"]:
            vse = VideoStatEntity.model_validate(vs)
            values = vse.model_dump()
            await pg_session.execute(
                pg_insert(VideoStatModel).values(values).on_conflict_do_update(
                    index_elements=["aid"],
                    set_={k: v for k, v in values.items() if k != "aid"},
                )
            )

        # 6. weekly_videos (immutable)
        for wv in records["weekly_videos"]:
            wve = WeeklyVideoEntity.model_validate(wv)
            await pg_session.execute(
                pg_insert(WeeklyVideoModel).values(wve.model_dump()).on_conflict_do_nothing()
            )


async def load_incremental(
    pg_session: AsyncSession,
    all_records: list[dict[str, list[dict]]],
) -> dict:
    """Incremental load: query weekly table, skip existing weeks.

    Args:
        pg_session: Database session.
        all_records: Output of load_raw_weeks().

    Returns:
        {"loaded": [1, 2], "skipped": [3, 4], "failed": {5: "error message"}}
    """
    # Query existing week numbers
    result = await pg_session.execute(select(WeeklyModel.number))
    existing = {row[0] for row in result.all()}

    loaded: list[int] = []
    skipped: list[int] = []
    failed: dict[int, str] = {}

    for records in all_records:
        week_num = records["weekly"][0]["number"]

        if week_num in existing:
            skipped.append(week_num)
            continue

        try:
            await load_week(pg_session, records)
            loaded.append(week_num)
        except Exception as exc:
            logger.exception("Failed to load week %s: %s", week_num, exc)
            failed[week_num] = str(exc)

    return {"loaded": loaded, "skipped": skipped, "failed": failed}
