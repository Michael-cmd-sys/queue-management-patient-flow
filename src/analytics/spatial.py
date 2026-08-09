"""
Pure functional spatial analysis routines (Point-in-Polygon raycasting).
Zero external dependencies beyond core python and schema definitions.
"""

from typing import Sequence, Tuple
from src.domain.schema import Point, BoundingBox, TrackedPerson, Zone


def is_point_in_polygon(point: Point, polygon: Sequence[Point]) -> bool:
    """
    Ray-Casting Algorithm to test if a 2D point is inside a polygon boundary.
    Pure function with zero side-effects.

    Args:
        point: Point(x, y) to evaluate.
        polygon: Sequence of Point(x, y) vertices defining the polygon boundary.

    Returns:
        True if the point lies inside or on the polygon boundary; False otherwise.

    .. note::
        When the point lies exactly on a polygon edge, the result depends on
        the specific vertex ordering and floating-point precision. The
        ray-casting algorithm does not guarantee consistent behavior for
        on-boundary points; callers requiring strict on-boundary membership
        should add an explicit epsilon tolerance or snap points to the
        nearest grid cell.
    """
    n = len(polygon)
    if n < 3:
        return False

    inside = False
    px, py = point.x, point.y

    j = n - 1
    for i in range(n):
        xi, yi = polygon[i].x, polygon[i].y
        xj, yj = polygon[j].x, polygon[j].y

        # Check if ray crosses edge
        intersect = ((yi > py) != (yj > py)) and (
            px < (xj - xi) * (py - yi) / (yj - yi + 1e-12) + xi
        )
        if intersect:
            inside = not inside
        j = i

    return inside


def is_person_in_queue(person_feet: Point, queue_polygon: Sequence[Point]) -> bool:
    """
    Determine if a person is in the queue area based on their ground contact point (feet).
    Pure function.
    """
    return is_point_in_polygon(person_feet, queue_polygon)


def is_person_in_zones(person_feet: Point, zones: Sequence[Zone]) -> Tuple[str, ...]:
    """
    Evaluate a point against multiple named queue zones.

    Pure function with zero side-effects.  For each zone the person's ground
    contact point is tested with the ray-casting algorithm; zones whose
    polygon contains the point are collected.

    Args:
        person_feet: Ground contact point (feet level) of the person.
        zones: Sequence of ``Zone`` definitions (each carries an ``id`` and
            ``points``).

    Returns:
        Tuple of zone IDs that contain the point (may be empty).
    """
    return tuple(
        zone.id for zone in zones if is_point_in_polygon(person_feet, zone.points)
    )
