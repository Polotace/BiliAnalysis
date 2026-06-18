from datetime import datetime

from pydantic import BaseModel


class Weekly(BaseModel):
    id: int
    number: int
    subject: str
    name: str
    start_time: datetime
    end_time: datetime


class Video(BaseModel):
    aid: int
    bvid: str
    title: str
    desc: str
    duration: int
    pubdate: datetime
    cid: int
    cover_url: str


class Creator(BaseModel):
    mid: int
    name: str
    face: str


class Category(BaseModel):
    pid: int
    pid_name: str
    tidv2: int
    tnamev2: str
    tid: int
    tname: str


class VideoStat(BaseModel):
    aid: int
    view: int
    like: int
    coin: int
    favorite: int
    share: int
    reply: int
    danmaku: int
    '''弹幕量'''