"""
Core pipeline logic: pure functions for frame processing and tracker state management.

These functions have no I/O side effects — they transform inputs into outputs.
The runner.py module handles video capture, file I/O, and lifecycle management.
"""

from typing import Dict, Tuple, Sequence

import cv2
import numpy as np

from src.domain.schema import Detection, Point, QueueSnapshot, TrackedPerson, Zone
from src.domain.config import PipelineConfig, ROIConfig, AnalyticsConfig
from src.vision.detector import detect_frame_objects
from src.vision.tracker import update_tracks
from src.evaluation.metrics import compute_queue_snapshot


def process_frame(
    frame: np.ndarray,
    model: object,
    config: PipelineConfig,
    zones: Sequence[Zone],
    frame_idx: int,
    fps: float,
    track_history: Dict[int, float],
) -> Tuple[Tuple[TrackedPerson, ...], QueueSnapshot, Dict[int, float]]:
    """
    Process a single video frame through detection, tracking, and analytics.

    Pure transformation: (frame, model, config, state) -> (tracks, snapshot, updated_history).
    No disk I/O, no network, no video writer.

    Args:
        frame: OpenCV BGR image frame array.
        model: Loaded YOLO model instance.
        config: PipelineConfig with vision/threshold parameters.
        zones: Sequence of Zone definitions (id, label, pixel-coordinate points)
            defining the queue boundary regions.
        frame_idx: Zero-based frame index.
        fps: Video frames-per-second.
        track_history: Mutable tracking dict (track_id -> first_seen_timestamp).

    Returns:
        Tuple of (TrackedPerson instances, QueueSnapshot, updated track_history).
    """
    timestamp = frame_idx / fps

    # 1. Object Detection
    detections: Tuple[Detection, ...] = detect_frame_objects(
        model=model,
        frame=frame,
        config=config.vision,
    )

    # 2. Multi-Object Tracking
    tracks, updated_history = update_tracks(
        tracker=config.tracker,  # Note: caller resolves the tracker instance
        detections=detections,
        timestamp=timestamp,
        zones=zones,
        track_history=track_history,
    )

    # 3. Compute Queue Metrics Snapshot
    snapshot = compute_queue_snapshot(
        frame_index=frame_idx,
        timestamp=timestamp,
        tracks=tracks,
        zones=zones,
        service_rate_per_min=config.analytics.service_rate_per_min,
    )

    return tracks, snapshot, updated_history


def advance_tracker_state(
    tracker: object,
    detections: Tuple[Detection, ...],
    timestamp: float,
    zones: Sequence[Zone],
    track_history: Dict[int, float],
) -> Tuple[Tuple[TrackedPerson, ...], Dict[int, float]]:
    """
    Convenience wrapper: advance the tracker with detections.
    Delegates to src.vision.tracker.update_tracks.

    Args:
        tracker: ByteTrackTracker instance (resolved by caller).
        detections: Tuple of Detection objects from current frame.
        timestamp: Current frame timestamp in seconds.
        zones: Sequence of Zone definitions defining queue boundary in pixel coordinates.
        track_history: Mapping of track_id to initial timestamp.

    Returns:
        Tuple of updated TrackedPerson objects and updated track_history dict.
    """
    return update_tracks(
        tracker=tracker,
        detections=detections,
        timestamp=timestamp,
        zones=zones,
        track_history=track_history,
    )
