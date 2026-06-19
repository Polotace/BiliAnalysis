"""SQLAlchemy ORM models and Pydantic entities for 6 PostgreSQL tables."""
from datetime import datetime

from pydantic import BaseModel
from sqlalchemy import BigInteger, Integer, Text, DateTime, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


# ═══ ORM Models ═══

class WeeklyModel(Base):
    __tablename__ = "weekly"

    number: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    subject: Mapped[str | None] = mapped_column(Text, nullable=True)
    name: Mapped[str | None] = mapped_column(Text, nullable=True)
    label: Mapped[str | None] = mapped_column(Text, nullable=True)
    cover: Mapped[str | None] = mapped_column(Text, nullable=True)
    start_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    end_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class CreatorModel(Base):
    __tablename__ = "creator"

    mid: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str | None] = mapped_column(Text, nullable=True)
    face: Mapped[str | None] = mapped_column(Text, nullable=True)


class CategoryModel(Base):
    __tablename__ = "category"

    tid: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    tname: Mapped[str | None] = mapped_column(Text, nullable=True)
    tid_v2: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    tname_v2: Mapped[str | None] = mapped_column(Text, nullable=True)
    pid_v2: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pid_name_v2: Mapped[str | None] = mapped_column(Text, nullable=True)


class VideoModel(Base):
    __tablename__ = "video"

    aid: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    bvid: Mapped[str | None] = mapped_column(Text, nullable=True)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pubdate: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cid: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    video_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    cover_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    copyright: Mapped[int | None] = mapped_column(Integer, nullable=True)
    creator_mid: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("creator.mid"), nullable=True)
    category_tid: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("category.tid"), nullable=True)


class VideoStatModel(Base):
    __tablename__ = "video_stat"

    aid: Mapped[int] = mapped_column(BigInteger, ForeignKey("video.aid"), primary_key=True)
    view: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    like_cnt: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    coin: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    favorite: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    share: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    reply: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    danmaku: Mapped[int | None] = mapped_column(BigInteger, nullable=True)


class WeeklyVideoModel(Base):
    __tablename__ = "weekly_video"

    weekly_number: Mapped[int] = mapped_column(BigInteger, ForeignKey("weekly.number"), primary_key=True)
    aid: Mapped[int] = mapped_column(BigInteger, ForeignKey("video.aid"), primary_key=True)


# ═══ Pydantic Entities (used for validation in loader) ═══

class WeeklyEntity(BaseModel):
    number: int
    subject: str | None = None
    name: str | None = None
    label: str | None = None
    cover: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None


class CreatorEntity(BaseModel):
    mid: int
    name: str | None = None
    face: str | None = None


class CategoryEntity(BaseModel):
    tid: int
    tname: str | None = None
    tid_v2: int | None = None
    tname_v2: str | None = None
    pid_v2: int | None = None
    pid_name_v2: str | None = None


class VideoEntity(BaseModel):
    aid: int
    bvid: str | None = None
    title: str | None = None
    description: str | None = None
    duration: int | None = None
    pubdate: datetime | None = None
    cid: int | None = None
    video_url: str | None = None
    cover_url: str | None = None
    copyright: int | None = None
    creator_mid: int | None = None
    category_tid: int | None = None


class VideoStatEntity(BaseModel):
    aid: int
    view: int | None = None
    like_cnt: int | None = None
    coin: int | None = None
    favorite: int | None = None
    share: int | None = None
    reply: int | None = None
    danmaku: int | None = None


class WeeklyVideoEntity(BaseModel):
    weekly_number: int
    aid: int
