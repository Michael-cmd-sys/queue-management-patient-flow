"""
Tests for the FastAPI WebSocket-RPC / video-streaming gateway.

These are transport-layer + routing tests only. They never touch the YOLO model
or the video file (the vision runtime is lazily initialized), so they are fast
and deterministic.
"""

import pytest
from starlette.testclient import TestClient

# Import via backward-compatible re-export — tests verify the public API path
from src.rpc.server import app, state, route_rpc_request
from src.rpc.protocol import RPCRequest, RPCResponse
from src.domain.schema import Point, QueueSnapshot


@pytest.fixture(autouse=True)
def reset_state():
    """Snapshot and restore the mutable global `state` around every test."""
    saved_roi = state.active_roi_points
    saved_snapshot = state.latest_snapshot
    saved_history = dict(state.track_history)
    saved_sockets = set(state.active_websockets)
    yield
    state.active_roi_points = saved_roi
    state.latest_snapshot = saved_snapshot
    state.track_history = saved_history
    state.active_websockets = saved_sockets


_CLIENT = TestClient(app)


def test_health_check():
    resp = _CLIENT.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "healthy"
    assert "patient-queue" in body["service"]


def test_get_roi_default():
    resp = _CLIENT.get("/api/roi")
    assert resp.status_code == 200
    bodies = resp.json()
    assert bodies["zone_name"] == state.config.roi.zone_name
    assert len(bodies["polygon_points"]) == len(state.active_roi_points)


def test_set_roi_rest_updates_state():
    payload = {
        "polygon_points": [
            {"x": 0.05, "y": 0.10},
            {"x": 0.95, "y": 0.10},
            {"x": 0.50, "y": 0.95},
        ],
    }
    resp = _CLIENT.post("/api/roi", json=payload)
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"
    assert len(state.active_roi_points) == 3
    updated = _CLIENT.get("/api/roi").json()
    assert updated["polygon_points"][0] == {"x": 0.05, "y": 0.10}


def test_set_roi_rest_rejects_too_few_points():
    payload = {
        "polygon_points": [{"x": 0.1, "y": 0.1}, {"x": 0.9, "y": 0.9}],
    }
    resp = _CLIENT.post("/api/roi", json=payload)
    assert resp.status_code == 422  # Pydantic min_length=3 validation


# ── RPC dispatch (route_rpc_request) ───────────────────────────────────────────


def _zone_params():
    return {
        "polygon_points": [
            {"x": 0.1, "y": 0.1},
            {"x": 0.9, "y": 0.1},
            {"x": 0.5, "y": 0.9},
        ],
    }


def test_route_set_queue_zone():
    before = state.active_roi_points
    req = RPCRequest(
        jsonrpc="2.0", id=1, method="set_queue_zone", params=_zone_params()
    )
    resp = route_rpc_request(req)
    assert resp.error is None
    assert resp.result["status"] == "success"
    assert resp.result["vertex_count"] == 3
    # State mutation persists on the shared boundary.
    assert len(state.active_roi_points) == 3
    assert state.active_roi_points != before


def test_route_get_current_metrics_when_none():
    req = RPCRequest(jsonrpc="2.0", id=2, method="get_current_metrics")
    resp = route_rpc_request(req)
    assert resp.result == {"status": "initializing"}


def test_route_get_current_metrics_when_set():
    state.latest_snapshot = QueueSnapshot(
        timestamp=1.0,
        frame_index=30,
        in_queue_count=5,
        out_of_queue_count=1,
        total_active_tracks=6,
        active_queue_ids=(1, 2, 3, 4, 5),
        avg_dwell_time_sec=12.0,
        estimated_wait_time_sec=150.0,
    )
    req = RPCRequest(jsonrpc="2.0", id=3, method="get_current_metrics")
    resp = route_rpc_request(req)
    assert resp.result["in_queue_count"] == 5
    assert resp.result["estimated_wait_time_min"] == pytest.approx(2.5)


def test_route_method_not_found():
    req = RPCRequest(jsonrpc="2.0", id=4, method="no_such_method")
    resp = route_rpc_request(req)
    assert resp.error is not None
    assert resp.error.code == -32601
    assert "no_such_method" in resp.error.message


def test_route_invalid_params_returns_error():
    # Only two polygon points — violates min_length and must be reported, not raised.
    req = RPCRequest(
        jsonrpc="2.0",
        id=5,
        method="set_queue_zone",
        params={"polygon_points": [{"x": 0.1, "y": 0.1}, {"x": 0.9, "y": 0.9}]},
    )
    resp = route_rpc_request(req)
    assert resp.error is not None
    assert resp.error.code == -32600
    assert resp.result is None
