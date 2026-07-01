"""Run trained models on the fixed 15 sample images.

Example:
    python 18周/scripts/predict_15_images.py \
      --weights yolo=runs/detect/week18_yolov8s_1280/weights/best.pt \
      --weights if_yolo=runs/detect/week18_if_yolo_1280/weights/best.pt \
      --weights csfmlite=runs/detect/week18_if_wiou_csfmlite_1280/weights/best.pt \
      --weights final_wff=runs/detect/week18_if_wiou_csfmlite_wff_1280/weights/best.pt
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from ultralytics import YOLO


ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--weights", action="append", required=True, help="Format: name=path/to/best.pt")
    parser.add_argument("--source", default=str(ROOT / "sample_images"))
    parser.add_argument("--device", default=None)
    parser.add_argument("--imgsz", type=int, default=1280)
    parser.add_argument("--conf", type=float, default=0.25)
    parser.add_argument("--iou", type=float, default=0.7)
    parser.add_argument("--project", default=str(ROOT / "results" / "predictions"))
    return parser.parse_args()


def parse_weight_items(items: list[str]) -> list[tuple[str, Path]]:
    parsed = []
    for item in items:
        if "=" not in item:
            raise ValueError(f"--weights must be name=path, got {item}")
        name, value = item.split("=", 1)
        path = Path(value)
        if not path.is_absolute():
            path = ROOT / path
        if not path.exists():
            raise FileNotFoundError(path)
        parsed.append((name, path))
    return parsed


def main() -> None:
    args = parse_args()
    source = Path(args.source)
    if not source.exists():
        raise FileNotFoundError(source)
    project = Path(args.project)
    project.mkdir(parents=True, exist_ok=True)

    rows = []
    for name, weight in parse_weight_items(args.weights):
        model = YOLO(str(weight))
        kwargs = {
            "source": str(source),
            "imgsz": args.imgsz,
            "conf": args.conf,
            "iou": args.iou,
            "project": str(project),
            "name": name,
            "save": True,
            "exist_ok": False,
        }
        if args.device is not None:
            kwargs["device"] = args.device
        results = model.predict(**kwargs)
        rows.append({"model": name, "weights": str(weight), "images": len(results), "output_dir": str(project / name)})

    with (project / "prediction_manifest.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["model", "weights", "images", "output_dir"])
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()

