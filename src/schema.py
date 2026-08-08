"""
Backward-compatible re-exports.

The domain types (schema.py, config.py) have been moved to src.domain/.
This module re-exports them so existing imports like `from src.schema import Point`
continue to work during the transition period.
"""

from src.domain.schema import *  # noqa: F401,F403
from src.domain.config import *  # noqa: F401,F403
