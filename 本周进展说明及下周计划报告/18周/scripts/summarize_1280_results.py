"""Summarize the four week18 1280 training results."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNS = {
    "yolo": "week18_yolov8s_1280",
    "if_yolo": "week18_if_yolo_1280",
    "csfmlite": "week18_if_wiou_csfmlite_1280",
    "final_wff": "week18_if_wiou_csfmlite_wff_1280",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", default=str(ROOT / "runs" / "detect"))
    parser.add_argument("--output", default=str(ROOT / "results" / "week18_1280_summary.csv"))
    return parser.parse_args()


def best_row(results_csv: Path) -> dict:
    if not results_csv.exists():
        return {"status": "missing_results"}
    with results_csv.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        return {"status": "empty_results"}

    def fnum(row: dict, target: str) -> float | None:
        for key, value in row.items():
            if key and key.strip() == target and value not in ("", None):
                try:
                    return float(value)
                except ValueError:
                    return None
        return None

    row = max(rows, key=lambda r: fnum(r, "metrics/mAP50-95(B)") or -1)
    return {
        "status": "ok",
        "best_epoch": int(float(row.get("epoch", 0))),
        "precision": fnum(row, "metrics/precision(B)"),
        "recall": fnum(row, "metrics/recall(B)"),
        "map50": fnum(row, "metrics/mAP50(B)"),
        "map50_95": fnum(row, "metrics/mAP50-95(B)"),
    }


def main() -> None:
    args = parse_args()
    project = Path(args.project).resolve()
    rows = []
    for key, run_name in RUNS.items():
        run_dir = project / run_name
        best_pt = run_dir / "weights" / "best.pt"
        row = {
            "model": key,
            "run_name": run_name,
            "run_dir": str(run_dir),
            "best_pt": str(best_pt) if best_pt.exists() else "",
        }
        row.update(best_row(run_dir / "results.csv"))
        rows.append(row)

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    md = output.with_suffix(".md")
    lines = ["# Week18 1280 Summary", "", "| model | status | best_epoch | precision | recall | mAP50 | mAP50-95 |", "|---|---|---:|---:|---:|---:|---:|"]
    for row in rows:
        lines.append(
            f"| {row['model']} | {row['status']} | {row.get('best_epoch', '')} | {row.get('precision', '')} | {row.get('recall', '')} | {row.get('map50', '')} | {row.get('map50_95', '')} |"
        )
    md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Saved {output} and {md}")


if __name__ == "__main__":
    main()

