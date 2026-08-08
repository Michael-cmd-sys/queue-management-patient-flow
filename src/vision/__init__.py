"""
Vision and object detection package.
"""

from src.vision.detector import load_yolo_model, detect_frame_objects

__all__ = ["load_yolo_model", "detect_frame_objects"]
