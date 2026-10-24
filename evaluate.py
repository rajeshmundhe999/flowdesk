"""Evaluation benchmark script for FlowDesk triage engine.

Evaluates predictions against a labeled ground-truth dataset and reports:
- Category & Severity Accuracy
- Confusion Matrix
- Per-category Precision, Recall, and F1-score
- Detailed breakdown of misclassifications and failure modes
"""

import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

from flowdesk.triage.rules import CATEGORIES, rules_triage


def load_labeled_dataset(path: Path | str) -> list[dict[str, str]]:
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"Labeled dataset not found: {file_path}")

    rows: list[dict[str, str]] = []
    with open(file_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append({k.strip(): v.strip() for k, v in r.items() if k})
    return rows


def evaluate_dataset(rows: list[dict[str, str]]) -> dict[str, Any]:
    total = len(rows)
    if total == 0:
        return {"error": "Dataset is empty"}

    cat_correct = 0
    sev_correct = 0

    # Confusion matrix: actual -> predicted -> count
    confusion_matrix: dict[str, dict[str, int]] = {
        act: {pred: 0 for pred in CATEGORIES} for act in CATEGORIES
    }

    # Per-category tracking: TP, FP, FN
    tp: dict[str, int] = defaultdict(int)
    fp: dict[str, int] = defaultdict(int)
    fn: dict[str, int] = defaultdict(int)

    misclassifications: list[dict[str, Any]] = []

    for r in rows:
        subject = r["subject"]
        body = r["body"]
        expected_cat = r["expected_category"]
        expected_sev = r["expected_severity"]
        tier = r.get("plan_tier", "free")

        res = rules_triage(subject, body, plan_tier=tier)
        predicted_cat = res.category
        predicted_sev = res.severity

        # Update category stats
        if expected_cat in confusion_matrix and predicted_cat in confusion_matrix[expected_cat]:
            confusion_matrix[expected_cat][predicted_cat] += 1

        if predicted_cat == expected_cat:
            cat_correct += 1
            tp[expected_cat] += 1
        else:
            fp[predicted_cat] += 1
            fn[expected_cat] += 1
            misclassifications.append({
                "id": r.get("id", "N/A"),
                "subject": subject,
                "expected_category": expected_cat,
                "predicted_category": predicted_cat,
                "confidence": res.confidence,
                "reason": res.reason,
            })

        # Update severity stats
        if predicted_sev == expected_sev:
            sev_correct += 1

    cat_accuracy = (cat_correct / total) * 100.0
    sev_accuracy = (sev_correct / total) * 100.0

    # Compute metrics per category
    metrics_per_cat: dict[str, dict[str, float]] = {}
    for cat in CATEGORIES:
        true_pos = tp[cat]
        false_pos = fp[cat]
        false_neg = fn[cat]
        precision = (
            (true_pos / (true_pos + false_pos) * 100.0) if (true_pos + false_pos) > 0 else 0.0
        )
        recall = (true_pos / (true_pos + false_neg) * 100.0) if (true_pos + false_neg) > 0 else 0.0
        f1 = (
            (2 * precision * recall / (precision + recall))
            if (precision + recall) > 0
            else 0.0
        )
        metrics_per_cat[cat] = {
            "precision": round(precision, 1),
            "recall": round(recall, 1),
            "f1": round(f1, 1),
            "support": true_pos + false_neg,
        }

    return {
        "total": total,
        "category_accuracy": round(cat_accuracy, 1),
        "severity_accuracy": round(sev_accuracy, 1),
        "metrics_per_category": metrics_per_cat,
        "confusion_matrix": confusion_matrix,
        "misclassifications": misclassifications,
    }


def format_evaluation_report(results: dict[str, Any]) -> str:
    lines = [
        "=" * 82,
        "  FlowDesk Triage Engine Evaluation Benchmark Report",
        "=" * 82,
        f"Total Samples:      {results['total']}",
        f"Category Accuracy:  {results['category_accuracy']}%",
        f"Severity Accuracy:  {results['severity_accuracy']}%",
        "-" * 82,
        f"{'Category':<20} {'Precision':<12} {'Recall':<12} {'F1-Score':<12} {'Support':<8}",
        "-" * 82,
    ]

    for cat, m in results["metrics_per_category"].items():
        if m["support"] > 0:
            p_str = f"{m['precision']:>7.1f}%"
            r_str = f"{m['recall']:>7.1f}%"
            f1_str = f"{m['f1']:>7.1f}%"
            sup_str = f"{m['support']:>5}"
            lines.append(f"{cat:<20} {p_str:>11} {r_str:>11} {f1_str:>11} {sup_str:>7}")

    lines.append("-" * 82)
    lines.append("\n### Confusion Matrix (Rows = Ground Truth, Columns = Predicted)")
    short_cats = [c[:8] for c in CATEGORIES]
    header = f"{'Actual':<18} | " + " | ".join(f"{sc:<8}" for sc in short_cats)
    lines.append(header)
    lines.append("-" * len(header))

    for act in CATEGORIES:
        counts = [str(results["confusion_matrix"][act][pred]) for pred in CATEGORIES]
        row_str = f"{act:<18} | " + " | ".join(f"{c:<8}" for c in counts)
        lines.append(row_str)

    lines.append("\n" + "=" * 82)
    lines.append(f"Misclassified Cases ({len(results['misclassifications'])} total):")
    lines.append("=" * 82)

    for m in results["misclassifications"]:
        exp = m["expected_category"]
        pred = m["predicted_category"]
        lines.append(f"[{m['id']}] Expected: '{exp}' -> Predicted: '{pred}'")
        lines.append(f"  Subject: \"{m['subject']}\"")
        lines.append(f"  Confidence: {m['confidence']} | Reason: {m['reason']}\n")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate FlowDesk triage accuracy")
    parser.add_argument(
        "--dataset",
        "-d",
        default="data/labeled_tickets.csv",
        help="Path to ground truth labeled dataset",
    )
    args = parser.parse_args()

    try:
        rows = load_labeled_dataset(args.dataset)
        results = evaluate_dataset(rows)
        print(format_evaluation_report(results))
    except Exception as exc:
        print(f"Evaluation error: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
