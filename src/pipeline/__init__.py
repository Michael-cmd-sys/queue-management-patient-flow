"""Pipeline package: frame processing, orchestration, visualization, and export.

Structure:
- core.py: Pure pipeline logic (process single frame, advance state)
- overlay.py: Drawing/visualization utilities
- export.py: JSON/CSV serialization of pipeline artifacts
- runner.py: I/O orchestration (video read/write, config, main loop)
"""

from src.pipeline.core import process_frame, advance_tracker_state
from src.pipeline.overlay import draw_pipeline_overlay
from src.pipeline.export import export_metrics_json
from src.pipeline.runner import run_pipeline

__all__ = [
    "process_frame",
    "advance_tracker_state",
    "draw_pipeline_overlay",
    "export_metrics_json",
    "run_pipeline",
]
