"""
Unit tests for functional spatial and queue analytics modules.
Pure math testing with zero video/hardware dependencies.
"""

import pytest
from src.schema import Point, BoundingBox, TrackedPerson
from src.analytics.spatial import is_point_in_polygon, is_person_in_queue
from src.analytics.queue_math import (
    calculate_expected_wait_time,
    compute_queue_snapshot,
    calculate_mae,
    calculate_rmse,
    calculate_mape,
)


@pytest.fixture
def square_polygon():
    """Simple 1x1 unit square polygon."""
    return (
        Point(0.0, 0.0),
        Point(1.0, 0.0),
        Point(1.0, 1.0),
        Point(0.0, 1.0),
    )


def test_point_in_polygon_inside(square_polygon):
    inside_point = Point(0.5, 0.5)
    assert is_point_in_polygon(inside_point, square_polygon) is True


def test_point_in_polygon_outside(square_polygon):
    outside_point = Point(1.5, 0.5)
    assert is_point_in_polygon(outside_point, square_polygon) is False


def test_person_in_queue_feet_level(square_polygon):
    # Person whose bottom center (feet) is inside the polygon
    box_inside = BoundingBox(x1=0.2, y1=0.2, x2=0.4, y2=0.8)
    assert is_person_in_queue(box_inside.bottom_center, square_polygon) is True

    # Person standing outside
    box_outside = BoundingBox(x1=1.2, y1=0.2, x2=1.4, y2=0.8)
    assert is_person_in_queue(box_outside.bottom_center, square_polygon) is False


def test_expected_wait_time():
    # 10 patients in queue, service rate of 2 patients per minute = 5 minutes = 300 seconds
    ewt = calculate_expected_wait_time(queue_length=10, service_rate_per_min=2.0)
    assert ewt == 300.0

    # 0 patients = 0 wait time
    assert calculate_expected_wait_time(0, 2.0) == 0.0


def test_compute_queue_snapshot(square_polygon):
    p1 = TrackedPerson(
        track_id=1,
        box=BoundingBox(0.1, 0.1, 0.3, 0.5),
        centroid=Point(0.2, 0.3),
        bottom_point=Point(0.2, 0.5),
        confidence=0.9,
        first_seen_timestamp=0.0,
        last_seen_timestamp=10.0,
        is_in_queue=True,
    )
    p2 = TrackedPerson(
        track_id=2,
        box=BoundingBox(1.1, 0.1, 1.3, 0.5),
        centroid=Point(1.2, 0.3),
        bottom_point=Point(1.2, 0.5),
        confidence=0.85,
        first_seen_timestamp=2.0,
        last_seen_timestamp=6.0,
        is_in_queue=False,
    )

    snapshot = compute_queue_snapshot(
        frame_index=100,
        timestamp=10.0,
        tracks=[p1, p2],
        service_rate_per_min=1.0,
    )

    assert snapshot.in_queue_count == 1
    assert snapshot.out_of_queue_count == 1
    assert snapshot.total_active_tracks == 2
    assert snapshot.active_queue_ids == (1,)
    assert snapshot.avg_dwell_time_sec == 10.0
    assert snapshot.estimated_wait_time_sec == 60.0  # 1 patient / 1 per min = 60s


def test_evaluation_error_metrics():
    actuals = [10.0, 20.0, 30.0]
    preds = [12.0, 18.0, 33.0]

    # MAE = (|10-12| + |20-18| + |30-33|) / 3 = (2 + 2 + 3) / 3 = 2.333...
    mae = calculate_mae(actuals, preds)
    assert pytest.approx(mae, 0.01) == 2.333

    # RMSE = sqrt((4 + 4 + 9) / 3) = sqrt(17/3) = sqrt(5.666) = 2.38
    rmse = calculate_rmse(actuals, preds)
    assert pytest.approx(rmse, 0.01) == 2.38

    # MAPE = 100/3 * (|2/10| + |2/20| + |3/30|) = 100/3 * (0.2 + 0.1 + 0.1) = 13.33%
    mape = calculate_mape(actuals, preds)
    assert pytest.approx(mape, 0.01) == 13.33
