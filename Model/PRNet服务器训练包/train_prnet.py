"""Train PRNet-YOLOv8s on VisDrone."""

from pathlib import Path
import argparse
import multiprocessing
import os

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

from ultralytics import YOLO


ROOT = Path(__file__).resolve().parent
MODEL_YAML = ROOT / "prnet_yolov8s.yaml"
DATA_YAML = ROOT / "VisDrone_server.yaml"
TRAIN_CFG = ROOT / "train_config.yaml"
OUTPUT_ROOT = ROOT / "runs" / "detect"


def train(resume: str | None = None):
    if resume:
        return YOLO(resume).train(resume=True)

    model = YOLO(str(MODEL_YAML))
    model.load("yolov8s.pt")
    results = model.train(
        cfg=str(TRAIN_CFG),
        data=str(DATA_YAML),
        project=str(OUTPUT_ROOT),
        name="week15_prnet",
        exist_ok=True,
    )
    model.val(data=str(DATA_YAML))
    return results


if __name__ == "__main__":
    multiprocessing.freeze_support()
    parser = argparse.ArgumentParser()
    parser.add_argument("--resume", type=str, default=None, help="Path to last.pt")
    args = parser.parse_args()
    train(args.resume)
