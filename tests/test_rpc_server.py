"""
Tests for the FastAPI WebSocket-RPC / video-streaming gateway.

These are transport-layer + routing tests only. They never touch the YOLO model
or the video file (the vision runtime is lazily initialized), so they are fast
and deterministic.
"""

import pytest
from starlette.testclient import TestClient

# Import from the canonical transport layer
from src.transport.server import app, state, route_rpc_request
from src.transport.protocol import RPCRequest, RPCResponse
from src.domain.schema import Point, QueueSnapshot


@pytest.fixture(autouse=True)
def reset_state():
    """Snapshot and restore the mutable global `state` around every test."""
    saved_zones = state.active_zones
    saved_snapshot = state.latest_snapshot
    saved_history = dict(state.track_history)
    saved_sockets = set(state.active_websockets)
    yield
    state.active_zones = saved_zones
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


def test_get_zones_default():
    resp = _CLIENT.get("/api/zones")
    assert resp.status_code == 200
    bodies = resp.json()
    assert isinstance(bodies, list)
    assert len(bodies) == len(state.active_zones)
    assert bodies[0]["label"] == state.config.roi.zones[0].label


def test_get_roi_backward_compat():
    """GET /api/roi still returns the first zone's points for backward compat."""
    resp = _CLIENT.get("/api/roi")
    assert resp.status_code == 200
    body = resp.json()
    assert body["zone_name"] == state.config.roi.zone_name
    assert len(body["polygon_points"]) == len(state.active_roi_points)


def test_set_zones_rest_updates_state():
    payload = {
        "zones": [
            {
                "id": "triage",
                "label": "Triage Area",
                "polygon_points": [
                    {"x": 0.05, "y": 0.10},
                    {"x": 0.95, "y": 0.10},
                    {"x": 0.50, "y": 0.95},
                ],
            },
            {
                "id": "waiting",
                "label": "Waiting Room",
                "polygon_points": [
                    {"x": 0.10, "y": 0.10},
                    {"x": 0.30, "y": 0.10},
                    {"x": 0.20, "y": 0.50},
                ],
            },
        ]
    }
    resp = _CLIENT.post("/api/zones", json=payload)
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"
    assert resp.json()["zone_count"] == 2
    assert len(state.active_zones) == 2
    assert state.active_zones[0].id == "triage"
    assert state.active_zones[1].id == "waiting"


def test_set_roi_rest_backward_compat():
    """POST /api/roi still works for single-zone backward compatibility."""
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
    assert len(state.active_zones) == 1


def test_set_roi_rest_rejects_too_few_points():
    payload = {
        "polygon_points": [{"x": 0.1, "y": 0.1}, {"x": 0.9, "y": 0.9}],
    }
    resp = _CLIENT.post("/api/roi", json=payload)
    assert resp.status_code == 422  # Pydantic min_length=3 validation


# ── RPC dispatch (route_rpc_request) ───────────────────────────────────────────


def _zones_params():
    return {
        "zones": [
            {
                "id": "main",
                "label": "Main Queue",
                "polygon_points": [
                    {"x": 0.1, "y": 0.1},
                    {"x": 0.9, "y": 0.1},
                    {"x": 0.5, "y": 0.9},
                ],
            },
            {
                "id": "secondary",
                "label": "Secondary Queue",
                "polygon_points": [
                    {"x": 0.1, "y": 0.1},
                    {"x": 0.3, "y": 0.1},
                    {"x": 0.2, "y": 0.5},
                ],
            },
        ]
    }


def _zone_params():
    """Backward-compatible single-zone params."""
    return {
        "polygon_points": [
            {"x": 0.1, "y": 0.1},
            {"x": 0.9, "y": 0.1},
            {"x": 0.5, "y": 0.9},
        ],
    }


def test_route_set_queue_zones():
    before = state.active_zones
    req = RPCRequest(
        jsonrpc="2.0", id=1, method="set_queue_zones", params=_zones_params()
    )
    resp = route_rpc_request(req)
    assert resp.error is None
    assert resp.result["status"] == "success"
    assert resp.result["zone_count"] == 2
    # State mutation persists on the shared boundary.
    assert len(state.active_zones) == 2
    assert state.active_zones != before


def test_route_set_queue_zone_deprecated():
    """Deprecated set_queue_zone method still works, wraps into 1-element zones."""
    req = RPCRequest(
        jsonrpc="2.0", id=1, method="set_queue_zone", params=_zone_params()
    )
    resp = route_rpc_request(req)
    assert resp.error is None
    assert resp.result["status"] == "success"
    assert resp.result["zone_count"] == 1
    assert len(state.active_zones) == 1


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
