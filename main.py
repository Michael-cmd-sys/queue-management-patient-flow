"""
CLI entrypoint for Queue Management via Surveillance Camera for Patient Flow.

Defines configuration inline, then delegates to the pipeline runner.
"""

from pathlib import Path

from src.domain.config import PipelineConfig, ROIConfig, VisionConfig, AnalyticsConfig
from src.domain.schema import Point, Zone
from src.pipeline.runner import run_pipeline


def main():
    print("=" * 60)
    print(" Queue Management via Surveillance Camera for Patient Flow ")
    print(" KNUST Mathematics Thesis Implementation Pipeline ")
    print("=" * 60)

    # Define custom ROI queue zone tailored for sample video
    custom_roi = ROIConfig(
        zones=(
            Zone(
                id="main",
                label="Patient Triage Queue Line",
                points=(
                    Point(0.05, 0.10),
                    Point(0.95, 0.10),
                    Point(0.95, 0.95),
                    Point(0.05, 0.95),
                ),
            ),
        ),
    )

    config = PipelineConfig(
        vision=VisionConfig(
            model_path=Path("models/best.pt"),
            confidence_threshold=0.20,
        ),
        roi=custom_roi,
        video_source=Path("data/input_videos/short video sample/sample.mp4"),
        output_dir=Path("data/output"),
    )

    snapshots = run_pipeline(config)
    print(f"Successfully processed {len(snapshots)} video frames!")


if __name__ == "__main__":
    main()
