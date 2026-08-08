"""
Spatial and queue analytics package.

Spatial functions remain in spatial.py; queue math has been extracted
to src.evaluation/metrics.py but is re-exported here for backward compat.
"""

from src.analytics.spatial import is_point_in_polygon, is_person_in_queue
from src.evaluation.metrics import (
    calculate_expected_wait_time,
    compute_queue_snapshot,
    calculate_mae,
    calculate_rmse,
    calculate_mape,
)

__all__ = [
    "is_point_in_polygon",
    "is_person_in_queue",
    "calculate_expected_wait_time",
    "compute_queue_snapshot",
    "calculate_mae",
    "calculate_rmse",
    "calculate_mape",
]
