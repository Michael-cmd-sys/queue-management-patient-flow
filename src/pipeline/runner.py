"""
Pipeline runner: I/O orchestration for video processing.

Handles video capture, model loading, frame iteration, sampling,
video output writing, and metrics export. Delegates per-frame processing
to pipeline.core.process_frame (pure logic) and visualization to
pipeline.overlay.draw_pipeline_overlay.
"""

import json
from pathlib import Path
from typing import List, Dict, Tuple, Sequence
import cv2

from src.domain.schema import Point, QueueSnapshot, TrackedPerson, Zone
from src.domain.config import PipelineConfig, ROIConfig
from src.vision.detector import load_yolo_model, detect_frame_objects
from src.vision.tracker import create_tracker, update_tracks
from src.evaluation.metrics import compute_queue_snapshot
from src.pipeline.core import process_frame
from src.pipeline.overlay import draw_pipeline_overlay
from src.pipeline.export import export_metrics_json


def run_pipeline(config: PipelineConfig) -> List[QueueSnapshot]:
    """
    Run complete video processing, tracking, and analytics pipeline.

    Orchestrates: model loading, video capture, frame sampling,
    per-frame detection/tracking/analytics, annotated video output,
    and metrics JSON export.

    Args:
        config: PipelineConfig configuration instance.

    Returns:
        List of QueueSnapshot records collected across the video.
    """
    if not config.video_source.exists():
        raise FileNotFoundError(
            f"Input video file not found at {config.video_source.resolve()}"
        )

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

    # Downsample: only run inference/tracking/analytics every `frame_step` frames.
    frame_step = max(1, int(round(fps / config.analytics.sampling_fps)))

    print(
        f"Opened video: {width}x{height} @ {fps:.1f} FPS ({total_frames} total frames)"
    )
    print(
        f"Frame sampling enabled: processing 1 of every {frame_step} frames "
        f"(sampling_fps={config.analytics.sampling_fps:.1f})"
    )

    # Prepare VideoWriter
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out_writer = cv2.VideoWriter(
        str(annotated_video_path), fourcc, fps, (width, height)
    )

    snapshots: List[QueueSnapshot] = []
    track_history: Dict[int, float] = {}

    frame_idx = 0
    # Convert ROI zone points (if normalized 0..1) to pixel coordinates
    pixel_zones = _zones_to_pixel(config.roi.zones, width, height)
    config_roi = ROIConfig(zones=pixel_zones)
    last_annotated_frame = None

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        timestamp = frame_idx / fps

        # Skip compute on non-sampled frames; keep video timeline intact by
        # repeating the most recent annotated frame.
        if frame_step > 1 and frame_idx % frame_step != 0:
            if last_annotated_frame is not None:
                out_writer.write(last_annotated_frame)
            else:
                out_writer.write(frame)
            frame_idx += 1
            continue

        # Process frame: detect → track → compute snapshot
        tracks, snapshot, track_history = _process_frame_with_tracker(
            frame=frame,
            model=model,
            tracker=tracker,
            config=config,
            pixel_zones=pixel_zones,
            frame_idx=frame_idx,
            fps=fps,
            track_history=track_history,
        )

        snapshots.append(snapshot)

        # Draw overlay annotations
        annotated_frame = draw_pipeline_overlay(
            frame=frame,
            tracks=tracks,
            snapshot=snapshot,
            roi_config=config_roi,
            frame_width=width,
            frame_height=height,
        )

        out_writer.write(annotated_frame)
        last_annotated_frame = annotated_frame
        frame_idx += 1

        if frame_idx % 30 == 0 or frame_idx == total_frames:
            print(
                f"Processed frame {frame_idx}/{total_frames} | "
                f"In-Queue Count: {snapshot.in_queue_count} | "
                f"EWT: {snapshot.estimated_wait_time_sec / 60:.1f} min"
            )

    cap.release()
    out_writer.release()

    # Export metrics JSON
    export_metrics_json(snapshots, json_metrics_path)

    print(f"Pipeline complete! Output video: {annotated_video_path.resolve()}")

    return snapshots


def _zones_to_pixel(zones: Sequence[Zone], width: int, height: int) -> Tuple[Zone, ...]:
    """Convert normalized zone points (0..1) to pixel coordinates."""
    pixel_zones = []
    for zone in zones:
        pts = tuple(
            Point(
                x=p.x * width if p.x <= 1.0 else p.x,
                y=p.y * height if p.y <= 1.0 else p.y,
            )
            for p in zone.points
        )
        pixel_zones.append(Zone(id=zone.id, label=zone.label, points=pts))
    return tuple(pixel_zones)


def _process_frame_with_tracker(
    frame,
    model,
    tracker,
    config: PipelineConfig,
    pixel_zones: Tuple[Zone, ...],
    frame_idx: int,
    fps: float,
    track_history: Dict[int, float],
) -> Tuple[Tuple[TrackedPerson, ...], QueueSnapshot, Dict[int, float]]:
    """Internal: process a frame using already-loaded model and tracker."""
    timestamp = frame_idx / fps

    # 1. Object Detection
    detections = detect_frame_objects(model, frame, config.vision)

    # 2. Multi-Object Tracking
    tracks, updated_history = update_tracks(
        tracker=tracker,
        detections=detections,
        timestamp=timestamp,
        zones=pixel_zones,
        track_history=track_history,
    )

    # 3. Compute Queue Metrics Snapshot
    snapshot = compute_queue_snapshot(
        frame_index=frame_idx,
        timestamp=timestamp,
        tracks=tracks,
        zones=pixel_zones,
        service_rate_per_min=config.analytics.service_rate_per_min,
    )

    return tracks, snapshot, updated_history
