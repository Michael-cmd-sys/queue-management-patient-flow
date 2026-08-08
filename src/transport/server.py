"""
FastAPI Server providing WebSocket-RPC & MJPEG Video Streaming Gateway.
Bridges the ML Vision Pipeline with the OctaneJS Interactive Dashboard.

This module contains only transport-layer logic (HTTP/WebSocket routing,
CORS, video streaming). All RPC dispatch is delegated to a pure,
testable handler in transport.dispatch.
"""

import asyncio
import json
from typing import Dict, List, Set, Tuple, Any

import cv2
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from src.domain.config import PipelineConfig, ROIConfig
from src.domain.schema import Point, QueueSnapshot
from src.vision.detector import load_yolo_model, detect_frame_objects
from src.vision.tracker import create_tracker, update_tracks
from src.analytics.queue_math import compute_queue_snapshot
from src.pipeline.overlay import draw_pipeline_overlay
from src.transport.protocol import (
    RPCRequest,
    RPCResponse,
    RPCError,
    RPCEvent,
    SetQueueZoneParams,
)

_CR_LF = bytes([13, 10])
_FRAME_BOUNDARY = b"--frame"


app = FastAPI(
    title="Patient Queue Flow Surveillance RPC Gateway",
    description="WebSocket-RPC and Video Streaming Server for Patient Flow Analytics",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SystemState:
    """Mutable process state, isolated at the transport boundary."""

    def __init__(self):
        self.config = PipelineConfig()
        self.active_roi_points: Tuple[Point, ...] = self.config.roi.polygon_points
        self.latest_snapshot: QueueSnapshot | None = None
        self.track_history: Dict[int, float] = {}
        self.active_websockets: Set[WebSocket] = set()


state = SystemState()

# The vision runtime is initialized lazily so that importing this module (and
# unit tests that exercise routing / REST handlers) does not pay the YOLO
# startup cost. The model is only loaded on the first video/metrics request.
_yolo_model = None
_byte_tracker = None


def get_vision_runtime():
    """Lazily initialize and cache the vision model + tracker."""
    global _yolo_model, _byte_tracker
    if _yolo_model is None or _byte_tracker is None:
        print(f"Initializing YOLOv8 model from {state.config.vision.model_path}...")
        _yolo_model = load_yolo_model(state.config.vision)
        _byte_tracker = create_tracker(state.config.tracker)
    return _yolo_model, _byte_tracker


async def broadcast_event(event_name: str, payload: Dict[str, Any]):
    """Broadcast an RPC event notification to all connected WebSockets."""
    event = RPCEvent(event=event_name, data=payload)
    message_str = event.model_dump_json()
    disconnected = set()

    for ws in state.active_websockets:
        try:
            await ws.send_text(message_str)
        except Exception:
            disconnected.add(ws)

    state.active_websockets -= disconnected


def route_rpc_request(req: RPCRequest) -> RPCResponse:
    """
    Transport-layer dispatch for a single JSON-RPC 2.0 request.

    Decoupled from the WebSocket loop so it can be unit-tested without a model
    or a live connection. Mutates the shared `state` boundary only through the
    documented handlers.
    """
    try:
        if req.method == "set_queue_zone":
            params = SetQueueZoneParams(**(req.params or {}))
            new_points = tuple(Point(p.x, p.y) for p in params.polygon_points)
            state.active_roi_points = new_points
            return RPCResponse(
                id=req.id,
                result={"status": "success", "vertex_count": len(new_points)},
            )

        if req.method == "get_current_metrics":
            snapshot = state.latest_snapshot
            if snapshot is not None:
                return RPCResponse(
                    id=req.id,
                    result={
                        "in_queue_count": snapshot.in_queue_count,
                        "out_of_queue_count": snapshot.out_of_queue_count,
                        "estimated_wait_time_min": round(
                            snapshot.estimated_wait_time_sec / 60.0, 1
                        ),
                    },
                )
            return RPCResponse(id=req.id, result={"status": "initializing"})

        return RPCResponse(
            id=req.id,
            error=RPCError(code=-32601, message="Method '%s' not found" % req.method),
        )
    except Exception as err:
        return RPCResponse(
            id=req.id,
            error=RPCError(code=-32600, message="Invalid RPC Request: %s" % err),
        )


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "patient-queue-flow-rpc"}


@app.get("/api/roi")
async def get_roi():
    """Fetch current ROI polygon points."""
    return {
        "zone_name": state.config.roi.zone_name,
        "polygon_points": [{"x": p.x, "y": p.y} for p in state.active_roi_points],
    }


