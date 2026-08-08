"""
Object detection wrapper using YOLOv8.
Transforms raw frame arrays into immutable Detection data contracts.
"""

from typing import Tuple, Any
import numpy as np

from src.schema import BoundingBox, Detection
from src.config import VisionConfig


def load_yolo_model(config: VisionConfig) -> Any:
    """
    Load YOLOv8 object detection model.
    Side-effecting model loader isolated at vision boundary.
    """
    from ultralytics import YOLO
    
    if not config.model_path.exists():
        raise FileNotFoundError(f"Model weight file not found at {config.model_path.resolve()}")
    
    model = YOLO(str(config.model_path))
    return model


def detect_frame_objects(
    model: Any,
    frame: np.ndarray,
    config: VisionConfig,
) -> Tuple[Detection, ...]:
    """
    Perform object detection on a single frame array.
    Pure transformation mapping (frame, config) -> Tuple[Detection, ...].

    Args:
        model: Loaded YOLO model instance.
        frame: OpenCV BGR image frame array.
        config: VisionConfig containing thresholds and target classes.

    Returns:
        Tuple of immutable Detection objects.
    """
    results = model.predict(
        source=frame,
        conf=config.confidence_threshold,
        iou=config.iou_threshold,
        classes=list(config.target_classes),
        verbose=False,
        device=config.device,
    )

    detections = []
    if not results or len(results) == 0:
        return ()

    result = results[0]
    boxes = result.boxes

    if boxes is None or len(boxes) == 0:
        return ()

    for box in boxes:
        # Extract coordinates (x1, y1, x2, y2)
        xyxy = box.xyxy[0].cpu().numpy()
        conf = float(box.conf[0].cpu().numpy())
        cls_id = int(box.cls[0].cpu().numpy())
        
        name = result.names.get(cls_id, "person")

        bbox = BoundingBox(
            x1=float(xyxy[0]),
            y1=float(xyxy[1]),
            x2=float(xyxy[2]),
            y2=float(xyxy[3]),
        )

        detections.append(
            Detection(
                box=bbox,
                confidence=conf,
                class_id=cls_id,
                class_name=name,
            )
        )

    return tuple(detections)
