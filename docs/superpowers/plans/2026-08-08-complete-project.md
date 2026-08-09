# Complete Project Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete the KNUST Patient Queue Flow Surveillance system by building the missing OctaneJS dashboard frontend, implementing frame sampling, automating evaluation reports, adding RPC/WebSocket tests, and cleaning up git state.

**Architecture:** Three-phase approach — (1) Backend improvements first to unlock real-time data flow, (2) Dashboard frontend components consuming the WebSocket-RPC gateway, (3) Testing and verification. Each phase produces independently runnable software.

**Tech Stack:** Python 3.13+, FastAPI, WebSocket JSON-RPC 2.0, OctaneJS (TSRX), pytest, matplotlib

---
## Phase 1: Backend Improvements & Frame Sampling

### Task 1: Implement Frame Sampling in Pipeline

**Files:**
- Modify: `src/pipeline/runner.py`
- Modify: `src/config.py:44-49`

- [ ] **Step 1: Write failing test for frame sampling**

In `tests/test_analytics.py`, add:

```python
def test_pipeline_respects_sampling_fps():
    """Pipeline should skip frames when sampling_fps < video fps."""
    from src.config import PipelineConfig, ROIConfig, VisionConfig, AnalyticsConfig
    from src.pipeline import run_pipeline
    
    config = PipelineConfig(
        vision=VisionConfig(model_path=Path("models/best.pt")),
        roi=ROIConfig(polygon_points=(Point(0.05, 0.10), Point(0.95, 0.10), Point(0.95, 0.95), Point(0.05, 0.95))),
        video_source=Path("data/input_videos/short video sample/sample.mp4"),
        output_dir=Path("data/output"),
        analytics=AnalyticsConfig(sampling_fps=1.0),
    )
    # With 30fps video and 1.0 sampling_fps, expect ~1/30th the frames
    snapshots = run_pipeline(config)
    # sample.mp4 is ~5078938 bytes, roughly 169s at 30fps = ~5070 frames
    # At 1.0 fps sampling, expect ~169 snapshots
    assert len(snapshots) < 500
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_analytics.py::test_pipeline_respects_sampling_fps -v`
Expected: FAIL with assertion error (too many snapshots, or no sampling logic)

- [ ] **Step 3: Implement frame sampling in pipeline**

Modify `src/config.py` — add `frame_step: int` to `AnalyticsConfig`:

```python
@dataclass(frozen=True)
class AnalyticsConfig:
    """Queue math and Expected Wait Time (EWT) parameters."""
    sampling_fps: float = 5.0
    service_rate_per_min: float = 2.0
    mape_interval_sec: float = 300.0
    frame_step: int = field(init=False)
    
    def __post_init__(self):
        if self.sampling_fps <= 0:
            raise ValueError("sampling_fps must be positive")
        # frame_step computed dynamically based on video fps
```

Modify `src/pipeline/runner.py` — compute `frame_step` and skip frames:

```python
fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
frame_step = max(1, int(round(fps / config.analytics.sampling_fps)))
```

In the while loop, add frame skipping:

```python
frame_idx += 1
if frame_idx % frame_step != 0:
    continue
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_analytics.py::test_pipeline_respects_sampling_fps -v`
Expected: PASS with ~169 snapshots

- [ ] **Step 5: Commit**

```bash
git add src/config.py src/pipeline/ tests/test_analytics.py
git commit -m "feat: add frame sampling to pipeline based on sampling_fps config"
```

---
## Phase 2: Dashboard Frontend

### Task 2: Create RoiCanvas Component

**Files:**
- Create: `dashboard/src/components/RoiCanvas.tsrx`
- Modify: `dashboard/src/App.tsrx:1-122`
- Modify: `dashboard/src/main.ts`

- [ ] **Step 1: Write failing test for RoiCanvas**

Create `dashboard/src/components/__tests__/RoiCanvas.test.ts`:

```typescript
import { describe, it, expect } from 'vitest';
import { render } from 'octanejs/test-utils';

describe('RoiCanvas', () => {
  it('renders canvas element', async () => {
    const { container } = await render(<RoiCanvas />);
    expect(container.querySelector('canvas')).toBeTruthy();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd dashboard && npm run test -- RoiCanvas.test.ts`
Expected: FAIL with "RoiCanvas not found"

- [ ] **Step 3: Create RoiCanvas component**

Create `dashboard/src/components/RoiCanvas.tsrx`:

