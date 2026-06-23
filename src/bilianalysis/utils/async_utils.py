"""Async utilities shared across the codebase."""
import asyncio
import threading


def safe_run_async(coro):
    """Run an async coroutine from sync code — safe inside or outside event loops.

    Uses ``asyncio.run()`` when no loop is running; spawns a background
    thread when called from within an active event loop (e.g. inside a
    pipeline task).
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    result_holder = []
    exc_holder = []

    def _target():
        try:
            result_holder.append(asyncio.run(coro))
        except Exception as exc:
            exc_holder.append(exc)

    t = threading.Thread(target=_target, daemon=True)
    t.start()
    t.join()
    if exc_holder:
        raise exc_holder[0]
    return result_holder[0] if result_holder else None