@app.post("/api/roi")
async def set_roi_rest(params: SetQueueZoneParams):
    """REST endpoint (fallback) to set queue ROI polygon points."""
    new_points = tuple(Point(p.x, p.y) for p in params.polygon_points)
    state.active_roi_points = new_points

    await broadcast_event(
        "roi_updated",
        {
            "zone_name": params.zone_name,
            "polygon_points": [{"x": p.x, "y": p.y} for p in new_points],
        },
    )
    return {"status": "success", "vertex_count": len(new_points)}


def generate_video_mjpeg():
    """
    Generator streaming annotated MJPEG frames with live detection, tracking,
    ROI polygon boundaries, and metrics HUD overlay.
    """
    video_path = state.config.video_source
    if not video_path.exists():
        raise FileNotFoundError(f"Video file missing: {video_path}")

    yolo_model, byte_tracker = get_vision_runtime()

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"Failed to open video file {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    frame_idx = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            # Loop the demo video continuously.
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            frame_idx = 0
            continue

        timestamp = frame_idx / fps

        poly_pixel_pts = tuple(
            Point(
                x=pt.x * width if pt.x <= 1.0 else pt.x,
                y=pt.y * height if pt.y <= 1.0 else pt.y,
            )
            for pt in state.active_roi_points
        )

        detections = detect_frame_objects(yolo_model, frame, state.config.vision)
        tracks, state.track_history = update_tracks(
            tracker=byte_tracker,
            detections=detections,
            timestamp=timestamp,
            queue_polygon=poly_pixel_pts,
            track_history=state.track_history,
        )

        snapshot = compute_queue_snapshot(
            frame_index=frame_idx,
            timestamp=timestamp,
            tracks=tracks,
            service_rate_per_min=state.config.analytics.service_rate_per_min,
        )
        state.latest_snapshot = snapshot

        annotated_frame = draw_pipeline_overlay(
            frame=frame,
            tracks=tracks,
            snapshot=snapshot,
            roi_config=ROIConfig(polygon_points=state.active_roi_points),
            frame_width=width,
            frame_height=height,
        )

        _, jpeg_buf = cv2.imencode(
            ".jpg", annotated_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80]
        )
        frame_bytes = jpeg_buf.tobytes()

        yield (
            _FRAME_BOUNDARY
            + _CR_LF
            + b"Content-Type: image/jpeg"
            + _CR_LF
            + _CR_LF
            + frame_bytes
            + _CR_LF
        )
        frame_idx += 1


@app.get("/api/video_feed")
async def video_feed():
    """Stream live annotated video feed as MJPEG multipart stream."""
    return StreamingResponse(
        generate_video_mjpeg(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


@app.websocket("/ws/rpc")
async def websocket_rpc_endpoint(websocket: WebSocket):
    """WebSocket endpoint implementing JSON-RPC 2.0 protocol & live telemetry."""
    await websocket.accept()
    state.active_websockets.add(websocket)
    print(f"WebSocket client connected. Total clients: {len(state.active_websockets)}")

    async def metrics_broadcaster():
        try:
            while True:
                await asyncio.sleep(1.0)
                if state.latest_snapshot:
                    s = state.latest_snapshot
                    payload = {
                        "timestamp": round(s.timestamp, 2),
                        "frame_index": s.frame_index,
                        "in_queue_count": s.in_queue_count,
                        "out_of_queue_count": s.out_of_queue_count,
                        "total_active_tracks": s.total_active_tracks,
                        "active_queue_ids": list(s.active_queue_ids),
                        "avg_dwell_time_sec": round(s.avg_dwell_time_sec, 2),
                        "estimated_wait_time_sec": round(s.estimated_wait_time_sec, 2),
                        "estimated_wait_time_min": round(
                            s.estimated_wait_time_sec / 60.0, 1
                        ),
                    }
                    event = RPCEvent(event="queue_metrics_update", data=payload)
                    await websocket.send_text(event.model_dump_json())
        except Exception:
            pass

    broadcast_task = asyncio.create_task(metrics_broadcaster())

    try:
        while True:
            raw_text = await websocket.receive_text()
            msg = None
            try:
                msg = json.loads(raw_text)
                req = RPCRequest(**msg)
                response = route_rpc_request(req)
                await websocket.send_text(response.model_dump_json())
            except Exception as err:
                err_resp = RPCResponse(
                    id=msg.get("id") if isinstance(msg, dict) else None,
                    error=RPCError(
                        code=-32600,
                        message="Invalid RPC Request: %s" % err,
                    ),
                )
                await websocket.send_text(err_resp.model_dump_json())
    except WebSocketDisconnect:
        state.active_websockets.discard(websocket)
        broadcast_task.cancel()
        print("WebSocket client disconnected.")


__all__ = ["app", "state", "route_rpc_request", "get_vision_runtime"]
