"""Domain exception hierarchy for pipeline operations."""

from dataclasses import dataclass


class PipelineError(Exception):
    """Base exception for all pipeline domain errors."""


class ModelLoadError(PipelineError):
    """Raised when a vision model cannot be loaded."""


class VideoSourceError(PipelineError):
    """Raised when a video source cannot be opened or is missing."""


class ConfigError(PipelineError):
    """Raised when configuration is invalid or inconsistent."""
