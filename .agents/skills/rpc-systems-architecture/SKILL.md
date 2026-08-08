---
name: rpc-systems-architecture
description: Guidelines for building production-grade, functional RPC microservices and real-time WebSocket systems
---

# Systems Solution Architecture: Functional RPC & Real-Time Telemetry

## Core Architectural Principles

### 1. Functional Procedure Handlers
- **Procedure as a Pure Mapping**: Every RPC method must be modeled as a pure input-to-output mapping function:
  $$f: (\text{Params}, \text{CurrentState}) \rightarrow (\text{Result}, \text{NewState})$$
- **Explicit Schema Contracts**: Every RPC method has a strict, immutable Pydantic/TypeScript contract (`Request`, `Response`, `Event`).
- **No Swallowed Exceptions**: Errors must return explicit, typed `RPCError` objects with standardized codes (-32600 invalid request, -32602 invalid params, -32000 internal execution error).

### 2. Event-Driven Telemetry Streaming
- **Subscription Model**: Clients send `SubscribeQueueMetrics(interval_ms)`. The server yields immutable `QueueMetricsEvent` payloads over a persistent WebSocket stream.
- **Backpressure & Frame Dropping**: High-frequency video feeds drop stale frames if client consumer lag is detected, preventing memory ballooning.

### 3. Readability & Code Reasoning Rules
- **Self-Documenting Signatures**: Every public method must declare full input/output types and concise mathematical docstrings.
- **Separation of Concerns**:
  - `protocol.py`: Pure type definitions.
  - `handlers.py`: Pure domain logic handlers.
  - `server.py`: Network transport adapter (FastAPI / WebSockets).
