"""Pre-training checks for week-17 YAML files."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

import torch

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from train_week17_experiment import MODEL_MAP, patch_wiou_v3  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--models", nargs="*", default=list(MODEL_MAP), help="Model keys to check.")
    parser.add_argument("--imgsz", type=int, default=960, help="Random input size for forward check.")
    parser.add_argument("--device", default="cpu", help="cpu, cuda, or cuda:0.")
    return parser.parse_args()


def module_name(module) -> str:
    return module.__class__.__name__


def check_one(model_key: str, imgsz: int, device: str) -> dict:
    from ultralytics import YOLO
    from ultralytics.nn.modules import Concat
    from ultralytics.nn.modules.head import Detect
    from ultralytics.nn.modules.week17_modules import CSFMLite, DySampleYOLO, WeightedFeatureFusion

    yaml_path = MODEL_MAP[model_key]
    raw_yaml = yaml_path.read_text(encoding="utf-8")
    if "MKP" in raw_yaml or "P5MKP" in raw_yaml:
        raise AssertionError(f"{yaml_path.name} still contains MKP text")

    before_train_cfg = (ROOT / "train_config.yaml").read_bytes()
    yolo = YOLO(str(yaml_path))
    patch_wiou_v3(yolo)
    yolo.model.to(device)
    yolo.model.eval()

    criterion = yolo.model.init_criterion()
    criterion_name = criterion.__class__.__name__
    bbox_loss_name = criterion.bbox_loss.__class__.__name__
    if "WIoU" not in criterion_name or "WIoU" not in bbox_loss_name:
        raise AssertionError(f"{yaml_path.name}: WIoU criterion was not installed")
    if getattr(criterion.bbox_loss, "dfl_loss", None) is None:
        raise AssertionError(f"{yaml_path.name}: DFL loss is missing")

    checks = {
        "model": model_key,
        "yaml": str(yaml_path),
        "dysample_layers": [],
        "concat_layers": [],
        "csfmlite_layers": [],
        "wff_layers": [],
        "detect_sources": None,
        "detect_output_shapes": None,
        "criterion": criterion_name,
        "bbox_loss": bbox_loss_name,
    }

    handles = []

    def dys_hook(name):
        def hook(module, inputs, output):
            x = inputs[0]
            if output.shape[1] != x.shape[1]:
                raise AssertionError(f"{name}: DySample changed channels {x.shape[1]} -> {output.shape[1]}")
            if output.shape[-2] != x.shape[-2] * 2 or output.shape[-1] != x.shape[-1] * 2:
                raise AssertionError(f"{name}: DySample shape {tuple(x.shape)} -> {tuple(output.shape)} is not 2x")
            checks["dysample_layers"].append((name, tuple(x.shape), tuple(output.shape)))
        return hook

    def concat_hook(name):
        def hook(module, inputs, output):
            feats = inputs[0]
            shapes = [tuple(t.shape[-2:]) for t in feats]
            if len(set(shapes)) != 1:
                raise AssertionError(f"{name}: Concat spatial mismatch {shapes}")
            checks["concat_layers"].append((name, shapes, tuple(output.shape)))
        return hook

    def csfm_hook(name):
        def hook(module, inputs, output):
            feats = inputs[0]
            if not isinstance(feats, (list, tuple)) or len(feats) != 3:
                raise AssertionError(f"{name}: CSFMLite expects 3 input features")
            checks["csfmlite_layers"].append((name, [tuple(t.shape) for t in feats], tuple(output.shape)))
        return hook

    def wff_hook(name):
        def hook(module, inputs, output):
            feats = inputs[0]
            shapes = [tuple(t.shape[-2:]) for t in feats]
            checks["wff_layers"].append((name, shapes, tuple(output.shape), module.weights.detach().cpu().tolist()))
        return hook

    detect_module = None
    for i, m in enumerate(yolo.model.model):
        name = f"{i}:{module_name(m)}"
        if isinstance(m, DySampleYOLO):
            handles.append(m.register_forward_hook(dys_hook(name)))
        elif isinstance(m, Concat):
            handles.append(m.register_forward_hook(concat_hook(name)))
        elif isinstance(m, CSFMLite):
            handles.append(m.register_forward_hook(csfm_hook(name)))
        elif isinstance(m, WeightedFeatureFusion):
            handles.append(m.register_forward_hook(wff_hook(name)))
        elif isinstance(m, Detect):
            detect_module = m
            checks["detect_sources"] = list(m.f) if hasattr(m, "f") else None

    if detect_module is None:
        raise AssertionError(f"{yaml_path.name}: Detect module not found")

    with torch.no_grad():
        x = torch.randn(1, 3, imgsz, imgsz, device=device)
        _ = yolo.model(x)

    for h in handles:
        h.remove()

    if len(checks["dysample_layers"]) == 0 and "dys" in model_key:
        raise AssertionError(f"{yaml_path.name}: no DySampleYOLO layer was executed")
    if checks["detect_sources"] is None or len(checks["detect_sources"]) != 4:
        raise AssertionError(f"{yaml_path.name}: Detect does not consume 4 feature scales: {checks['detect_sources']}")

    after_train_cfg = (ROOT / "train_config.yaml").read_bytes()
    if before_train_cfg != after_train_cfg:
        raise AssertionError("train_config.yaml changed during model check")

    print(f"[OK] {model_key}: DySample={len(checks['dysample_layers'])}, Concat={len(checks['concat_layers'])}, WFF={len(checks['wff_layers'])}, Detect={checks['detect_sources']}")
    return checks


def main() -> None:
    args = parse_args()
    all_checks = []
    for key in args.models:
        if key not in MODEL_MAP:
            raise KeyError(f"Unknown model key: {key}. Available: {', '.join(MODEL_MAP)}")
        all_checks.append(check_one(key, args.imgsz, args.device))
    print("All requested week-17 model checks passed.")
    return all_checks


if __name__ == "__main__":
    main()
