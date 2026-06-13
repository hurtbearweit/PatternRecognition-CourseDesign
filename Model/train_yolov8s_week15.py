from pathlib import Path
import multiprocessing
import os

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

from ultralytics import YOLO


ROOT = Path(__file__).resolve().parent
TRAIN_CFG = ROOT / "train_config.yaml"
PRETRAINED_WEIGHTS = ROOT / "yolov8s.pt"


def train_yolov8s_baseline():
    """Train the original YOLOv8s with the week-15 unified config."""
    if not PRETRAINED_WEIGHTS.exists():
        raise FileNotFoundError(f"Pretrained weights not found: {PRETRAINED_WEIGHTS}")

    model = YOLO(str(PRETRAINED_WEIGHTS))

    results = model.train(
        cfg=str(TRAIN_CFG),
        project=str(ROOT / "runs" / "detect"),
        name="week15_yolov8s_baseline",
        exist_ok=False,
    )

    metrics = model.val()
    return results, metrics


if __name__ == "__main__":
    multiprocessing.freeze_support()
    train_yolov8s_baseline()
