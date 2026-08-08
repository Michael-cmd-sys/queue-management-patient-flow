"""
Backward-compatible re-exports.

The RPC server has been moved to src.transport/server.py.
This module re-exports for backward compatibility.
"""

from src.transport.server import (
    app,
    state,
    route_rpc_request,
    get_vision_runtime,
    broadcast_event,
    generate_video_mjpeg,
)

__all__ = [
    "app",
    "state",
    "route_rpc_request",
    "get_vision_runtime",
    "broadcast_event",
    "generate_video_mjpeg",
]
