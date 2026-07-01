"""Run pre-training checks for the week17 WFF model.

Example:
    python week17/scripts/check_wff_model.py --model week17/configs/if_yolov8s_wiou_csfmlite_wff_p3p2.yaml --device cuda:0
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

import torch
import yaml
from ultralytics import YOLO
from ultralytics.nn.modules.head import Detect


ROOT = Path(__file__).resolve().parents[1]
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default=str(ROOT / "configs" / "if_yolov8s_wiou_csfmlite_wff_p3p2.yaml"))
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--output", default=str(ROOT / "results" / "tables" / "wff_model_check.json"))
    return parser.parse_args()


def count_params(model: torch.nn.Module) -> int:
    return sum(p.numel() for p in model.parameters())


def main() -> None:
    args = parse_args()
    model_path = Path(args.model).resolve()
    if not model_path.exists():
        raise FileNotFoundError(model_path)

    with model_path.open("r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    assert cfg.get("loss") == "wiou_v3", "YAML must keep loss: wiou_v3"

    yolo = YOLO(str(model_path))
    yolo.info(imgsz=960)
    model = yolo.model.to(args.device).eval()

    module_names = [m.__class__.__name__ for m in model.modules()]
    forbidden = {"P5MKPLite", "MKP", "DySampleYOLO", "DySample", "LocalDetailRefine", "LDR"}
    present_forbidden = sorted(name for name in module_names if name in forbidden or "MKP" in name)
    assert not present_forbidden, f"Forbidden modules found: {present_forbidden}"
    assert "WeightedFeatureFusion" in module_names, "WeightedFeatureFusion not found"
    assert "DFL" in module_names, "DFL module not found in detection head"

    detect = next(m for m in model.modules() if isinstance(m, Detect))
    detect_inputs = len(detect.stride) if getattr(detect, "stride", None) is not None else len(detect.cv2)
    assert detect_inputs == 4, f"Detect must use 4 scales, got {detect_inputs}"

    forward_shapes = {}
    with torch.no_grad():
        for size in (640, 960):
            x = torch.randn(1, 3, size, size, device=args.device)
            out = model(x)
            tensors = out if isinstance(out, (list, tuple)) else [out]
            assert all(torch.isfinite(t).all().item() for t in tensors if torch.is_tensor(t)), f"NaN/Inf at {size}"
            forward_shapes[str(size)] = [list(t.shape) for t in tensors if torch.is_tensor(t)]

    result = {
        "model": str(model_path),
        "loss_config": cfg.get("loss"),
        "params": count_params(model),
        "detect_scales": detect_inputs,
        "contains_wff": True,
        "contains_dfl": True,
        "forbidden_modules": present_forbidden,
        "forward_shapes": forward_shapes,
        "note": "GFLOPs are printed by model.info(); Ultralytics does not expose a stable return value in all versions.",
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    logging.info("WFF model check passed. Saved %s", output)


if __name__ == "__main__":
    main()
