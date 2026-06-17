"""数据存取与进度管理。"""
import datetime
from typing import Any
import json
import asyncio
from pathlib import Path

from pydantic import BaseModel

DATA_DIR = Path("data/raw")
_progress_lock = asyncio.Lock()


class ProgressFile(BaseModel):
    crawled: list[int] = list()
    failed: dict[int, str] = dict()
    last_run: datetime.datetime | None = None


async def save_week(number: int, data: dict[str, Any]) -> None:
    """保存单期 JSON 文件到 data/raw/week_{number:03d}.json。"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    filepath = DATA_DIR / f"week_{number:03d}.json"
    content = json.dumps(data, ensure_ascii=False, indent=2)
    await asyncio.to_thread(filepath.write_text, content, encoding="utf-8")


def _progress_path() -> Path:
    return DATA_DIR / "progress.json"


async def load_progress() -> ProgressFile:
    """读取 progress.json，文件不存在时返回默认空结构。"""
    path = _progress_path()
    if not path.exists():
        return ProgressFile()
    async with _progress_lock:
        text = path.read_text(encoding="utf-8")
        return ProgressFile(**json.loads(text))


async def save_progress(state: ProgressFile) -> None:
    """写入 progress.json。"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    content = state.model_dump_json(ensure_ascii=False, indent=2)
    async with _progress_lock:
        _progress_path().write_text(content, encoding="utf-8")


async def get_pending_weeks(latest_number: int) -> tuple[list[int], list[int]]:
    """对比 progress.json，返回 (retry, pending)。
       retry: 历史失败的期号列表，每次 run 重新尝试一次
       pending: 从未爬取的新期号列表"""
    progress = await load_progress()
    crawled = set(progress.crawled)
    failed = set(int(k) for k in progress.failed.keys())
    all_weeks = set(range(1, latest_number + 1))
    done = crawled - failed
    retry = sorted(failed)
    pending = sorted(all_weeks - done - failed)
    return retry, pending
