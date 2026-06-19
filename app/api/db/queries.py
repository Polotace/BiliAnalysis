"""Database queries: encapsulated SQL patterns for business API endpoints.

All functions take an AsyncSession and return plain dicts/Pydantic models — no FastAPI
or HTTP concerns. This is the ONLY module (besides loader.py and schema.py) allowed to
import sqlalchemy.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel
from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from .schema import (
    WeeklyModel, CreatorModel, CategoryModel, VideoModel,
    VideoStatModel, WeeklyVideoModel,
)


# ═══ Response models ═══

class WeekItem(BaseModel):
    number: int
    subject: str | None
    name: str | None
    label: str | None
    cover: str | None
    start_time: datetime | None
    end_time: datetime | None
    video_count: int


class WeekDetail(BaseModel):
    number: int
    subject: str | None
    name: str | None
    label: str | None
    cover: str | None
    start_time: datetime | None
    end_time: datetime | None
    videos: list["VideoSummary"]


class VideoSummary(BaseModel):
    aid: int
    bvid: str | None
    title: str | None
    cover_url: str | None
    duration: int | None
    pubdate: datetime | None
    creator_name: str | None
    category_name: str | None
    view: int | None
    like_cnt: int | None


class VideoDetail(BaseModel):
    aid: int
    bvid: str | None
    title: str | None
    description: str | None
    duration: int | None
    pubdate: datetime | None
    cid: int | None
    video_url: str | None
    cover_url: str | None
    copyright: int | None
    creator_mid: int | None
    creator_name: str | None
    creator_face: str | None
    category_tid: int | None
    category_name: str | None
    category_v2_name: str | None
    view: int | None
    like_cnt: int | None
    coin: int | None
    favorite: int | None
    share: int | None
    reply: int | None
    danmaku: int | None
    appeared_weeks: list[int]


class CreatorSummary(BaseModel):
    mid: int
    name: str | None
    face: str | None
    video_count: int
    total_views: int | None


class CreatorDetail(BaseModel):
    mid: int
    name: str | None
    face: str | None
    video_count: int
    total_views: int | None
    total_likes: int | None
    total_coins: int | None
    total_favorites: int | None
    videos: list[VideoSummary]


class CategorySummary(BaseModel):
    tid: int
    tname: str | None
    tid_v2: int | None
    tname_v2: str | None
    pid_v2: int | None
    pid_name_v2: str | None
    video_count: int


class PaginatedVideos(BaseModel):
    videos: list[VideoSummary]
    total: int
    page: int
    page_size: int


class PaginatedCreators(BaseModel):
    creators: list[CreatorSummary]
    total: int
    page: int
    page_size: int


# ═══ Shared building blocks ═══

_VIDEO_SUMMARY_COLS = [
    VideoModel.aid,
    VideoModel.bvid,
    VideoModel.title,
    VideoModel.cover_url,
    VideoModel.duration,
    VideoModel.pubdate,
    CreatorModel.name.label("creator_name"),
    CategoryModel.tname.label("category_name"),
    VideoStatModel.view,
    VideoStatModel.like_cnt,
]


def _build_video_summary_query():
    """Return a select() that joins video → creator → category → video_stat."""
    return (
        select(*_VIDEO_SUMMARY_COLS)
        .select_from(VideoModel)
        .outerjoin(CreatorModel, VideoModel.creator_mid == CreatorModel.mid)
        .outerjoin(CategoryModel, VideoModel.category_tid == CategoryModel.tid)
        .outerjoin(VideoStatModel, VideoModel.aid == VideoStatModel.aid)
    )


def _row_to_video_summary(row) -> VideoSummary:
    """Map a query row to VideoSummary."""
    return VideoSummary(
        aid=row.aid,
        bvid=row.bvid,
        title=row.title,
        cover_url=row.cover_url,
        duration=row.duration,
        pubdate=row.pubdate,
        creator_name=row.creator_name,
        category_name=row.category_name,
        view=row.view,
        like_cnt=row.like_cnt,
    )


# ═══ Weeks ═══

async def get_weeks(session: AsyncSession) -> list[WeekItem]:
    """Return all weekly issues with video counts, newest first."""
    stmt = (
        select(
            WeeklyModel,
            func.count(WeeklyVideoModel.aid).label("video_count"),
        )
        .outerjoin(WeeklyVideoModel, WeeklyModel.number == WeeklyVideoModel.weekly_number)
        .group_by(WeeklyModel.number)
        .order_by(desc(WeeklyModel.number))
    )
    result = await session.execute(stmt)
    rows = result.all()
    return [
        WeekItem(
            number=row.WeeklyModel.number,
            subject=row.WeeklyModel.subject,
            name=row.WeeklyModel.name,
            label=row.WeeklyModel.label,
            cover=row.WeeklyModel.cover,
            start_time=row.WeeklyModel.start_time,
            end_time=row.WeeklyModel.end_time,
            video_count=row.video_count,
        )
        for row in rows
    ]


async def get_week(session: AsyncSession, week_number: int) -> WeekDetail | None:
    """Return a single week with its videos, or None if not found."""
    weekly = await session.get(WeeklyModel, week_number)
    if weekly is None:
        return None

    stmt = (
        _build_video_summary_query()
        .join(WeeklyVideoModel, VideoModel.aid == WeeklyVideoModel.aid)
        .where(WeeklyVideoModel.weekly_number == week_number)
        .order_by(desc(VideoStatModel.view))
    )
    result = await session.execute(stmt)
    videos = [_row_to_video_summary(row) for row in result.all()]

    return WeekDetail(
        number=weekly.number,
        subject=weekly.subject,
        name=weekly.name,
        label=weekly.label,
        cover=weekly.cover,
        start_time=weekly.start_time,
        end_time=weekly.end_time,
        videos=videos,
    )


# ═══ Videos ═══

async def get_videos(
    session: AsyncSession,
    *,
    page: int = 1,
    page_size: int = 20,
    week_number: int | None = None,
    category_tid: int | None = None,
    creator_mid: int | None = None,
    search: str | None = None,
    sort_by: str = "view",
) -> PaginatedVideos:
    """Paginated video list with optional filters and sorting.

    Args:
        page: 1-indexed page number.
        page_size: Items per page (clamped 1–100).
        week_number: Filter by week.
        category_tid: Filter by category.
        creator_mid: Filter by creator/UP主.
        search: Title substring search (ILIKE).
        sort_by: "view" (default), "like", "pubdate".
    """
    page_size = max(1, min(page_size, 100))
    offset = (page - 1) * page_size

    base = _build_video_summary_query()

    # Filters
    conditions = []
    if week_number is not None:
        base = base.join(WeeklyVideoModel, VideoModel.aid == WeeklyVideoModel.aid)
        conditions.append(WeeklyVideoModel.weekly_number == week_number)
    if category_tid is not None:
        conditions.append(VideoModel.category_tid == category_tid)
    if creator_mid is not None:
        conditions.append(VideoModel.creator_mid == creator_mid)
    if search:
        conditions.append(VideoModel.title.ilike(f"%{search}%"))

    if conditions:
        base = base.where(and_(*conditions))

    # Count total
    count_stmt = select(func.count()).select_from(base.subquery())
    total_result = await session.execute(count_stmt)
    total = total_result.scalar() or 0

    # Sort
    sort_map = {
        "view": desc(VideoStatModel.view),
        "like": desc(VideoStatModel.like_cnt),
        "pubdate": desc(VideoModel.pubdate),
    }
    order_col = sort_map.get(sort_by, desc(VideoStatModel.view))

    base = base.order_by(order_col).limit(page_size).offset(offset)

    result = await session.execute(base)
    videos = [_row_to_video_summary(row) for row in result.all()]

    return PaginatedVideos(
        videos=videos,
        total=total,
        page=page,
        page_size=page_size,
    )


async def get_video(session: AsyncSession, aid: int) -> VideoDetail | None:
    """Return a single video with full detail, stats, and appeared weeks."""
    stmt = (
        select(
            VideoModel,
            CreatorModel.name.label("creator_name"),
            CreatorModel.face.label("creator_face"),
            CategoryModel.tname.label("category_name"),
            CategoryModel.tname_v2.label("category_v2_name"),
            VideoStatModel.view,
            VideoStatModel.like_cnt,
            VideoStatModel.coin,
            VideoStatModel.favorite,
            VideoStatModel.share,
            VideoStatModel.reply,
            VideoStatModel.danmaku,
        )
        .select_from(VideoModel)
        .outerjoin(CreatorModel, VideoModel.creator_mid == CreatorModel.mid)
        .outerjoin(CategoryModel, VideoModel.category_tid == CategoryModel.tid)
        .outerjoin(VideoStatModel, VideoModel.aid == VideoStatModel.aid)
        .where(VideoModel.aid == aid)
    )
    result = await session.execute(stmt)
    row = result.one_or_none()
    if row is None:
        return None

    # Appeared weeks
    weeks_stmt = (
        select(WeeklyVideoModel.weekly_number)
        .where(WeeklyVideoModel.aid == aid)
        .order_by(desc(WeeklyVideoModel.weekly_number))
    )
    weeks_result = await session.execute(weeks_stmt)
    appeared_weeks = [w for (w,) in weeks_result.all()]

    return VideoDetail(
        aid=row.VideoModel.aid,
        bvid=row.VideoModel.bvid,
        title=row.VideoModel.title,
        description=row.VideoModel.description,
        duration=row.VideoModel.duration,
        pubdate=row.VideoModel.pubdate,
        cid=row.VideoModel.cid,
        video_url=row.VideoModel.video_url,
        cover_url=row.VideoModel.cover_url,
        copyright=row.VideoModel.copyright,
        creator_mid=row.VideoModel.creator_mid,
        creator_name=row.creator_name,
        creator_face=row.creator_face,
        category_tid=row.VideoModel.category_tid,
        category_name=row.category_name,
        category_v2_name=row.category_v2_name,
        view=row.view,
        like_cnt=row.like_cnt,
        coin=row.coin,
        favorite=row.favorite,
        share=row.share,
        reply=row.reply,
        danmaku=row.danmaku,
        appeared_weeks=appeared_weeks,
    )


# ═══ Creators ═══

async def get_creators(
    session: AsyncSession,
    *,
    page: int = 1,
    page_size: int = 20,
    sort_by: str = "video_count",
) -> PaginatedCreators:
    """Paginated creator list with aggregated stats.

    Args:
        page: 1-indexed page number.
        page_size: Items per page (clamped 1–100).
        sort_by: "video_count" (default), "total_views", "name".
    """
    page_size = max(1, min(page_size, 100))
    offset = (page - 1) * page_size

    base = (
        select(
            CreatorModel.mid,
            CreatorModel.name,
            CreatorModel.face,
            func.count(func.distinct(WeeklyVideoModel.aid)).label("video_count"),
            func.sum(VideoStatModel.view).label("total_views"),
        )
        .select_from(CreatorModel)
        .outerjoin(VideoModel, VideoModel.creator_mid == CreatorModel.mid)
        .outerjoin(VideoStatModel, VideoModel.aid == VideoStatModel.aid)
        .outerjoin(WeeklyVideoModel, VideoModel.aid == WeeklyVideoModel.aid)
        .group_by(CreatorModel.mid, CreatorModel.name, CreatorModel.face)
    )

    # Count total
    sub = base.subquery()
    count_stmt = select(func.count()).select_from(sub)
    total_result = await session.execute(count_stmt)
    total = total_result.scalar() or 0

    # Sort
    sort_map = {
        "video_count": desc(func.count(func.distinct(WeeklyVideoModel.aid))),
        "total_views": desc(func.sum(VideoStatModel.view)),
        "name": CreatorModel.name,
    }
    order_col = sort_map.get(sort_by, desc(func.count(func.distinct(WeeklyVideoModel.aid))))

    base = base.order_by(order_col).limit(page_size).offset(offset)

    result = await session.execute(base)
    rows = result.all()

    creators = [
        CreatorSummary(
            mid=row.mid,
            name=row.name,
            face=row.face,
            video_count=row.video_count,
            total_views=row.total_views,
        )
        for row in rows
    ]

    return PaginatedCreators(
        creators=creators,
        total=total,
        page=page,
        page_size=page_size,
    )


async def get_creator(session: AsyncSession, mid: int) -> CreatorDetail | None:
    """Return a single creator with aggregated stats and their videos."""
    # Aggregated stats
    stats_stmt = (
        select(
            CreatorModel.mid,
            CreatorModel.name,
            CreatorModel.face,
            func.count(func.distinct(WeeklyVideoModel.aid)).label("video_count"),
            func.sum(VideoStatModel.view).label("total_views"),
            func.sum(VideoStatModel.like_cnt).label("total_likes"),
            func.sum(VideoStatModel.coin).label("total_coins"),
            func.sum(VideoStatModel.favorite).label("total_favorites"),
        )
        .select_from(CreatorModel)
        .outerjoin(VideoModel, VideoModel.creator_mid == CreatorModel.mid)
        .outerjoin(VideoStatModel, VideoModel.aid == VideoStatModel.aid)
        .outerjoin(WeeklyVideoModel, VideoModel.aid == WeeklyVideoModel.aid)
        .where(CreatorModel.mid == mid)
        .group_by(CreatorModel.mid, CreatorModel.name, CreatorModel.face)
    )
    result = await session.execute(stats_stmt)
    row = result.one_or_none()
    if row is None:
        return None

    # Videos by this creator
    v_stmt = (
        _build_video_summary_query()
        .where(VideoModel.creator_mid == mid)
        .order_by(desc(VideoStatModel.view))
        .limit(100)
    )
    v_result = await session.execute(v_stmt)
    videos = [_row_to_video_summary(r) for r in v_result.all()]

    return CreatorDetail(
        mid=row.mid,
        name=row.name,
        face=row.face,
        video_count=row.video_count,
        total_views=row.total_views,
        total_likes=row.total_likes,
        total_coins=row.total_coins,
        total_favorites=row.total_favorites,
        videos=videos,
    )


# ═══ Categories ═══

async def get_categories(session: AsyncSession) -> list[CategorySummary]:
    """Return all categories with video counts, ordered by count descending."""
    stmt = (
        select(
            CategoryModel,
            func.count(func.distinct(VideoModel.aid)).label("video_count"),
        )
        .outerjoin(VideoModel, VideoModel.category_tid == CategoryModel.tid)
        .group_by(CategoryModel.tid)
        .order_by(desc(func.count(func.distinct(VideoModel.aid))))
    )
    result = await session.execute(stmt)
    rows = result.all()
    return [
        CategorySummary(
            tid=row.CategoryModel.tid,
            tname=row.CategoryModel.tname,
            tid_v2=row.CategoryModel.tid_v2,
            tname_v2=row.CategoryModel.tname_v2,
            pid_v2=row.CategoryModel.pid_v2,
            pid_name_v2=row.CategoryModel.pid_name_v2,
            video_count=row.video_count,
        )
        for row in rows
    ]
