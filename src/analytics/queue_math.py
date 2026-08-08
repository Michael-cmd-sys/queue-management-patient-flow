"""
Backward-compatible re-exports.

Queue math functions have been extracted to src.evaluation/metrics.py.
This module re-exports for backward compatibility.
"""

from src.evaluation.metrics import (
    calculate_expected_wait_time,
    compute_queue_snapshot,
    calculate_mae,
    calculate_rmse,
    calculate_mape,
)

__all__ = [
    "calculate_expected_wait_time",
    "compute_queue_snapshot",
    "calculate_mae",
    "calculate_rmse",
    "calculate_mape",
]
