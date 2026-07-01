"""Train one week17 experiment with the unified train_config.yaml.

Examples:
    python week17/scripts/train_experiment.py --model A --name week17_A_if_wiou_csfmlite_seed0 --device 0 --seed 0
    python week17/scripts/train_experiment.py --model B --name week17_B_if_wiou_csfmlite_wff_seed0 --device 0 --seed 0
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
TRAIN_CFG = ROOT / "configs" / "train_config.yaml"
DATA_CFG = ROOT / "configs" / "visdrone.yaml"
RUNTIME_CFG = ROOT / "logs" / "runtime_train_config.yaml"
CONFIGS = {
    "A": ROOT / "configs" / "if_yolov8s_wiou_csfmlite.yaml",
    "B": ROOT / "configs" / "if_yolov8s_wiou_csfmlite_wff_p3p2.yaml",
}
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True, help="'A', 'B', or path to a YAML file")
    parser.add_argument("--name", required=True)
    parser.add_argument("--device", default=None)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--project", default=str(ROOT / "runs" / "detect"))
    parser.add_argument("--resume", action="store_true")
    return parser.parse_args()


def resolve_model(value: str) -> Path:
    path = CONFIGS.get(value.upper(), Path(value))
    path = path if path.is_absolute() else (ROOT / path)
    if not path.exists():
        raise FileNotFoundError(f"Model YAML not found: {path}")
    return path.resolve()


def read_imgsz() -> int:
    cfg = yaml.safe_load(TRAIN_CFG.read_text(encoding="utf-8"))
    return int(cfg.get("imgsz", cfg.get("img_size", 960)))


def make_runtime_train_cfg() -> Path:
    """Preserve train_config.yaml params and replace only the data path for servers."""
    cfg = yaml.safe_load(TRAIN_CFG.read_text(encoding="utf-8"))
    cfg["data"] = str(DATA_CFG.resolve())
    RUNTIME_CFG.parent.mkdir(parents=True, exist_ok=True)
    RUNTIME_CFG.write_text(yaml.safe_dump(cfg, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return RUNTIME_CFG


def extract_last_metrics(results_csv: Path) -> dict:
    if not results_csv.exists():
        return {}
    with results_csv.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        return {}

    def fnum(row: dict, key: str) -> float | None:
        for k, v in row.items():
            if k and k.strip() == key and v not in ("", None):
                try:
                    return float(v)
                except ValueError:
                    return None
        return None

    best = max(rows, key=lambda r: fnum(r, "metrics/mAP50-95(B)") or -1)
    return {
        "best_epoch": int(float(best.get("epoch", 0))),
        "precision": fnum(best, "metrics/precision(B)"),
        "recall": fnum(best, "metrics/recall(B)"),
        "map50": fnum(best, "metrics/mAP50(B)"),
        "map50_95": fnum(best, "metrics/mAP50-95(B)"),
    }


def save_summary(run_dir: Path, model_yaml: Path, name: str, seed: int) -> None:
    metrics = extract_last_metrics(run_dir / "results.csv")
    best = run_dir / "weights" / "best.pt"
    summary = {
        "name": name,
        "seed": seed,
        "model_yaml": str(model_yaml),
        "run_dir": str(run_dir),
        "best_pt": str(best) if best.exists() else None,
        **metrics,
    }
    (run_dir / "week17_metrics_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    with (run_dir / "week17_metrics_summary.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(summary.keys()))
        writer.writeheader()
        writer.writerow(summary)


def main() -> None:
    args = parse_args()
    model_yaml = resolve_model(args.model)
    project = Path(args.project)
    project = project if project.is_absolute() else (ROOT / project)
    run_dir = project / args.name

    if args.resume:
        last_pt = run_dir / "weights" / "last.pt"
        if not last_pt.exists():
            raise FileNotFoundError(f"resume=True but last.pt does not exist: {last_pt}")
    elif run_dir.exists():
        raise FileExistsError(f"Run directory already exists: {run_dir}")

    project.mkdir(parents=True, exist_ok=True)
    imgsz = read_imgsz()
    runtime_cfg = make_runtime_train_cfg()

    model = YOLO(str(model_yaml))
    model.info(imgsz=imgsz)
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

    logging.info("Starting train: %s", train_kwargs)
    model.train(**train_kwargs)

    best_pt = run_dir / "weights" / "best.pt"
    if not best_pt.exists():
        raise FileNotFoundError(f"Training finished but best.pt is missing: {best_pt}")
    best_model = YOLO(str(best_pt))
    val_kwargs = {"data": str(DATA_CFG), "imgsz": imgsz, "plots": True, "save_json": True}
    if args.device is not None:
        val_kwargs["device"] = args.device
    best_model.val(**val_kwargs)

    manifest_dir = run_dir / "week17_inputs"
    manifest_dir.mkdir(exist_ok=True)
    for path in (TRAIN_CFG, runtime_cfg, DATA_CFG, model_yaml):
        shutil.copy2(path, manifest_dir / path.name)
    save_summary(run_dir, model_yaml, args.name, args.seed)
    logging.info("Done: %s", run_dir)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        logging.exception("Training failed: %s", exc)
        sys.exit(1)
