"""
Queue Management via Surveillance Camera for Patient Flow package.
Root re-exports for convenient top-level imports.
"""

__version__ = "0.2.0"

# Domain layer
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
    "__version__",
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
