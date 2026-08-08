"""
Pure functional spatial analysis routines (Point-in-Polygon raycasting).
Zero external dependencies beyond core python and schema definitions.
"""

from typing import Sequence
from src.domain.schema import Point, BoundingBox, TrackedPerson


def is_point_in_polygon(point: Point, polygon: Sequence[Point]) -> bool:
    """
    Ray-Casting Algorithm to test if a 2D point is inside a polygon boundary.
    Pure function with zero side-effects.

    Args:
        point: Point(x, y) to evaluate.
        polygon: Sequence of Point(x, y) vertices defining the polygon boundary.

    Returns:
        True if the point lies strictly inside or on the polygon, False otherwise.
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
