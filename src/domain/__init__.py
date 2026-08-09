"""Domain layer: core schemas, configuration, and exceptions.

All immutable data structures and configuration types live here.
No dependency on vision, analytics, or transport layers.
"""

from src.domain.schema import (
    Point,
    BoundingBox,
    Detection,
    TrackedPerson,
    QueueSnapshot,
    EvaluationReport,
    Zone,
)
from src.domain.config import (
    VisionConfig,
    TrackerConfig,
    ROIConfig,
    AnalyticsConfig,
    PipelineConfig,
)

__all__ = [
    # Schema
    "Point",
    "BoundingBox",
    "Detection",
    "TrackedPerson",
    "QueueSnapshot",
    "EvaluationReport",
    "Zone",
    # Config
    "VisionConfig",
    "TrackerConfig",
    "ROIConfig",
    "AnalyticsConfig",
    "PipelineConfig",
]
