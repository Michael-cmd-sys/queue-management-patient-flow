"""
Export utilities for serializing pipeline artifacts to disk.

Pure data transformation — takes snapshots and produces serializable structures.
Filesystem writes are isolated to specific functions.
"""

import json
from pathlib import Path
from typing import List, Dict, Any

from src.domain.schema import QueueSnapshot


def snapshots_to_dicts(snapshots: List[QueueSnapshot]) -> List[Dict[str, Any]]:
    """
    Convert QueueSnapshot records to JSON-serializable dictionaries.

    Args:
        snapshots: List of QueueSnapshot objects.

    Returns:
        List of dictionaries with frame metrics.
    """
    return [
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


def export_metrics_json(
    snapshots: List[QueueSnapshot],
    output_path: Path,
) -> None:
    """
    Persist queue metrics snapshots to a JSON file.

    Args:
        snapshots: List of QueueSnapshot records collected across the video.
        output_path: Target file path for the JSON output.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    metrics_data = snapshots_to_dicts(snapshots)

    with open(output_path, "w") as f:
        json.dump(metrics_data, f, indent=2)

    print(f"Metrics exported to: {output_path.resolve()}")


__all__ = ["snapshots_to_dicts", "export_metrics_json"]