```typescript
export function RoiCanvas() @{
  const canvasRef = signal<HTMLCanvasElement | null>(null);
  const points = signal<{x: number; y: number}[]>([]);
  const isDragging = signal(false);
  const dragIndex = signal(-1);

  onMount(() => {
    const canvas = canvasRef.value;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    canvas.addEventListener('click', (e) => {
      if (isDragging.value) return;
      const rect = canvas.getBoundingClientRect();
      points.value = [...points.value, {
        x: e.clientX - rect.left,
        y: e.clientY - rect.top
      }];
    });

    canvas.addEventListener('mousedown', (e) => {
      const rect = canvas.getBoundingClientRect();
      const mx = e.clientX - rect.left;
      const my = e.clientY - rect.top;
      const idx = points.value.findIndex(p => 
        Math.hypot(p.x - mx, p.y - my) < 10
      );
      if (idx >= 0) {
        isDragging.value = true;
        dragIndex.value = idx;
      }
    });

    canvas.addEventListener('mousemove', (e) => {
      if (!isDragging.value || dragIndex.value < 0) return;
      const rect = canvas.getBoundingClientRect();
      const newPoints = [...points.value];
      newPoints[dragIndex.value] = {
        x: e.clientX - rect.left,
        y: e.clientY - rect.top
      };
      points.value = newPoints;
    });

    canvas.addEventListener('mouseup', () => {
      isDragging.value = false;
      dragIndex.value = -1;
    });
  });

  const submitROI = async () => {
    if (points.value.length < 3) return;
    const ws = new WebSocket('ws://localhost:8000/ws/rpc');
    ws.onopen = () => {
      ws.send(JSON.stringify({
        jsonrpc: "2.0",
        id: 1,
        method: "set_queue_zone",
        params: { polygon_points: points.value }
      }));
    };
  };

  <canvas 
    ref={canvasRef}
    width={640}
    height={480}
    style=${{ border: '1px solid #333', background: '#000' }}
  />
  <button onClick={submitROI} disabled={points.value.length < 3}>
    Set Queue Zone
  </button>
  <p>Click to add points, drag to adjust. Need at least 3 points.</p>
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd dashboard && npm run test -- RoiCanvas.test.ts`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add dashboard/src/components/RoiCanvas.tsrx dashboard/src/components/__tests__/RoiCanvas.test.ts
git commit -m "feat: add interactive RoiCanvas component for polygon editing"
```

### Task 3: Create QueueTelemetry Component

**Files:**
- Create: `dashboard/src/components/QueueTelemetry.tsrx`

- [ ] **Step 1: Write failing test**

Create `dashboard/src/components/__tests__/QueueTelemetry.test.ts`:

```typescript
import { describe, it, expect } from 'vitest';
import { render } from 'octanejs/test-utils';

