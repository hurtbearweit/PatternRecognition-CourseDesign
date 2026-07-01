from pathlib import Path
import multiprocessing
import os

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

from ultralytics import YOLO


ROOT = Path(__file__).resolve().parent
MODEL_YAML = ROOT / "prnet_yolov8s_week15.yaml"
TRAIN_CFG = ROOT / "train_config_prnet.yaml"
PRETRAINED_WEIGHTS = ROOT / "yolov8s.pt"


def train_prnet():
    """Train PRNet-YOLOv8s with the same week-15 settings as the baselines."""
    model = YOLO(str(MODEL_YAML))

    if PRETRAINED_WEIGHTS.exists():
        model.load(str(PRETRAINED_WEIGHTS))

    results = model.train(
        cfg=str(TRAIN_CFG),
        project=str(ROOT / "runs" / "detect"),
        name="week15_prnet",
        exist_ok=True,
    )

    metrics = model.val()
    return results, metrics


if __name__ == "__main__":
    multiprocessing.freeze_support()
    train_prnet()
