"""
Pure mathematical metric calculations for queue analytics.

All functions here are pure: (inputs) -> float. No I/O, no side effects.
These implement the queueing theory and statistical error metrics
defined in the thesis.
"""

import math
from typing import Sequence

from src.domain.schema import QueueSnapshot, TrackedPerson, EvaluationReport, Zone


def calculate_expected_wait_time(
    queue_length: int, service_rate_per_min: float
) -> float:
    """
    Calculate Expected Wait Time (EWT) based on queueing theory fundamentals.
    EWT = Queue_Length / Service_Rate (in seconds)

    Args:
        queue_length: Number of patients currently waiting in the queue.
        service_rate_per_min: Average rate of patients serviced per minute (mu).

    Returns:
        Estimated wait time in seconds.
    """
    if queue_length <= 0 or service_rate_per_min <= 0:
        return 0.0

    wait_time_minutes = queue_length / service_rate_per_min
    return wait_time_minutes * 60.0


def compute_queue_snapshot(
    frame_index: int,
    timestamp: float,
    tracks: Sequence[TrackedPerson],
    service_rate_per_min: float,
    zones: Sequence[Zone] = (),
) -> QueueSnapshot:
    """
    Pure transformation mapping active temporal tracks into a QueueSnapshot.

    When *zones* is provided, per-zone membership counts are derived from each
    track's ``in_zone_ids`` field.  When omitted (or empty), the legacy
    single-zone ``is_in_queue`` flag is used and ``zone_counts`` is empty —
    preserving backward-compatible single-zone behaviour.

    Args:
        frame_index: Frame index number.
        timestamp: Current video/stream timestamp in seconds.
        tracks: Sequence of active tracked persons in the current frame.
        service_rate_per_min: Service rate hyperparameter.
        zones: Sequence of Zone definitions (each with an ``id`` and ``points``)
            used to compute per-zone counts.

    Returns:
        Immutable QueueSnapshot object.
    """
    in_queue_tracks = [t for t in tracks if t.is_in_queue]
    out_of_queue_tracks = [t for t in tracks if not t.is_in_queue]

    in_queue_count = len(in_queue_tracks)
    out_count = len(out_of_queue_tracks)

    if in_queue_count > 0:
        avg_dwell = sum(t.dwell_duration_sec for t in in_queue_tracks) / in_queue_count
    else:
        avg_dwell = 0.0

    ewt = calculate_expected_wait_time(in_queue_count, service_rate_per_min)

    zone_counts = {
        zone.id: sum(1 for t in tracks if zone.id in t.in_zone_ids) for zone in zones
    }

    return QueueSnapshot(
        timestamp=timestamp,
        frame_index=frame_index,
        in_queue_count=in_queue_count,
        out_of_queue_count=out_count,
        total_active_tracks=len(tracks),
        active_queue_ids=tuple(t.track_id for t in in_queue_tracks),
        avg_dwell_time_sec=avg_dwell,
        estimated_wait_time_sec=ewt,
        zone_counts=zone_counts,
    )


def calculate_mae(actuals: Sequence[float], predictions: Sequence[float]) -> float:
    """Mean Absolute Error (MAE) = 1/n * sum(|actual - predicted|)."""
    if not actuals or len(actuals) != len(predictions):
        return 0.0
    n = len(actuals)
    return sum(abs(act - pred) for act, pred in zip(actuals, predictions)) / n


def calculate_rmse(actuals: Sequence[float], predictions: Sequence[float]) -> float:
    """Root Mean Squared Error (RMSE) = sqrt(1/n * sum((actual - predicted)^2))."""
    if not actuals or len(actuals) != len(predictions):
        return 0.0
    n = len(actuals)
    mse = sum((act - pred) ** 2 for act, pred in zip(actuals, predictions)) / n
    return math.sqrt(mse)


def calculate_mape(actuals: Sequence[float], predictions: Sequence[float]) -> float:
    """Mean Absolute Percentage Error (MAPE) = 100/n * sum(|actual - pred| / actual)."""
    if not actuals or len(actuals) != len(predictions):
        return 0.0
    valid_pairs = [(act, pred) for act, pred in zip(actuals, predictions) if act > 0]
    if not valid_pairs:
        return 0.0
    return (100.0 / len(valid_pairs)) * sum(
        abs(act - pred) / act for act, pred in valid_pairs
    )
