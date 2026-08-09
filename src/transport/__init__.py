"""
Transport layer: RPC protocol definitions, server state, and FastAPI entry point.
"""

from src.transport.protocol import (
    PointDTO,
    RPCRequest,
    RPCResponse,
    RPCError,
    RPCEvent,
    ZoneDTO,
    SetQueueZonesParams,
    SetQueueZoneParams,
    QueueMetricsPayload,
)
from src.transport.server import app, state, route_rpc_request, get_vision_runtime

__all__ = [
    "PointDTO",
    "RPCRequest",
    "RPCResponse",
    "RPCError",
    "RPCEvent",
    "ZoneDTO",
    "SetQueueZonesParams",
    "SetQueueZoneParams",
    "QueueMetricsPayload",
    "app",
    "state",
    "route_rpc_request",
    "get_vision_runtime",
]
