"""
Spatial and queue analytics package.
"""

from src.analytics.spatial import is_point_in_polygon, is_person_in_queue
from src.analytics.queue_math import (
    calculate_expected_wait_time,
    compute_queue_snapshot,
    calculate_mae,
    calculate_rmse,
    calculate_mape,
    evaluate_predictions,
)

__all__ = [
    "is_point_in_polygon",
    "is_person_in_queue",
    "calculate_expected_wait_time",
    "compute_queue_snapshot",
    "calculate_mae",
    "calculate_rmse",
    "calculate_mape",
    "evaluate_predictions",
]
