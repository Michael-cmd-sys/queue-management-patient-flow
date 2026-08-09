"""
JSON-RPC 2.0 and Event Streaming Protocol Definitions.
Strict typing and serialization models for frontend-backend contract safety.
"""

from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field


class PointDTO(BaseModel):
    """2D Point Coordinate DTO (Normalized 0.0 - 1.0 or Pixel space)."""

    x: float = Field(..., description="X coordinate")
    y: float = Field(..., description="Y coordinate")


class RPCRequest(BaseModel):
    """Standard JSON-RPC 2.0 Request Payload."""

    jsonrpc: str = Field(default="2.0", description="Protocol version")
    id: Union[int, str] = Field(..., description="Request identifier")
    method: str = Field(..., description="RPC method name (e.g. 'set_queue_zones')")
    params: Optional[Dict[str, Any]] = Field(
        default=None, description="Procedure arguments"
    )


class RPCError(BaseModel):
    """Standard JSON-RPC 2.0 Error Object."""

    code: int = Field(
        ...,
        description="Error code (-32600 invalid, -32602 invalid params, -32000 internal error)",
    )
    message: str = Field(..., description="Human readable error message")
    data: Optional[Any] = Field(default=None, description="Optional diagnostic details")


class RPCResponse(BaseModel):
    """Standard JSON-RPC 2.0 Response Payload."""

    jsonrpc: str = Field(default="2.0")
    id: Optional[Union[int, str]] = None
    result: Optional[Any] = None
    error: Optional[RPCError] = None


class RPCEvent(BaseModel):
    """Server-to-Client Event Broadcast Notification."""

    jsonrpc: str = Field(default="2.0")
    event: str = Field(..., description="Event name (e.g. 'queue_metrics_update')")
    data: Dict[str, Any] = Field(..., description="Event payload")


class ZoneDTO(BaseModel):
    """A named queue zone definition for the set_queue_zones procedure."""

    id: str = Field(default="main", description="Unique zone identifier")
    label: str = Field(
        default="Main Queue Zone", description="Human-readable zone name"
    )
    polygon_points: List[PointDTO] = Field(
        ..., min_length=3, description="List of at least 3 polygon points"
    )


class SetQueueZonesParams(BaseModel):
    """Parameters for 'set_queue_zones' procedure — accepts multiple named zones."""

    zones: List[ZoneDTO] = Field(
        ..., min_length=1, description="List of at least 1 zone definition"
    )


class SetQueueZoneParams(BaseModel):
    """Backward-compatible single-zone parameters (deprecated; use SetQueueZonesParams)."""

    zone_name: str = Field(default="Main Queue Area")
    polygon_points: List[PointDTO] = Field(
        ..., min_length=3, description="List of at least 3 polygon points"
    )


class QueueMetricsPayload(BaseModel):
    """Live Telemetry Payload broadcasted over WebSocket."""

    timestamp: float
    frame_index: int
    in_queue_count: int
    out_of_queue_count: int
    total_active_tracks: int
    active_queue_ids: List[int]
    avg_dwell_time_sec: float
    estimated_wait_time_sec: float
    estimated_wait_time_min: float
