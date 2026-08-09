"""
Typed, immutable configuration schemas for Queue Management pipeline.
All hyperparameters and file paths are centralized and deterministic.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Tuple
from src.domain.schema import Point, Zone


@dataclass(frozen=True)
class VisionConfig:
    """YOLOv8 Detection model hyperparameters."""

    model_path: Path = Path("models/best.pt")
    confidence_threshold: float = 0.25
    iou_threshold: float = 0.45
    target_classes: Tuple[int, ...] = (0,)  # 0: person class
    device: str = "cpu"  # 'cpu', 'cuda', or 'mps'


@dataclass(frozen=True)
class TrackerConfig:
    """ByteTrack temporal tracker hyperparameters."""

    track_thresh: float = 0.25
    track_buffer: int = 30
    match_thresh: float = 0.8
    frame_rate: int = 30


@dataclass(frozen=True)
class ROIConfig:
    """Region of Interest (named zones) definition for queue boundary."""

    zones: Tuple[Zone, ...] = (
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

    @property
    def zone_name(self) -> str:
        """Backward-compatible access to the first zone's label."""
        return self.zones[0].label if self.zones else "Main Patient Queue Zone"

    @property
    def polygon_points(self) -> Tuple[Point, ...]:
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
