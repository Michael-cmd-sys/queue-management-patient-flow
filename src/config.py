"""
Backward-compatible re-exports.

config.py has been moved to src.domain/. This module re-exports
so existing imports continue to work during the transition period.
"""

from src.domain.config import *  # noqa: F401,F403
