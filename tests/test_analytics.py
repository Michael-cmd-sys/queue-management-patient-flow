"""
Unit tests for functional spatial and queue analytics modules.
Pure math testing with zero video/hardware dependencies.
"""

import pytest
from src.domain.schema import Point, BoundingBox, TrackedPerson, QueueSnapshot, Zone
from src.analytics.spatial import (
    is_point_in_polygon,
    is_person_in_queue,
    is_person_in_zones,
)
from src.evaluation.metrics import (
    calculate_expected_wait_time,
    compute_queue_snapshot,
    calculate_mae,
    calculate_rmse,
    calculate_mape,
)
from src.evaluation.report import generate_evaluation_report


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


@pytest.fixture
def two_zones():
    """Two overlapping unit-square zones with distinct IDs."""
    return (
        Zone(
            id="zone_a",
            label="Area A",
            points=(
                Point(0.0, 0.0),
                Point(1.0, 0.0),
                Point(1.0, 1.0),
                Point(0.0, 1.0),
            ),
        ),
        Zone(
            id="zone_b",
            label="Area B",
            points=(
                Point(0.5, 0.5),
                Point(2.0, 0.5),
                Point(2.0, 2.0),
                Point(0.5, 2.0),
            ),
        ),
    )


def test_is_person_in_zones_multi_zone(two_zones):
    # Point in zone_a only (top-left of square, outside overlapping region)
    assert is_person_in_zones(Point(0.2, 0.2), two_zones) == ("zone_a",)

    # Point in overlapping region (both zones)
    assert is_person_in_zones(Point(0.7, 0.7), two_zones) == ("zone_a", "zone_b")

    # Point in zone_b only
    assert is_person_in_zones(Point(1.5, 1.5), two_zones) == ("zone_b",)

    # Point outside both zones
    assert is_person_in_zones(Point(3.0, 3.0), two_zones) == ()


def test_compute_queue_snapshot_multi_zone(two_zones):
    p1 = TrackedPerson(
        track_id=1,
        box=BoundingBox(0.1, 0.1, 0.3, 0.5),
        centroid=Point(0.2, 0.3),
        bottom_point=Point(0.2, 0.5),  # inside zone_a only
        confidence=0.9,
        first_seen_timestamp=0.0,
        last_seen_timestamp=10.0,
        is_in_queue=True,
        in_zone_ids=("zone_a",),
    )
    p2 = TrackedPerson(
        track_id=2,
        box=BoundingBox(0.6, 0.6, 0.8, 0.9),
        centroid=Point(0.7, 0.75),
        bottom_point=Point(0.7, 0.9),  # inside both zones
        confidence=0.85,
        first_seen_timestamp=2.0,
        last_seen_timestamp=8.0,
        is_in_queue=True,
        in_zone_ids=("zone_a", "zone_b"),
    )
    p3 = TrackedPerson(
        track_id=3,
        box=BoundingBox(1.5, 1.5, 1.7, 1.9),
        centroid=Point(1.6, 1.7),
        bottom_point=Point(1.6, 1.9),  # inside zone_b only
        confidence=0.8,
        first_seen_timestamp=1.0,
        last_seen_timestamp=9.0,
        is_in_queue=True,
        in_zone_ids=("zone_b",),
    )

    snapshot = compute_queue_snapshot(
        frame_index=0,
        timestamp=0.0,
        tracks=[p1, p2, p3],
        zones=two_zones,
        service_rate_per_min=1.0,
    )

    assert snapshot.in_queue_count == 3
    assert snapshot.zone_counts["zone_a"] == 2  # p1 + p2
    assert snapshot.zone_counts["zone_b"] == 2  # p2 + p3


def test_compute_queue_snapshot_single_zone_backward_compat():
    """Single-zone list of length 1 preserves old behaviour; zone_counts empty."""
    single_zone = (
        Zone(
            id="main",
            label="Main",
            points=(
                Point(0.0, 0.0),
                Point(1.0, 0.0),
                Point(1.0, 1.0),
                Point(0.0, 1.0),
            ),
        ),
    )
    p = TrackedPerson(
        track_id=1,
        box=BoundingBox(0.2, 0.2, 0.4, 0.8),
        centroid=Point(0.3, 0.5),
        bottom_point=Point(0.3, 0.8),
        confidence=0.9,
        first_seen_timestamp=0.0,
        last_seen_timestamp=10.0,
        is_in_queue=True,
        in_zone_ids=("main",),
    )

    snapshot = compute_queue_snapshot(
        frame_index=0,
        timestamp=0.0,
        tracks=[p],
        zones=single_zone,
        service_rate_per_min=1.0,
    )

    assert snapshot.in_queue_count == 1
    assert snapshot.zone_counts == {"main": 1}


