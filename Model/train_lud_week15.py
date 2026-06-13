from pathlib import Path
import multiprocessing
import os

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

from ultralytics import YOLO


ROOT = Path(__file__).resolve().parent
MODEL_YAML = ROOT / "lud_yolov8s_week15.yaml"
TRAIN_CFG = ROOT / "train_config.yaml"
PRETRAINED_WEIGHTS = ROOT / "yolov8s.pt"


def train_lud_yolo():
    """Train LUD-YOLO with the week-15 unified training config."""
    model = YOLO(str(MODEL_YAML))

    if PRETRAINED_WEIGHTS.exists():
        model.load(str(PRETRAINED_WEIGHTS))

    results = model.train(
        cfg=str(TRAIN_CFG),
        project=str(ROOT / "runs" / "detect"),
        name="week15_lud_yolo",
        exist_ok=False,
    )

    metrics = model.val()
    return results, metrics


if __name__ == "__main__":
    multiprocessing.freeze_support()
    train_lud_yolo()
