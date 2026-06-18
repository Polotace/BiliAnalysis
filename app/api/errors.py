"""Business exceptions for API layer."""


class AppError(Exception):
    """Base error with HTTP status code."""
    def __init__(self, status: int, detail: str):
        self.status = status
        self.detail = detail


class TaskNotFound(AppError):
    def __init__(self, name: str):
        super().__init__(404, f"Task '{name}' not found")


class PipelineNotFound(AppError):
    def __init__(self, name: str):
        super().__init__(404, f"Pipeline '{name}' not found")


class ConfigInvalid(AppError):
    def __init__(self, msg: str):
        super().__init__(400, f"Invalid config: {msg}")


class EngineUnavailable(AppError):
    def __init__(self):
        super().__init__(503, "Analysis engine not available")
