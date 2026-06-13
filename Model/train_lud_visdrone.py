from pathlib import Path
import multiprocessing
import os

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
from ultralytics import YOLO


ROOT = Path(__file__).resolve().parent
DATA_YAML = ROOT / "visdrone.yaml"
MODEL_YAML = ROOT / "lud_yolov8s_visdrone.yaml"
PRETRAINED_WEIGHTS = ROOT / "yolov8s.pt"


def train_lud_visdrone():
    model = YOLO(str(MODEL_YAML))

    if PRETRAINED_WEIGHTS.exists():
        model.load(str(PRETRAINED_WEIGHTS))

    results = model.train(
        data=str(DATA_YAML),
        epochs=100,
        imgsz=960,
        batch=4,
        lr0=0.003,
        lrf=0.01,
        patience=20,
        mosaic=1.0,
        copy_paste=0.2,
        mixup=0.1,
        degrees=5.0,
        scale=0.3,
        cls=2.0,
        box=7.5,
        iou=0.5,
        device=0,
        workers=0,
        cache=False,
        amp=True,
        val=True,
        plots=True,
        seed=0,
        project=str(ROOT / "runs" / "detect"),
        name="visdrone_lud_yolov8s",
    )

    model.val(data=str(DATA_YAML), imgsz=960, batch=4, device=0, workers=0)
    model.export(format="onnx", opset=13)
    return results


if __name__ == "__main__":
    multiprocessing.freeze_support()
    train_lud_visdrone()
