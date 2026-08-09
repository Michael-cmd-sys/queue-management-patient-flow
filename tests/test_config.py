"""
Tests for ROIConfig construction, validation, and backward compatibility.
"""

import pytest

from src.domain.config import ROIConfig
from src.domain.schema import Point, Zone


def test_default_roi_has_single_main_zone():
    cfg = ROIConfig()
    assert len(cfg.zones) == 1
    assert cfg.zones[0].id == "main"
    assert cfg.zone_name == "Main Patient Queue Zone"
    assert len(cfg.polygon_points) == 4


def test_legacy_kwargs_build_main_zone():
    """Regression: legacy zone_name/polygon_points build a single 'main' zone."""
    cfg = ROIConfig(
        zone_name="Triage Queue",
        polygon_points=(
            Point(0.0, 0.0),
            Point(1.0, 0.0),
            Point(1.0, 1.0),
            Point(0.0, 1.0),
        ),
    )
    assert len(cfg.zones) == 1
    assert cfg.zones[0].id == "main"
    assert cfg.zones[0].label == "Triage Queue"
    assert cfg.zone_name == "Triage Queue"
    assert cfg.polygon_points == (
        Point(0.0, 0.0),
        Point(1.0, 0.0),
        Point(1.0, 1.0),
        Point(0.0, 1.0),
    )


def test_zones_based_construction_preserved():
    cfg = ROIConfig(
        zones=(
            Zone(id="a", label="Zone A", points=(Point(0.0, 0.0), Point(1.0, 0.0))),
            Zone(id="b", label="Zone B", points=(Point(0.0, 1.0), Point(1.0, 1.0))),
        )
    )
    assert [z.id for z in cfg.zones] == ["a", "b"]
    assert cfg.zone_name == "Zone A"


def test_duplicate_zone_ids_rejected():
    with pytest.raises(ValueError):
        ROIConfig(
            zones=(
                Zone(id="dup", label="One", points=(Point(0.0, 0.0), Point(1.0, 0.0))),
                Zone(id="dup", label="Two", points=(Point(0.0, 1.0), Point(1.0, 1.0))),
            )
        )
