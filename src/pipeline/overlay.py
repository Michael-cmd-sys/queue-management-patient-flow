"""
Visualization utilities for drawing pipeline overlays on video frames.

Pure image transformation functions — no I/O, no state mutation.
"""


import cv2
import numpy as np

from src.domain.config import ROIConfig
from src.domain.schema import QueueSnapshot, TrackedPerson


def draw_pipeline_overlay(
    frame: np.ndarray,
    tracks: tuple[TrackedPerson, ...],
    snapshot: QueueSnapshot,
    roi_config: ROIConfig,
    frame_width: int,
    frame_height: int,
) -> np.ndarray:
    """
    Draw visual annotations: Queue zone polygons, patient bounding boxes/IDs,
    and a top HUD dashboard displaying live queue count, per-zone counts,
    and Expected Wait Time (EWT).

    Pure image transformation function.

    Args:
        frame: OpenCV BGR image frame array.
        tracks: Tuple of TrackedPerson objects to render.
        snapshot: QueueSnapshot with current metrics for HUD display.
        roi_config: ROIConfig defining zones and zone names.
        frame_width: Frame width in pixels.
        frame_height: Frame height in pixels.

    Returns:
        Annotated frame as numpy array (same shape as input).
    """
    annotated = frame.copy()

    # Convert ROI zone points (if normalized 0..1) to pixel coordinates
    pts_list: list[list[list[int]]] = []
    colors = []
    palette = [
        (0, 255, 0),  # green
        (255, 0, 0),  # blue
        (0, 255, 255),  # yellow
        (0, 165, 255),  # orange
        (255, 0, 255),  # magenta
    ]
    for zone in roi_config.zones:
        poly_pts = []
        for pt in zone.points:
            px = int(pt.x * frame_width) if pt.x <= 1.0 else int(pt.x)
            py = int(pt.y * frame_height) if pt.y <= 1.0 else int(pt.y)
            poly_pts.append([px, py])
        pts_list.append(poly_pts)
        colors.append(palette[len(colors) % len(palette)])
    # 1. Draw semi-transparent queue zone polygons (one per zone)
    for poly_pts, color in zip(pts_list, colors):
        poly_arr = np.array(poly_pts, dtype=np.int32)
        overlay = annotated.copy()
        cv2.fillPoly(overlay, [poly_arr], color=color)
        cv2.addWeighted(overlay, 0.15, annotated, 0.85, 0, annotated)
        cv2.polylines(annotated, [poly_arr], isClosed=True, color=color, thickness=2)

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

    # 3. Draw HUD Dashboard panel at top (dynamically sized per zone count)
    id_to_meta = {
        z.id: (z.label, colors[i]) for i, z in enumerate(roi_config.zones)
    }

    ewt_min = snapshot.estimated_wait_time_sec / 60.0
    hud_lines = [
        ("PATIENT QUEUE FLOW ANALYTICS", (255, 255, 255), 0.55),
        (f"In-Queue Patients: {snapshot.in_queue_count}", (0, 255, 0), 0.5),
        (
            f"Out-of-Queue / Transit: {snapshot.out_of_queue_count}",
            (255, 200, 0),
            0.5,
        ),
    ]
    for zid, count in snapshot.zone_counts.items():
        label, color = id_to_meta.get(zid, (zid, (0, 255, 255)))
        hud_lines.append((f"{label}: {count}", color, 0.5))
    hud_lines.append(
        (f"Estimated Wait Time (EWT): {ewt_min:.1f} min", (0, 255, 255), 0.5)
    )

    panel_height = 12 + len(hud_lines) * 20
    cv2.rectangle(annotated, (10, 10), (450, 10 + panel_height), (0, 0, 0), -1)
    cv2.rectangle(annotated, (10, 10), (450, 10 + panel_height), (0, 255, 0), 2)

    y = 32
    for text, color, scale in hud_lines:
        cv2.putText(
            annotated,
            text,
            (20, y),
            cv2.FONT_HERSHEY_SIMPLEX,
            scale,
            color,
            2,
        )
        y += 20

    return annotated
