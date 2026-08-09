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
                                 |    OctaneJS + Vite Web Dashboard      |
                                 |  - HTML5 Canvas Interactive ROI Editor |
                                 |  - No-VDOM Atomic 60 FPS UI          |
                                 |  - Live Patient Count & EWT Gauges    |
                                 +---------------------------------------+
```

---

### 2. Functional Layer Decomposition

#### Layer 1: Perceptual & Vision Pipeline (`src/vision/`)
* **`detector.py`**: Pure functional wrapper over YOLOv8 returning immutable `Tuple[Detection, ...]`.
* **`tracker.py`**: `ByteTrackTracker` wrapper maintaining spatial trajectories across frames without global state mutation.

#### Layer 2: Spatial Geometry & Analytics Engine (`src/analytics/`)
* **`spatial.py`**: Pure implementation of the Ray-Casting algorithm ($O(V)$ vertex check) to evaluate if a person's ground contact point $P_i = ((x_1+x_2)/2, y_2)$ lies inside polygon boundary $\Omega_{\text{ROI}}$.
* **`queue_math.py`**: Pure implementation of queue dynamics:
  - Instantaneous queue count $N(t) = \sum \mathbb{I}_{\text{Queue}}(P_i(t))$
  - Expected Wait Time $\text{EWT}(t) = \frac{N(t)}{\mu}$
  - Statistical error metrics: MAE, RMSE, MAPE.

#### Layer 3: WebSocket-RPC Gateway (`src/transport/`)
* **`protocol.py`**: Strongly-typed JSON-RPC 2.0 protocol specifications (`RPCRequest`, `RPCResponse`, `RPCEvent`).
* **`server.py`**: FastAPI WebSocket endpoint exposing procedures:
  - `rpc.set_queue_zone(points)`: Dynamically updates active ROI polygon.
  - `rpc.get_current_metrics()`: Fetches immediate queue snapshot.
  - `rpc.stream_metrics()`: Continuous push broadcast of `QueueSnapshot` events.

#### Layer 4: Interactive OctaneJS Frontend (`dashboard/`)
* **`src/components/RoiCanvas`**: Interactive HTML5 Canvas allowing point-and-click polygon creation, point dragging, real-time scaling, and RPC submission.
* **`src/components/QueueTelemetry`**: Fine-grained reactive gauges displaying patient count, dwell time, and EWT.
