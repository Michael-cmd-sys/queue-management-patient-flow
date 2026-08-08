"""
Evaluation report aggregation for thesis-grade metric computation.

Bridges the immutable `QueueSnapshot` timeline produced by the vision pipeline
with ground-truth patient counts to produce a full `EvaluationReport`
(precision, recall, F1, MAPE, MAE, RMSE) suitable for publication and for the
absorbed hospital-module quality gate.
"""

import json
from pathlib import Path
from typing import Sequence, List

from src.domain.schema import QueueSnapshot, EvaluationReport
from src.evaluation.metrics import (
    calculate_mae,
    calculate_rmse,
    calculate_mape,
    calculate_expected_wait_time,
)


def _compute_precision_recall(
    predicted_counts: Sequence[int],
    ground_truth_counts: Sequence[int],
) -> tuple[float, float]:
    """
    Binary "queue non-empty" precision and recall across the sampled timeline.

    A true positive is a frame where the predicted count exceeds zero AND the
    ground-truth count exceeds zero. False positives are non-empty predictions
    on an empty queue; false negatives are missed detections on a non-empty
    queue.
    """
    predicted_flags = [p > 0 for p in predicted_counts]
    truth_flags = [g > 0 for g in ground_truth_counts]

    if len(predicted_flags) != len(truth_flags):
        raise ValueError(
            "predicted_counts and ground_truth_counts must align in length"
        )

    true_positives = sum(1 for p, g in zip(predicted_flags, truth_flags) if p and g)
    predicted_positives = sum(1 for p in predicted_flags if p)
    actual_positives = sum(1 for g in truth_flags if g)

    precision = true_positives / predicted_positives if predicted_positives > 0 else 0.0
    recall = true_positives / actual_positives if actual_positives > 0 else 0.0
    return precision, recall


def generate_evaluation_report(
    snapshots: List[QueueSnapshot],
    ground_truth_counts: Sequence[int],
    service_rate_per_min: float,
) -> EvaluationReport:
    """
    Compare the automated pipeline predictions against ground-truth patient
    counts and produce a complete evaluation report.

    Args:
        snapshots: Ordered list of QueueSnapshot records from the pipeline.
        ground_truth_counts: Ground-truth patient count per sampled frame,
            aligned 1:1 with the snapshots' in_queue_count.
        service_rate_per_min: Service rate (mu) used to derive expected-wait
            reference values.

    Returns:
        An immutable EvaluationReport populated with the computed metrics.
    """
    if len(snapshots) != len(ground_truth_counts):
        raise ValueError(
            f"snapshots length ({len(snapshots)}) must match ground_truth_counts "
            f"length ({len(ground_truth_counts)})"
        )

    predicted_counts = [s.in_queue_count for s in snapshots]
    predicted_waits = [s.estimated_wait_time_sec for s in snapshots]
    # Ground-truth wait time derived from the reference service rate.
    ground_truth_waits = [
        calculate_expected_wait_time(gc, service_rate_per_min)
        for gc in ground_truth_counts
    ]

    mae = calculate_mae(ground_truth_waits, predicted_waits)
    rmse = calculate_rmse(ground_truth_waits, predicted_waits)
    mape = calculate_mape(
        [float(g) for g in ground_truth_counts],
        [float(p) for p in predicted_counts],
    )

    precision, recall = _compute_precision_recall(predicted_counts, ground_truth_counts)
    f1 = (
        2 * precision * recall / (precision + recall)
        if (precision + recall) > 0
        else 0.0
    )

    return EvaluationReport(
        precision=precision,
        recall=recall,
        f1_score=f1,
        mape=mape,
        mae=mae,
        rmse=rmse,
    )


def save_evaluation_report(report: EvaluationReport, output_path: Path) -> None:
    """Persist an EvaluationReport to JSON for thesis documentation."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "precision": report.precision,
        "recall": report.recall,
        "f1_score": report.f1_score,
        "mape_percent": report.mape,
        "mae_sec": report.mae,
        "rmse_sec": report.rmse,
    }
    with open(output_path, "w") as f:
        json.dump(payload, f, indent=2)
    print(f"Evaluation report saved to: {output_path.resolve()}")


__all__ = ["generate_evaluation_report", "save_evaluation_report"]
