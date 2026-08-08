"""
End-to-end Queue Management & Analytics Pipeline Runner.
Processes input video streams, performs detection + tracking + spatial ROI analysis,
draws live overlays, and exports structured queue metrics.
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Tuple
import cv2
import numpy as np

from src.config import PipelineConfig, ROIConfig
from src.schema import Point, QueueSnapshot, TrackedPerson
from src.vision.detector import load_yolo_model, detect_frame_objects
from src.vision.tracker import create_tracker, update_tracks
from src.analytics.queue_math import compute_queue_snapshot


def draw_pipeline_overlay(
    frame: np.ndarray,
    tracks: Tuple[TrackedPerson, ...],
    snapshot: QueueSnapshot,
    roi_config: ROIConfig,
    frame_width: int,
    frame_height: int,
) -> np.ndarray:
    """
    Draw visual annotations: Queue polygon zone, patient bounding boxes/IDs,
    and a top HUD dashboard displaying live queue count and Expected Wait Time (EWT).
    Pure image transformation function.
    """
    annotated = frame.copy()

    # Convert ROI polygon points (if normalized 0..1) to pixel coordinates
    poly_pts = []
    for pt in roi_config.polygon_points:
        px = int(pt.x * frame_width) if pt.x <= 1.0 else int(pt.x)
        py = int(pt.y * frame_height) if pt.y <= 1.0 else int(pt.y)
        poly_pts.append([px, py])

    poly_arr = np.array(poly_pts, dtype=np.int32)

    # 1. Draw semi-transparent queue polygon zone
    overlay = annotated.copy()
    cv2.fillPoly(overlay, [poly_arr], color=(0, 255, 0))  # Green fill
    cv2.addWeighted(overlay, 0.15, annotated, 0.85, 0, annotated)
    cv2.polylines(annotated, [poly_arr], isClosed=True, color=(0, 255, 0), thickness=2)

    # 2. Draw tracks
    for t in tracks:
        x1, y1, x2, y2 = int(t.box.x1), int(t.box.y1), int(t.box.x2), int(t.box.y2)
        color = (0, 255, 0) if t.is_in_queue else (255, 100, 0)  # Green if in queue, Blue/Orange if out
        
        cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
        
        # Label: ID and Dwell duration
        label = f"ID #{t.track_id} {'[QUEUE]' if t.is_in_queue else ''}"
        cv2.putText(
            annotated,
            label,
            (x1, max(15, y1 - 8)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            color,
            2,
        )

        # Draw ground contact point (feet)
        bx, by = int(t.bottom_point.x), int(t.bottom_point.y)
        cv2.circle(annotated, (bx, by), 4, (0, 0, 255), -1)

    # 3. Draw HUD Dashboard panel at top
    cv2.rectangle(annotated, (10, 10), (450, 110), (0, 0, 0), -1)
    cv2.rectangle(annotated, (10, 10), (450, 110), (0, 255, 0), 2)

    ewt_min = snapshot.estimated_wait_time_sec / 60.0
    cv2.putText(annotated, "PATIENT QUEUE FLOW ANALYTICS", (20, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)
    cv2.putText(annotated, f"In-Queue Patients: {snapshot.in_queue_count}", (20, 58), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
    cv2.putText(annotated, f"Out-of-Queue / Transit: {snapshot.out_of_queue_count}", (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 200, 0), 1)
    cv2.putText(annotated, f"Estimated Wait Time (EWT): {ewt_min:.1f} min", (20, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)

    return annotated


def run_pipeline(config: PipelineConfig) -> List[QueueSnapshot]:
    """
    Run complete video processing, tracking, and analytics pipeline.

    Args:
        config: PipelineConfig configuration instance.

    Returns:
        List of QueueSnapshot records collected across the video.
    """
    if not config.video_source.exists():
        raise FileNotFoundError(f"Input video file not found at {config.video_source.resolve()}")

    config.output_dir.mkdir(parents=True, exist_ok=True)
    annotated_video_path = config.output_dir / "annotated_sample.mp4"
    json_metrics_path = config.output_dir / "queue_metrics.json"

    print(f"Loading YOLOv8 model from {config.vision.model_path}...")
    model = load_yolo_model(config.vision)
    tracker = create_tracker(config.tracker)

    cap = cv2.VideoCapture(str(config.video_source))
    if not cap.isOpened():
        raise RuntimeError(f"Failed to open video file {config.video_source}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    print(f"Opened video: {width}x{height} @ {fps:.1f} FPS ({total_frames} total frames)")

    # Prepare VideoWriter
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out_writer = cv2.VideoWriter(str(annotated_video_path), fourcc, fps, (width, height))

    snapshots: List[QueueSnapshot] = []
    track_history: Dict[int, float] = {}

    frame_idx = 0
    polygon_points = config.roi.polygon_points

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        timestamp = frame_idx / fps

        # Convert ROI polygon points (if normalized 0..1) to pixel coordinates
        poly_pixel_pts = tuple(
            Point(
                x=pt.x * width if pt.x <= 1.0 else pt.x,
                y=pt.y * height if pt.y <= 1.0 else pt.y,
            )
            for pt in polygon_points
        )

        # 1. Object Detection
        detections = detect_frame_objects(model, frame, config.vision)

        # 2. Multi-Object Tracking
        tracks, track_history = update_tracks(
            tracker=tracker,
            detections=detections,
            timestamp=timestamp,
            queue_polygon=poly_pixel_pts,
            track_history=track_history,
        )

        # 3. Compute Queue Metrics Snapshot
        snapshot = compute_queue_snapshot(
            frame_index=frame_idx,
            timestamp=timestamp,
            tracks=tracks,
            service_rate_per_min=config.analytics.service_rate_per_min,
        )
        snapshots.append(snapshot)

        # 4. Draw Overlay Annotations
        annotated_frame = draw_pipeline_overlay(
            frame=frame,
            tracks=tracks,
            snapshot=snapshot,
            roi_config=config.roi,
            frame_width=width,
            frame_height=height,
        )

        out_writer.write(annotated_frame)
        frame_idx += 1

        if frame_idx % 30 == 0 or frame_idx == total_frames:
            print(f"Processed frame {frame_idx}/{total_frames} | In-Queue Count: {snapshot.in_queue_count} | EWT: {snapshot.estimated_wait_time_sec/60:.1f} min")

    cap.release()
    out_writer.release()

    # 5. Export metrics JSON
    metrics_data = [
        {
            "frame_index": s.frame_index,
            "timestamp_sec": round(s.timestamp, 2),
            "in_queue_count": s.in_queue_count,
            "out_of_queue_count": s.out_of_queue_count,
            "total_active_tracks": s.total_active_tracks,
            "active_queue_ids": list(s.active_queue_ids),
            "avg_dwell_time_sec": round(s.avg_dwell_time_sec, 2),
            "estimated_wait_time_sec": round(s.estimated_wait_time_sec, 2),
        }
        for s in snapshots
    ]

    with open(json_metrics_path, "w") as f:
        json.dump(metrics_data, f, indent=2)

    print(f"Pipeline complete! Output video: {annotated_video_path.resolve()}")
    print(f"Metrics exported to: {json_metrics_path.resolve()}")

    return snapshots
