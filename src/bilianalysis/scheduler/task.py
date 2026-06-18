"""Task 抽象接口与上下文模型。"""
from abc import ABC, abstractmethod
from typing import Literal

from pydantic import BaseModel

from bilianalysis.config.model import AppConfig
from bilianalysis.engine.base import AnalysisEngine


class TaskResult(BaseModel):
    """单个 Task 的执行结果。"""
    task_name: str
    status: Literal["success", "failed", "skipped"]
    duration_seconds: float
    output: dict = {}
    error: str | None = None


class TaskContext(BaseModel):
    """Task 执行上下文——携带配置、引擎、上游结果。"""
    model_config = {"arbitrary_types_allowed": True}

    config: AppConfig
    engine: AnalysisEngine | None = None
    previous: dict[str, TaskResult] = {}
    shared: dict = {}


class Task(ABC):
    """Task 抽象基类。子类必须设置 name 并实现 async run()。"""
    name: str = ""

    @abstractmethod
    async def run(self, ctx: TaskContext) -> TaskResult:
        """执行任务。内部负责异常捕获，永远不抛异常。"""
        ...
