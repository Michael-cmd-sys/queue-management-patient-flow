"""
Visualization script to plot time-series Queue Count and Expected Wait Time (EWT).
Generates publication-quality charts for thesis documentation.
"""

import json
from pathlib import Path
import matplotlib.pyplot as plt
import pandas as pd


def plot_queue_metrics(metrics_json_path: Path, output_image_path: Path) -> None:
    """
    Load exported queue metrics JSON and plot time-series analytics.
    """
    if not metrics_json_path.exists():
        raise FileNotFoundError(f"Metrics file not found: {metrics_json_path}")

    with open(metrics_json_path, "r") as f:
        data = json.load(f)

    df = pd.DataFrame(data)
    df["ewt_minutes"] = df["estimated_wait_time_sec"] / 60.0

    plt.style.use("seaborn-v0_8-darkgrid" if "seaborn-v0_8-darkgrid" in plt.style.available else "default")
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6), sharex=True)

    # Subplot 1: Queue Count Over Time
    ax1.plot(df["timestamp_sec"], df["in_queue_count"], color="#1f77b4", linewidth=2, label="In-Queue Patient Count")
    ax1.set_ylabel("Patient Count", fontsize=11, fontweight="bold")
    ax1.set_title("Patient Queue Flow Analytics & Expected Wait Time (EWT)", fontsize=14, fontweight="bold", pad=12)
    ax1.legend(loc="upper right")
    ax1.grid(True, linestyle="--", alpha=0.6)

    # Subplot 2: Expected Wait Time (EWT) Over Time
    ax2.plot(df["timestamp_sec"], df["ewt_minutes"], color="#2ca02c", linewidth=2, linestyle="-", label="Estimated Wait Time (EWT)")
    ax2.set_xlabel("Video Time (Seconds)", fontsize=11, fontweight="bold")
    ax2.set_ylabel("EWT (Minutes)", fontsize=11, fontweight="bold")
    ax2.legend(loc="upper right")
    ax2.grid(True, linestyle="--", alpha=0.6)

    plt.tight_layout()
    output_image_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_image_path, dpi=300)
    plt.close()
    print(f"Chart successfully saved to {output_image_path.resolve()}")


if __name__ == "__main__":
    json_path = Path("data/output/queue_metrics.json")
    img_path = Path("data/output/queue_analytics_plot.png")
    plot_queue_metrics(json_path, img_path)