describe('QueueTelemetry', () => {
  it('renders queue count and EWT', async () => {
    const { container } = await render(<QueueTelemetry />);
    expect(container.textContent).toContain('In Queue');
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd dashboard && npm run test -- QueueTelemetry.test.ts`
Expected: FAIL

- [ ] **Step 3: Create QueueTelemetry component**

Create `dashboard/src/components/QueueTelemetry.tsrx`:

```typescript
import { signal, effect } from 'octanejs';

interface Metrics {
  in_queue_count: number;
  out_of_queue_count: number;
  estimated_wait_time_min: number;
  avg_dwell_time_sec: number;
}

export function QueueTelemetry() @{
  const metrics = signal<Metrics>({
    in_queue_count: 0,
    out_of_queue_count: 0,
    estimated_wait_time_min: 0,
    avg_dwell_time_sec: 0,
  });

  onMount(() => {
    const ws = new WebSocket('ws://localhost:8000/ws/rpc');
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.event === 'queue_metrics_update') {
        metrics.value = data.data;
      }
    };
  });

  <div class="telemetry-panel">
    <div class="metric">
      <span class="label">In Queue</span>
      <span class="value">{metrics.value.in_queue_count}</span>
    </div>
    <div class="metric">
      <span class="label">Out of Queue</span>
      <span class="value">{metrics.value.out_of_queue_count}</span>
    </div>
    <div class="metric">
      <span class="label">EWT</span>
      <span class="value">{metrics.value.estimated_wait_time_min.toFixed(1)} min</span>
    </div>
    <div class="metric">
      <span class="label">Avg Dwell</span>
      <span class="value">{metrics.value.avg_dwell_time_sec.toFixed(1)}s</span>
    </div>
  </div>
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd dashboard && npm run test -- QueueTelemetry.test.ts`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add dashboard/src/components/QueueTelemetry.tsrx dashboard/src/components/__tests__/QueueTelemetry.test.ts
git commit -m "feat: add QueueTelemetry reactive gauge component"
```

### Task 4: Build Main Dashboard Layout

**Files:**
- Modify: `dashboard/src/App.tsrx:1-122`
- Modify: `dashboard/src/main.ts`

- [ ] **Step 1: Write failing integration test**

Create `dashboard/src/__tests__/App.test.ts`:

```typescript
import { describe, it, expect } from 'vitest';
import { render } from 'octanejs/test-utils';
import { App } from '../App';

describe('App', () => {
  it('renders RoiCanvas and QueueTelemetry', async () => {
    const { container } = await render(<App />);
    expect(container.querySelector('canvas')).toBeTruthy();
    expect(container.textContent).toContain('In Queue');
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd dashboard && npm run test -- App.test.ts`
Expected: FAIL (App still has default OctaneJS scaffold)

- [ ] **Step 3: Rewrite App.tsrx**

Replace `dashboard/src/App.tsrx` content with:

```typescript
import { RoiCanvas } from './components/RoiCanvas';
import { QueueTelemetry } from './components/QueueTelemetry';

export function App() @{
  <div class="dashboard">
    <header class="header">
      <h1>Patient Queue Flow Analytics</h1>
    </header>
    <main class="main">
      <section class="panel">
        <h2>Queue Zone Editor</h2>
        <RoiCanvas />
      </section>
      <section class="panel">
        <h2>Live Telemetry</h2>
        <QueueTelemetry />
        <img src="http://localhost:8000/api/video_feed" class="video-feed" />
      </section>
    </main>
  </div>
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd dashboard && npm run test -- App.test.ts`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add dashboard/src/App.tsrx dashboard/src/__tests__/App.test.ts
git commit -m "feat: integrate dashboard layout with RoiCanvas and QueueTelemetry"
```

---
## Phase 3: Evaluation Report Automation

### Task 5: Build EvaluationReport Generator

**Files:**
- Create: `src/evaluation/report.py`
- Modify: `src/schema.py:81-89`

- [ ] **Step 1: Write failing test**

In `tests/test_analytics.py`, add:

```python
def test_generate_evaluation_report():
    from src.evaluation.report import generate_evaluation_report
    from src.schema import EvaluationReport
    
    snapshots = [
        QueueSnapshot(timestamp=0.0, frame_index=0, in_queue_count=5, out_of_queue_count=2,
                      total_active_tracks=7, active_queue_ids=(1,2,3), avg_dwell_time_sec=60.0,
                      estimated_wait_time_sec=150.0),
        QueueSnapshot(timestamp=1.0, frame_index=30, in_queue_count=6, out_of_queue_count=2,
                      total_active_tracks=8, active_queue_ids=(1,2,3,4), avg_dwell_time_sec=65.0,
                      estimated_wait_time_sec=180.0),
    ]
    ground_truth = [5, 6]
    
    report = generate_evaluation_report(snapshots, ground_truth, service_rate_per_min=2.0)
    assert isinstance(report, EvaluationReport)
    assert report.mape >= 0
    assert report.mae >= 0
    assert report.rmse >= 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_analytics.py::test_generate_evaluation_report -v`
Expected: FAIL with "generate_evaluation_report not found"

- [ ] **Step 3: Implement report generator**

Create `src/evaluation/report.py`:

```python
from typing import List, Tuple
from src.schema import QueueSnapshot, EvaluationReport
from src.analytics.queue_math import calculate_mae, calculate_rmse, calculate_mape


def generate_evaluation_report(
    snapshots: List[QueueSnapshot],
    ground_truth_counts: List[int],
    service_rate_per_min: float,
) -> EvaluationReport:
    """
    Compare automated predictions against ground truth and produce full evaluation report.
    """
    predicted = [s.in_queue_count for s in snapshots]
    
    mae = calculate_mae(ground_truth_counts, predicted)
    rmse = calculate_rmse(ground_truth_counts, predicted)
    mape = calculate_mape(ground_truth_counts, predicted)
    
    precision = sum(1 for p, g in zip(predicted, ground_truth_counts) if p == g and g > 0) / max(1, sum(1 for p in predicted if p > 0))
    recall = sum(1 for p, g in zip(predicted, ground_truth_counts) if p == g and p > 0) / max(1, sum(1 for g in ground_truth_counts if g > 0))
    f1 = 2 * precision * recall / (precision + recall + 1e-9)
    
    return EvaluationReport(
        precision=precision,
        recall=recall,
        f1_score=f1,
        mape=mape,
        mae=mae,
        rmse=rmse,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_analytics.py::test_generate_evaluation_report -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/evaluation/report.py tests/test_analytics.py
git commit -m "feat: add evaluation report generator for thesis metrics"
```

---
## Phase 4: RPC/WebSocket Testing

### Task 6: Add FastAPI Integration Tests

**Files:**
- Create: `tests/test_rpc_server.py`

- [ ] **Step 1: Write failing test for RPC method dispatch**

Create `tests/test_rpc_server.py`:

```python
import json
import pytest
from fastapi.testclient import TestClient
from src.rpc.server import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_set_queue_zone_rest():
    response = client.post("/api/roi", json={
        "zone_name": "Test Zone",
        "polygon_points": [{"x": 0.1, "y": 0.1}, {"x": 0.9, "y": 0.1}, {"x": 0.9, "y": 0.9}]
    })
    assert response.status_code == 200
    assert response.json()["status"] == "success"


def test_get_roi_rest():
    response = client.get("/api/roi")
    assert response.status_code == 200
    data = response.json()
    assert "polygon_points" in data
    assert len(data["polygon_points"]) >= 3


def test_websocket_rpc_set_queue_zone():
    with client.websocket_connect("/ws/rpc") as ws:
        ws.send_text(json.dumps({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "set_queue_zone",
            "params": {
                "zone_name": "WS Test",
                "polygon_points": [{"x": 0.2, "y": 0.2}, {"x": 0.8, "y": 0.2}, {"x": 0.8, "y": 0.8}]
            }
        }))
        response = json.loads(ws.receive_text())
        assert response["id"] == 1
        assert response["result"]["status"] == "success"


def test_websocket_rpc_unknown_method():
    with client.websocket_connect("/ws/rpc") as ws:
        ws.send_text(json.dumps({
            "jsonrpc": "2.0",
            "id": 2,
            "method": "nonexistent_method",
            "params": {}
        }))
        response = json.loads(ws.receive_text())
        assert response["error"]["code"] == -32601
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_rpc_server.py -v`
Expected: FAIL (server imports will fail due to missing dependencies or state issues)

- [ ] **Step 3: Fix server imports for testability**

Modify `src/rpc/server.py` to guard model loading:

```python
# At top of file, after imports
try:
    yolo_model = load_yolo_model(state.config.vision)
    byte_tracker = create_tracker(state.config.tracker)
except Exception as e:
    print(f"Warning: Could not load vision models: {e}")
    yolo_model = None
    byte_tracker = None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_rpc_server.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_rpc_server.py src/rpc/server.py
git commit -m "test: add FastAPI RPC server integration tests"
```

---
## Phase 5: Git Cleanup & Verification

### Task 7: Clean Up Git State

**Files:**
- All tracked files

- [ ] **Step 1: Review git status**

Run: `git status`
Expected: Shows modified `pyproject.toml`, `uv.lock`, and untracked `src/rpc/`, `dashboard/`, `docs/architecture_specification.md`

- [ ] **Step 2: Stage all intended changes**

```bash
git add pyproject.toml uv.lock src/rpc/ dashboard/ docs/architecture_specification.md
```

- [ ] **Step 3: Commit with conventional message**

```bash
git commit -m "feat: add FastAPI WebSocket-RPC gateway and OctaneJS dashboard scaffold

- Implement JSON-RPC 2.0 protocol with set_queue_zone/get_current_metrics
- Add MJPEG video streaming endpoint
- Add WebSocket metrics broadcaster
- Add OctaneJS dashboard scaffold with RoiCanvas and QueueTelemetry
- Add frame sampling to pipeline based on sampling_fps config
- Add evaluation report generator for thesis metrics
- Add FastAPI integration tests for RPC server"
```

- [ ] **Step 4: Verify all tests pass**

Run: `pytest -v`
Expected: All tests PASS

- [ ] **Step 5: Run lint/typecheck if available**

Run: `cd dashboard && npm run typecheck`
Expected: No type errors (or fix any that exist)

---
## Execution Order Summary

1. **Phase 1** — Frame sampling (backend improvement, unblocks accurate metrics)
2. **Phase 2** — Dashboard frontend (RoiCanvas, QueueTelemetry, App layout)
3. **Phase 3** — Evaluation report automation (thesis metrics)
4. **Phase 4** — RPC/WebSocket tests (coverage for gateway)
5. **Phase 5** — Git cleanup and final verification

Each phase produces independently runnable, tested software. No step depends on a later phase.
