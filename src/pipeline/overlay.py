"""
Visualization utilities for drawing pipeline overlays on video frames.

Pure image transformation functions — no I/O, no state mutation.
"""

import numpy as np
import cv2
from typing import Tuple

from src.domain.schema import Point, TrackedPerson, QueueSnapshot
from src.domain.config import ROIConfig


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

    Args:
        frame: OpenCV BGR image frame array.
        tracks: Tuple of TrackedPerson objects to render.
        snapshot: QueueSnapshot with current metrics for HUD display.
        roi_config: ROIConfig defining polygon and zone name.
        frame_width: Frame width in pixels.
        frame_height: Frame height in pixels.

    Returns:
        Annotated frame as numpy array (same shape as input).
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
        color = (
            (0, 255, 0) if t.is_in_queue else (255, 100, 0)
        )  # Green if in queue, Blue/Orange if out

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
    cv2.putText(
        annotated,
        "PATIENT QUEUE FLOW ANALYTICS",
        (20, 32),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (255, 255, 255),
        2,
    )
    cv2.putText(
        annotated,
        f"In-Queue Patients: {snapshot.in_queue_count}",
        (20, 58),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.5,
        (0, 255, 0),
        2,
    )
    cv2.putText(
        annotated,
        f"Out-of-Queue / Transit: {snapshot.out_of_queue_count}",
        (20, 80),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.5,
        (255, 200, 0),
        1,
    )
    cv2.putText(
        annotated,
        f"Estimated Wait Time (EWT): {ewt_min:.1f} min",
        (20, 100),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.5,
        (0, 255, 255),
        2,
    )

    return annotated
