"""
Multi-object tracking wrapper using ByteTrackTracker via the trackers library.
Transforms detections into persistent TrackedPerson instances over time.
"""

from typing import Tuple, Dict
import numpy as np
import supervision as sv
from trackers import ByteTrackTracker

from src.schema import Point, BoundingBox, Detection, TrackedPerson
from src.config import TrackerConfig
from src.analytics.spatial import is_person_in_queue


def create_tracker(config: TrackerConfig) -> ByteTrackTracker:
    """Initialize ByteTrackTracker instance using the modern trackers library."""
    return ByteTrackTracker(
        track_activation_threshold=config.track_thresh,
        lost_track_buffer=config.track_buffer,
        minimum_iou_threshold=config.match_thresh,
        frame_rate=config.frame_rate,
    )


def update_tracks(
    tracker: ByteTrackTracker,
    detections: Tuple[Detection, ...],
    timestamp: float,
    queue_polygon: Tuple[Point, ...],
    track_history: Dict[int, float],  # Maps track_id -> first_seen_timestamp
) -> Tuple[Tuple[TrackedPerson, ...], Dict[int, float]]:
    """
    Update tracker with current frame detections.

    Args:
        tracker: ByteTrackTracker instance.
        detections: Tuple of Detection objects from current frame.
        timestamp: Current frame timestamp in seconds.
        queue_polygon: Polygon defining the queue boundary in pixel coordinates.
        track_history: Mapping of track_id to initial timestamp.

    Returns:
        Tuple of updated TrackedPerson objects, and updated track_history dictionary.
    """
    if not detections:
        sv_dets = sv.Detections.empty()
    else:
        xyxy_list = [[d.box.x1, d.box.y1, d.box.x2, d.box.y2] for d in detections]
        conf_list = [d.confidence for d in detections]
        cls_list = [d.class_id for d in detections]

        sv_dets = sv.Detections(
            xyxy=np.array(xyxy_list, dtype=np.float32),
            confidence=np.array(conf_list, dtype=np.float32),
            class_id=np.array(cls_list, dtype=int),
        )

    # Modern trackers update API
    tracked_dets = tracker.update(sv_dets)

    tracked_persons = []
    updated_history = dict(track_history)

    if tracked_dets.tracker_id is not None and len(tracked_dets) > 0:
        for i in range(len(tracked_dets)):
            track_id = int(tracked_dets.tracker_id[i])
            xyxy = tracked_dets.xyxy[i]
            conf = float(tracked_dets.confidence[i]) if tracked_dets.confidence is not None else 1.0

            bbox = BoundingBox(
                x1=float(xyxy[0]),
                y1=float(xyxy[1]),
                x2=float(xyxy[2]),
                y2=float(xyxy[3]),
            )

            # Record first seen timestamp if new track
            if track_id not in updated_history:
                updated_history[track_id] = timestamp

            first_seen = updated_history[track_id]
            bottom_pt = bbox.bottom_center
            in_queue = is_person_in_queue(bottom_pt, queue_polygon)

            tracked_persons.append(
                TrackedPerson(
                    track_id=track_id,
                    box=bbox,
                    centroid=bbox.center,
                    bottom_point=bottom_pt,
                    confidence=conf,
                    first_seen_timestamp=first_seen,
                    last_seen_timestamp=timestamp,
                    is_in_queue=in_queue,
                )
            )

    return tuple(tracked_persons), updated_history