def test_compute_queue_snapshot_no_zones_backward_compat():
    """Without zones argument, behaves exactly like the old API (zone_counts empty)."""
    p = TrackedPerson(
        track_id=1,
        box=BoundingBox(0.2, 0.2, 0.4, 0.8),
        centroid=Point(0.3, 0.5),
        bottom_point=Point(0.3, 0.8),
        confidence=0.9,
        first_seen_timestamp=0.0,
        last_seen_timestamp=10.0,
        is_in_queue=True,
    )

    snapshot = compute_queue_snapshot(
        frame_index=0,
        timestamp=0.0,
        tracks=[p],
        service_rate_per_min=1.0,
    )

    assert snapshot.in_queue_count == 1
    assert snapshot.zone_counts == {}


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


@pytest.mark.slow
def test_pipeline_respects_sampling_fps():
    """Pipeline should skip frames when sampling_fps < video fps."""
    from pathlib import Path
    from src.domain.config import (
        PipelineConfig,
        ROIConfig,
        VisionConfig,
        AnalyticsConfig,
    )
    from src.pipeline.runner import run_pipeline

    config = PipelineConfig(
        vision=VisionConfig(model_path=Path("models/best.pt")),
        roi=ROIConfig(
            zones=(
                Zone(
                    id="main",
                    label="Patient Triage Queue Line",
                    points=(
                        Point(0.05, 0.10),
                        Point(0.95, 0.10),
                        Point(0.95, 0.95),
                        Point(0.05, 0.95),
                    ),
                ),
            )
        ),
        video_source=Path("data/input_videos/short video sample/sample.mp4"),
        output_dir=Path("data/output"),
        analytics=AnalyticsConfig(sampling_fps=1.0),
    )
    snapshots = run_pipeline(config)
    # sample.mp4 is ~5078938 bytes, roughly 169s at 30fps = ~5070 frames
    # At 1.0 fps sampling, expect ~169 snapshots
    assert len(snapshots) < 500


def test_generate_evaluation_report():
    """Report generator produces correct MAE/RMSE/MAPE/precision/recall/F1."""
    service_rate_per_min = 3.0  # 3 patients per minute
    # Ground truth: 3 frames where counts are [3, 0, 2]
    ground_truth_counts = [3, 0, 2]
    # Snapshot EWT = count / service_rate * 60 (seconds)
    # predicted waits: 3/3*60=60, 0, 2/3*60=40
    snapshots = [
        QueueSnapshot(
            timestamp=float(i),
            frame_index=i,
            in_queue_count=gc,
            out_of_queue_count=0,
            total_active_tracks=gc,
            active_queue_ids=(1,),
            avg_dwell_time_sec=0.0,
            estimated_wait_time_sec=gc / service_rate_per_min * 60.0,
        )
        for i, gc in enumerate(ground_truth_counts)
    ]

    report = generate_evaluation_report(
        snapshots, ground_truth_counts, service_rate_per_min
    )

    # Predicted counts match ground truth exactly → MAE/RMSE zero for waits,
    # MAPE zero, and precision/recall/F1 = 1.0
    assert report.mae == pytest.approx(0.0, abs=1e-9)
    assert report.rmse == pytest.approx(0.0, abs=1e-9)
    assert report.mape == pytest.approx(0.0, abs=1e-9)
    assert report.precision == pytest.approx(1.0)
    assert report.recall == pytest.approx(1.0)
    assert report.f1_score == pytest.approx(1.0)


def test_generate_evaluation_report_mismatch():
    """A missed detection (predicted 0 vs truth 1) lowers recall but not precision."""
    ground_truth_counts = [1, 1, 0]
    snapshots = [
        QueueSnapshot(
            timestamp=float(i),
            frame_index=i,
            in_queue_count=pred,
            out_of_queue_count=0,
            total_active_tracks=pred,
            active_queue_ids=(1,),
            avg_dwell_time_sec=0.0,
            estimated_wait_time_sec=0.0,
        )
        for i, pred in enumerate([1, 0, 0])  # missed the 2nd patient
    ]

    report = generate_evaluation_report(
        snapshots, ground_truth_counts, service_rate_per_min=3.0
    )

    # One true positive, one false negative, one true negative
    assert report.recall == pytest.approx(0.5)
    assert report.precision == pytest.approx(1.0)
    assert report.f1_score == pytest.approx(2 / 3, abs=1e-9)


def test_generate_evaluation_report_length_mismatch():
    snapshots = [QueueSnapshot(0.0, 0, 1, 0, 1, (1,), 0.0, 0.0) for _ in range(3)]
    with pytest.raises(ValueError):
        generate_evaluation_report(snapshots, [1, 1], 1.0)


def test_generate_evaluation_report_save(tmp_path):
    from pathlib import Path
    from src.evaluation.report import save_evaluation_report

    snapshots = [
        QueueSnapshot(0.0, 0, 2, 0, 2, (1, 2), 10.0, 40.0),
        QueueSnapshot(1.0, 1, 3, 0, 3, (1, 2, 3), 10.0, 60.0),
    ]
    report = generate_evaluation_report(snapshots, [2, 3], service_rate_per_min=3.0)
    out = tmp_path / "report.json"
    save_evaluation_report(report, out)
    assert out.exists()
    import json

    data = json.loads(out.read_text())
    assert data["precision"] == pytest.approx(1.0)
