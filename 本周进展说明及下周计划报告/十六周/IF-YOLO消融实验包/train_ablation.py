"""Run one IF-YOLO ablation experiment."""

from pathlib import Path
import argparse
import multiprocessing

from ultralytics import YOLO


ROOT = Path(__file__).resolve().parent
EXPERIMENTS = {
    "baseline": ("01_yolov8s_baseline.yaml", "ablation_01_baseline"),
    "ipfa": ("02_yolov8s_ipfa.yaml", "ablation_02_ipfa"),
    "csfm": ("03_yolov8s_csfm.yaml", "ablation_03_csfm"),
    "fgafpn": ("04_yolov8s_fgafpn.yaml", "ablation_04_fgafpn"),
    "full": ("05_if_yolov8s_full.yaml", "ablation_05_if_yolo_full"),
}


def train(experiment: str, resume: str | None = None):
    if resume:
        return YOLO(resume).train(resume=True)

    yaml_name, run_name = EXPERIMENTS[experiment]
    model = YOLO(str(ROOT / yaml_name))
    model.load("yolov8s.pt")
    result = model.train(
        cfg=str(ROOT / "train_config.yaml"),
        data=str(ROOT / "VisDrone_server.yaml"),
        project=str(ROOT / "runs" / "detect"),
        name=run_name,
        exist_ok=True,
    )
    model.val(data=str(ROOT / "VisDrone_server.yaml"))
    return result


if __name__ == "__main__":
    multiprocessing.freeze_support()
    parser = argparse.ArgumentParser()
    parser.add_argument("--experiment", choices=EXPERIMENTS, required=True)
    parser.add_argument("--resume", default=None, help="Path to last.pt")
    args = parser.parse_args()
    train(args.experiment, args.resume)
