"""
Typed, immutable configuration schemas for Queue Management pipeline.
All hyperparameters and file paths are centralized and deterministic.
"""

from dataclasses import dataclass, field
from pathlib import Path

from src.domain.schema import Point, Zone


@dataclass(frozen=True)
class VisionConfig:
    """YOLOv8 Detection model hyperparameters."""

    model_path: Path = Path("models/best.pt")
    confidence_threshold: float = 0.25
    iou_threshold: float = 0.45
    target_classes: tuple[int, ...] = (0,)  # 0: person class
    device: str = "cpu"  # 'cpu', 'cuda', or 'mps'


@dataclass(frozen=True)
class TrackerConfig:
    """ByteTrack temporal tracker hyperparameters."""

    track_thresh: float = 0.25
    track_buffer: int = 30
    match_thresh: float = 0.8
    frame_rate: int = 30


_DEFAULT_ZONES = (
    Zone(
        id="main",
        label="Main Patient Queue Zone",
        points=(
            Point(0.1, 0.2),
            Point(0.9, 0.2),
            Point(0.9, 0.9),
            Point(0.1, 0.9),
        ),
    ),
)


@dataclass(frozen=True)
class ROIConfig:
    """Region of Interest (named zones) definition for queue boundary."""

    zones: tuple[Zone, ...] = _DEFAULT_ZONES

    def __init__(
        self,
        zones: tuple[Zone, ...] | None = None,
        *,
        zone_name: str | None = None,
        polygon_points: tuple[Point, ...] | None = None,
    ):
        """
        Build ROIConfig.

        Accepts the modern ``zones`` tuple, or the legacy ``zone_name`` /
        ``polygon_points`` keywords which are translated into a single
        ``Zone`` with id ``"main"``.  Rejects duplicate zone IDs so that
        downstream code can safely key ``zone_counts`` by zone id.
        """
        if zones is None:
            if polygon_points is not None:
                zones = (
                    Zone(
                        id="main",
                        label=zone_name or "Main Patient Queue Zone",
                        points=tuple(polygon_points),
                    ),
                )
            else:
                zones = _DEFAULT_ZONES

        ids = [z.id for z in zones]
        if len(ids) != len(set(ids)):
            dupes = sorted({i for i in ids if ids.count(i) > 1})
            raise ValueError(f"Duplicate zone IDs in ROIConfig: {dupes}")

        object.__setattr__(self, "zones", zones)

    @property
    def zone_name(self) -> str:
        """Backward-compatible access to the first zone's label."""
        return self.zones[0].label if self.zones else "Main Patient Queue Zone"

    @property
    def polygon_points(self) -> tuple[Point, ...]:
        """Backward-compatible access to the first zone's points."""
        return self.zones[0].points if self.zones else ()


@dataclass(frozen=True)
class AnalyticsConfig:
    """Queue math and Expected Wait Time (EWT) parameters."""

    sampling_fps: float = 5.0  # Downsample video to 5 FPS for fast compute
    service_rate_per_min: float = 2.0  # Estimated patients served per minute (mu)
    mape_interval_sec: float = 300.0  # 5-minute evaluation window for MAPE


@dataclass(frozen=True)
class PipelineConfig:
    """Complete application pipeline configuration."""

    vision: VisionConfig = field(default_factory=VisionConfig)
    tracker: TrackerConfig = field(default_factory=TrackerConfig)
    roi: ROIConfig = field(default_factory=ROIConfig)
    analytics: AnalyticsConfig = field(default_factory=AnalyticsConfig)
    video_source: Path = Path("data/input_videos/short video sample/sample.mp4")
    output_dir: Path = Path("data/output")
