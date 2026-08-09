"""
Core domain data structures and immutable schemas for Queue Management.
Follows Functional Programming principles: frozen (immutable) dataclasses, pure data objects.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import NamedTuple


class Point(NamedTuple):
    """2D Point coordinate (x, y)."""

    x: float
    y: float


class Zone(NamedTuple):
    """A named queue zone defined by a polygon boundary."""

    id: str
    label: str
    points: tuple[Point, ...]
    coordinate_space: str = "normalized"


class BoundingBox(NamedTuple):
    """Bounding box coordinates (x1, y1, x2, y2)."""

    x1: float
    y1: float
    x2: float
    y2: float

    @property
    def width(self) -> float:
        return self.x2 - self.x1

    @property
    def height(self) -> float:
        return self.y2 - self.y1

    @property
    def center(self) -> Point:
        return Point(x=(self.x1 + self.x2) / 2.0, y=(self.y1 + self.y2) / 2.0)

    @property
    def bottom_center(self) -> Point:
        """Ground contact point (feet level), ideal for Point-in-Polygon queue testing."""
        return Point(x=(self.x1 + self.x2) / 2.0, y=self.y2)


@dataclass(frozen=True)
class Detection:
    """Immutable single-frame object detection."""

    box: BoundingBox
    confidence: float
    class_id: int
    class_name: str = "person"


@dataclass(frozen=True)
class TrackedPerson:
    """Immutable temporal track of an individual person."""

    track_id: int
    box: BoundingBox
    centroid: Point
    bottom_point: Point
    confidence: float
    first_seen_timestamp: float
    last_seen_timestamp: float
    is_in_queue: bool
    in_zone_ids: tuple[str, ...] = ()

    @property
    def dwell_duration_sec(self) -> float:
        """Calculate total observed duration in seconds."""
        return max(0.0, self.last_seen_timestamp - self.first_seen_timestamp)


@dataclass(frozen=True)
class QueueSnapshot:
    """Immutable snapshot of queue dynamics at a specific point in time."""

    timestamp: float
    frame_index: int
    in_queue_count: int
    out_of_queue_count: int
    total_active_tracks: int
    active_queue_ids: tuple[int, ...]
    avg_dwell_time_sec: float
    estimated_wait_time_sec: float
    zone_counts: Mapping[str, int] = field(default_factory=lambda: MappingProxyType({}))


@dataclass(frozen=True)
class EvaluationReport:
    """Evaluation metrics comparing automated predictions against ground truth."""

    precision: float
    recall: float
    f1_score: float
    mape: float  # Mean Absolute Percentage Error (for queue counts)
    mae: float  # Mean Absolute Error (for wait time in seconds)
    rmse: float  # Root Mean Squared Error (for wait time in seconds)
