"""Data warehouse layered builder — DWD / DWS / ADS.

Pure computation. No database access.
"""
from .report import WarehouseReport

try:
    from .builder import build_warehouse
except ImportError:
    build_warehouse = None  # builder.py not yet created (Task 5)

__all__ = ["WarehouseReport", "build_warehouse"]
