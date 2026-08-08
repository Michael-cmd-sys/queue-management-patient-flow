---
name: cv-functional-mlops
description: Best practices for Production-Grade Computer Vision, MLOps, and Functional Programming in Python
---

# Production Computer Vision & MLOps with Functional Programming

## Core Philosophies

### 1. Functional Programming & Readability First
- **Pure Functions over Stateful Classes**: Core transformations (bounding box math, point-in-polygon filtering, metric computations) MUST be pure functions with zero side effects.
- **Immutability**: Use `@dataclass(frozen=True)` or `NamedTuple` for frame states, detections, and queue metrics. Never mutate objects in place.
- **Explicit Typing**: Enforce total type hints using `typing` and `numpy.typing` / `NDArray`.
- **Pipeline Composition**: Structure computer vision pipelines as a series of composable transformation functions:
  ```python
  # Pure pipeline flow
  Detections -> TrackedDetections -> SpatialFilteredDetections -> QueueMetrics
  ```
- **Side-Effect Isolation**: I/O operations (video file reading, RTSP network streaming, disk logging, UI push) must be isolated at system boundaries (`adapters`), keeping core analytics pure and testable without video hardware.

### 2. Production MLOps Best Practices
- **Config-Driven Architecture**: Hyperparameters (YOLO confidence, NMS IoU, ByteTrack parameters, ROI polygons, sampling FPS) must reside in typed config schemas (`pydantic` or `dataclass`).
- **Reproducibility & Determinism**: Seed all stochastic components and version model weights alongside inference parameters.
- **Decoupled Layers**:
  - `acquisition`: Video stream / camera adapters.
  - `vision`: Model loading, inference, and tracking wrappers.
  - `analytics`: Pure spatial and mathematical queue dynamics routines.
  - `presentation`: Data exporters, logging, and API streams.
- **Empirical Evaluation**: Every pipeline modification must be verifiable against ground truth metrics (Precision, Recall, F1, MAPE, MAE, RMSE).
