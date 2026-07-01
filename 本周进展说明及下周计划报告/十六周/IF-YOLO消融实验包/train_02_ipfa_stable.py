from pathlib import Path
import multiprocessing

from ultralytics import YOLO


ROOT = Path(__file__).resolve().parent


def train_ipfa_stable():
    model = YOLO(str(ROOT / "02_yolov8s_ipfa.yaml"))
    model.load("yolov8s.pt")
    results = model.train(
        cfg=str(ROOT / "train_config_ipfa_stable.yaml"),
        data=str(ROOT / "VisDrone_server.yaml"),
        project=str(ROOT / "runs" / "detect"),
        name="ablation_02_ipfa_stable",
        exist_ok=True,
    )
    metrics = model.val(data=str(ROOT / "VisDrone_server.yaml"))
    return results, metrics


if __name__ == "__main__":
    multiprocessing.freeze_support()
    train_ipfa_stable()
