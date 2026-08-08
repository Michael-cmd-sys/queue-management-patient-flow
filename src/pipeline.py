"""
Backward-compatible re-exports.

The pipeline orchestrator has been refactored into src.pipeline.runner.
This module re-exports run_pipeline and draw_pipeline_overlay for backward compatibility.
"""

from src.pipeline.runner import run_pipeline
from src.pipeline.overlay import draw_pipeline_overlay

__all__ = ["run_pipeline", "draw_pipeline_overlay"]
