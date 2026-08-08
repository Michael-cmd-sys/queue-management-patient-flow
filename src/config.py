"""
Typed, immutable configuration schemas for Queue Management pipeline.
All hyperparameters and file paths are centralized and deterministic.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Tuple
from src.schema import Point


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
    """Region of Interest (Polygon) definition for queue boundary."""
    zone_name: str = "Main Patient Queue Zone"
    # Polygon vertices (x, y) normalized (0.0 - 1.0) or pixel coordinates
    polygon_points: Tuple[Point, ...] = (
        Point(0.1, 0.2),
        Point(0.9, 0.2),
        Point(0.9, 0.9),
        Point(0.1, 0.9),
    )


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
