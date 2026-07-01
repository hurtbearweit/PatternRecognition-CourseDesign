"""Summarize week17 A/B multi-seed experiment results.

Example:
    python week17/scripts/summarize_multiseed.py --project week17/runs/detect
"""

from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNS = {
    "A": [f"week17_A_if_wiou_csfmlite_seed{i}" for i in range(3)],
    "B": [f"week17_B_if_wiou_csfmlite_wff_seed{i}" for i in range(3)],
}
METRICS = ["precision", "recall", "map50", "map50_95"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", default=str(ROOT / "runs" / "detect"))
    parser.add_argument("--output-dir", default=str(ROOT / "results" / "tables"))
    return parser.parse_args()


def read_results(run_dir: Path) -> dict:
    results_csv = run_dir / "results.csv"
    if not results_csv.exists():
        return {"run_dir": str(run_dir), "status": "missing_results"}
    with results_csv.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        return {"run_dir": str(run_dir), "status": "empty_results"}

    def get(row: dict, name: str) -> float | None:
        for key, value in row.items():
            if key and key.strip() == name and value not in ("", None):
                try:
                    return float(value)
                except ValueError:
                    return None
        return None

    best = max(rows, key=lambda row: get(row, "metrics/mAP50-95(B)") or -1)
    best_pt = run_dir / "weights" / "best.pt"
    return {
        "run_dir": str(run_dir),
        "status": "ok",
        "best_epoch": int(float(best.get("epoch", 0))),
        "precision": get(best, "metrics/precision(B)"),
        "recall": get(best, "metrics/recall(B)"),
        "map50": get(best, "metrics/mAP50(B)"),
        "map50_95": get(best, "metrics/mAP50-95(B)"),
        "best_pt": str(best_pt) if best_pt.exists() else "",
        "weight_mb": round(best_pt.stat().st_size / 1024 / 1024, 3) if best_pt.exists() else None,
    }


def stats(values: list[float]) -> dict:
    if not values:
        return {"mean": None, "std": None, "min": None, "max": None}
    mean = sum(values) / len(values)
    var = sum((v - mean) ** 2 for v in values) / len(values)
    return {"mean": mean, "std": math.sqrt(var), "min": min(values), "max": max(values)}


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = sorted({key for row in rows for key in row})
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    args = parse_args()
    project = Path(args.project).resolve()
    output_dir = Path(args.output_dir).resolve()

    raw_rows: list[dict] = []
    for group, names in RUNS.items():
        for seed, name in enumerate(names):
            row = read_results(project / name)
            row.update({"group": group, "seed": seed, "name": name})
            raw_rows.append(row)

    summary_rows: list[dict] = []
    for group in RUNS:
        group_rows = [r for r in raw_rows if r["group"] == group and r["status"] == "ok"]
        for metric in METRICS:
            values = [float(r[metric]) for r in group_rows if r.get(metric) is not None]
            s = stats(values)
            summary_rows.append({"group": group, "metric": metric, "n": len(values), **s})

    write_csv(output_dir / "multiseed_raw.csv", raw_rows)
    write_csv(output_dir / "multiseed_summary.csv", summary_rows)

    a = next((r for r in summary_rows if r["group"] == "A" and r["metric"] == "map50_95"), {})
    b = next((r for r in summary_rows if r["group"] == "B" and r["metric"] == "map50_95"), {})
    recommendation = "insufficient results"
    if a.get("mean") is not None and b.get("mean") is not None:
        diff = float(b["mean"]) - float(a["mean"])
        if abs(diff) <= 0.002:
            recommendation = "A (差异 <= 0.002，优先选择结构更简单的 CSFM-Lite 主模型)"
        else:
            recommendation = "B" if diff > 0 else "A"

    lines = ["# Week17 Multi-Seed Summary", "", "## Raw Runs", ""]
    for row in raw_rows:
        lines.append(f"- {row['name']}: status={row['status']}, mAP50-95={row.get('map50_95')}, best_epoch={row.get('best_epoch')}")
    lines += ["", "## Statistics", "", "| group | metric | n | mean | std | min | max |", "|---|---:|---:|---:|---:|---:|---:|"]
    for row in summary_rows:
        lines.append(
            f"| {row['group']} | {row['metric']} | {row['n']} | {row['mean']} | {row['std']} | {row['min']} | {row['max']} |"
        )
    lines += ["", f"## Recommendation", "", recommendation]
    (output_dir / "multiseed_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()

