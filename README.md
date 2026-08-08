# Queue Management via Surveillance Camera for Patient Flow

A computer vision and queue analytics prototype for tracking patient queue flow, dwell times, and occupancy metrics using video surveillance streams.

## Project Structure
```
queue-management-patient-flow/
├── docs/               # Literature review, research papers, and project documentation
├── models/             # Pre-trained and custom object detection/tracking models (.pt, .onnx, etc.)
├── data/               # Sample videos, test images, and annotated datasets
│   └── input_videos/   # Raw video clips for testing model pipeline
├── src/                # Core Python source code (detection, tracking, metrics, analytics)
└── README.md
```

## Features & Goals
- **Patient / Person Detection**: Detect individuals in queue zones using YOLO.
- **Multi-Object Tracking**: Track patients across video frames to prevent double-counting.
- **ROI / Zone Analytics**: Track queue length, entry/exit rates, and waiting (dwell) times.
- **Patient Flow Metrics**: Generate actionable queue metrics tailored for healthcare environments.
