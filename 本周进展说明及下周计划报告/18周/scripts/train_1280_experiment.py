"""Train one 1280-size week18 experiment.

Examples:
    python 18周/scripts/train_1280_experiment.py --model yolo --name week18_yolov8s_1280 --device 0 --seed 0
    python 18周/scripts/train_1280_experiment.py --model final_wff --name week18_final_wff_1280 --device 0 --seed 0
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import shutil
import sys
from pathlib import Path

import yaml
from ultralytics import YOLO


ROOT = Path(__file__).resolve().parents[1]
TRAIN_CFG = ROOT / "configs" / "train_config_1280.yaml"
DATA_CFG = ROOT / "configs" / "visdrone.yaml"
RUNTIME_CFG = ROOT / "logs" / "runtime_train_config_1280.yaml"
CONFIGS = {
    "yolo": ROOT / "configs" / "yolov8s.yaml",
    "if_yolo": ROOT / "configs" / "if_yolov8s.yaml",
    "csfmlite": ROOT / "configs" / "if_yolov8s_wiou_csfmlite.yaml",
    "final_wff": ROOT / "configs" / "if_yolov8s_wiou_csfmlite_wff_p3p2.yaml",
}

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True, choices=sorted(CONFIGS))
    parser.add_argument("--name", required=True)
    parser.add_argument("--device", default=None)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--project", default=str(ROOT / "runs" / "detect"))
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--pretrained", default=None, help="Optional pretrained .pt path, e.g. yolov8s.pt")
    return parser.parse_args()


def make_runtime_cfg() -> Path:
    cfg = yaml.safe_load(TRAIN_CFG.read_text(encoding="utf-8"))
    cfg["data"] = str(DATA_CFG.resolve())
    cfg["imgsz"] = 1280
    RUNTIME_CFG.parent.mkdir(parents=True, exist_ok=True)
    RUNTIME_CFG.write_text(yaml.safe_dump(cfg, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return RUNTIME_CFG


def extract_best_metrics(results_csv: Path) -> dict:
    if not results_csv.exists():
        return {}
    with results_csv.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        return {}

    def fnum(row: dict, target: str) -> float | None:
        for key, value in row.items():
            if key and key.strip() == target and value not in ("", None):
                try:
                    return float(value)
                except ValueError:
                    return None
        return None

    best = max(rows, key=lambda row: fnum(row, "metrics/mAP50-95(B)") or -1)
    return {
        "best_epoch": int(float(best.get("epoch", 0))),
        "precision": fnum(best, "metrics/precision(B)"),
        "recall": fnum(best, "metrics/recall(B)"),
        "map50": fnum(best, "metrics/mAP50(B)"),
        "map50_95": fnum(best, "metrics/mAP50-95(B)"),
    }


def main() -> None:
    args = parse_args()
    model_yaml = CONFIGS[args.model]
    project = Path(args.project)
    project = project if project.is_absolute() else (ROOT / project)
    run_dir = project / args.name
    if args.resume:
        if not (run_dir / "weights" / "last.pt").exists():
            raise FileNotFoundError(f"Missing last.pt for resume: {run_dir}")
    elif run_dir.exists():
        raise FileExistsError(f"Run directory already exists: {run_dir}")

    runtime_cfg = make_runtime_cfg()
    model = YOLO(str(model_yaml))
    if args.pretrained:
        pretrained = Path(args.pretrained)
        if not pretrained.exists():
            raise FileNotFoundError(pretrained)
        model.load(str(pretrained))
    model.info(imgsz=1280)

    train_kwargs = {
        "cfg": str(runtime_cfg),
        "model": str(model_yaml),
        "project": str(project),
        "name": args.name,
        "seed": args.seed,
        "exist_ok": False,
    }
    if args.device is not None:
        train_kwargs["device"] = args.device
    if args.resume:
        train_kwargs["resume"] = True
    model.train(**train_kwargs)

    best_pt = run_dir / "weights" / "best.pt"
    if not best_pt.exists():
        raise FileNotFoundError(f"best.pt not found after training: {best_pt}")
    best_model = YOLO(str(best_pt))
    val_kwargs = {"data": str(DATA_CFG), "imgsz": 1280, "plots": True, "save_json": True}
    if args.device is not None:
        val_kwargs["device"] = args.device
    best_model.val(**val_kwargs)

    manifest_dir = run_dir / "week18_inputs"
    manifest_dir.mkdir(exist_ok=True)
    for path in (TRAIN_CFG, runtime_cfg, DATA_CFG, model_yaml):
        shutil.copy2(path, manifest_dir / path.name)

    summary = {
        "model_key": args.model,
        "name": args.name,
        "seed": args.seed,
        "imgsz": 1280,
        "model_yaml": str(model_yaml),
        "best_pt": str(best_pt),
        **extract_best_metrics(run_dir / "results.csv"),
    }
    (run_dir / "week18_metrics_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    logging.info("Done: %s", run_dir)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        logging.exception("Training failed: %s", exc)
        sys.exit(1)

