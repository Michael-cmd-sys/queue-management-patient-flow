# Systems Solution Architecture Specification
## Patient Queue Flow Surveillance & Real-Time Analytics System

### 1. Architectural System Overview

The system is designed as a **decoupled, real-time, event-driven computer vision microservice** coupled with a high-performance **No-VDOM reactive web dashboard**. 

```
                                 +---------------------------------------+
                                 |   Surveillance CCTV Camera / Video    |
                                 +---------------------------------------+
                                                     |
                                                     v
                                 +---------------------------------------+
                                 |  Python Computer Vision ML Engine     |
                                 |  - YOLOv8 Person Detection            |
                                 |  - ByteTrack Trajectory Tracking      |
                                 |  - Ray-Casting Point-in-Polygon ROI   |
                                 |  - Queue Dynamics & EWT Math Model    |
                                 +---------------------------------------+
                                            |               ^
                   Real-time Metrics        |               |  RPC Commands
                   (WebSocket Broadcast)    v               |  (SetQueueZone, etc.)
                                 +---------------------------------------+
                                 |    FastAPI WebSocket-RPC Gateway      |
                                 +---------------------------------------+
                                                     |
                                                     v
                                 +---------------------------------------+
                                 |    OctaneJS + Vite Web Dashboard *(planned)* |
                                 |  - HTML5 Canvas Interactive ROI Editor |
                                 |  - No-VDOM Atomic 60 FPS UI          |
                                 |  - Live Patient Count & EWT Gauges    |
                                 +---------------------------------------+
```

---

### 2. Functional Layer Decomposition

#### Supporting Layers: Domain & Evaluation (`src/domain/`, `src/evaluation/`)
* **`src/domain/schema.py`**: Immutable domain contracts (`Point`, `BoundingBox`, `Detection`, `TrackedPerson`, `QueueSnapshot`, `EvaluationReport`).
* **`src/domain/config.py`**: Immutable typed configuration (`VisionConfig`, `TrackerConfig`, `ROIConfig`, `AnalyticsConfig`, `PipelineConfig`).
* **`src/evaluation/metrics.py`**: Pure queue-math functions:
  - Instantaneous queue count $N(t) = \sum \mathbb{I}_{\text{Queue}}(P_i(t))$
  - Expected Wait Time $\text{EWT}(t) = \frac{N(t)}{\mu}$
  - Statistical error metrics: MAE, RMSE, MAPE.
* **`src/evaluation/report.py`**: Aggregation of snapshots + ground truth into a full `EvaluationReport`.
* **`src/evaluation/plotting.py`**: Time-series chart generation for thesis documentation.
* (`src/analytics/queue_math.py` re-exports the math functions for backward compatibility.)

#### Layer 1: Perceptual & Vision Pipeline (`src/vision/`)
* **`detector.py`**: Pure functional wrapper over YOLOv8 returning immutable `Tuple[Detection, ...]`.
* **`tracker.py`**: `ByteTrackTracker` wrapper maintaining spatial trajectories across frames without global state mutation.

#### Layer 2: Spatial Geometry & Analytics Engine (`src/analytics/`)
* **`spatial.py`**: Pure implementation of the Ray-Casting algorithm ($O(V)$ vertex check) to evaluate if a person's ground contact point $P_i = ((x_1+x_2)/2, y_2)$ lies inside polygon boundary $\Omega_{\text{ROI}}$.

#### Layer 3: WebSocket-RPC Gateway (`src/transport/`)
* **`protocol.py`**: Strongly-typed JSON-RPC 2.0 protocol specifications (`RPCRequest`, `RPCResponse`, `RPCEvent`).
* **`server.py`**: FastAPI WebSocket endpoint exposing procedures:
  - `rpc.set_queue_zones(zones)`: Replaces the active ROI with one or more named zones (primary procedure).
  - `rpc.set_queue_zone(zones)` *(deprecated)*: Single-zone backward-compatible alias.
  - `rpc.get_current_metrics()`: Returns the latest `QueueSnapshot` on demand.
  - `queue_metrics_update` WebSocket events provide continuous push broadcasts of `QueueSnapshot` updates (not a polling RPC method).

#### Layer 4: Interactive Dashboard Frontend (`dashboard/`) — *planned, not yet implemented*
* **`/api/video_feed`** (backend, implemented): annotated MJPEG multipart stream from `generate_video_mjpeg()`.
* **Frontend (planned)**: an OctaneJS + Vite dashboard with `src/components/QueueTelemetry` reactive gauges for patient count, dwell time, and EWT. Not present in the current module tree.

#### Layer 4: Interactive Dashboard Frontend (`dashboard/`)
* **`src/components/QueueTelemetry`**: Fine-grained reactive gauges displaying patient count, dwell time, and EWT.
* **Video stream**: `/api/video_feed` — annotated MJPEG multipart stream from `generate_video_mjpeg()`.

#### Layer 5: Pipeline Orchestration (`src/pipeline/`)
* **`runner.py`**: I/O orchestration (video capture, frame sampling, model loading, annotated video output, metrics export).
* **`core.py`**: Pure per-frame processing (detect → track → snapshot).
* **`overlay.py`**: Drawing/visualization utilities (queue polygon, track boxes, HUD).
* **`export.py`**: JSON/CSV serialization of pipeline artifacts.
