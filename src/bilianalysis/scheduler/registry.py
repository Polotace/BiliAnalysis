"""Task 注册表——装饰器注册 + 按名查询。"""
from .task import Task

_registry: dict[str, type[Task]] = {}


def register(name: str):
    """装饰器：将 Task 子类注册到全局注册表。"""
    def decorator(cls: type[Task]) -> type[Task]:
        if not isinstance(cls, type) or not issubclass(cls, Task):
            raise TypeError(f"'{getattr(cls, '__name__', cls)}' is not a Task subclass")
        if name in _registry:
            raise ValueError(f"Task '{name}' is already registered")
        _registry[name] = cls
        return cls
    return decorator


def get_task(name: str) -> type[Task]:
    """按名获取 Task 类。不存在时抛出 KeyError。"""
    if name not in _registry:
        raise KeyError(f"Task '{name}' not found. Available: {list(_registry)}")
    return _registry[name]


def list_tasks() -> list[str]:
    """列出所有已注册的 Task 名称。"""
    return sorted(_registry.keys())


def clear_registry() -> None:
    """清空注册表（仅用于测试）。"""
    _registry.clear()
