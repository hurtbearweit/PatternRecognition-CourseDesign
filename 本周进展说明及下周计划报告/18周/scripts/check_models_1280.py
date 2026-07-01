"""Check all week18 model YAML files before training."""

from __future__ import annotations

import json
from pathlib import Path

import torch
from ultralytics import YOLO


ROOT = Path(__file__).resolve().parents[1]
MODELS = {
    "yolo": ROOT / "configs" / "yolov8s.yaml",
    "if_yolo": ROOT / "configs" / "if_yolov8s.yaml",
    "csfmlite": ROOT / "configs" / "if_yolov8s_wiou_csfmlite.yaml",
    "final_wff": ROOT / "configs" / "if_yolov8s_wiou_csfmlite_wff_p3p2.yaml",
}


def main() -> None:
    rows = []
    for name, path in MODELS.items():
        yolo = YOLO(str(path))
        yolo.info(imgsz=1280)
        model = yolo.model.eval()
        with torch.no_grad():
            out = model(torch.randn(1, 3, 1280, 1280))
        tensors = out if isinstance(out, (list, tuple)) else [out]
        shapes = [list(t.shape) for t in tensors if torch.is_tensor(t)]
        module_names = {m.__class__.__name__ for m in model.modules()}
        rows.append(
            {
                "name": name,
                "yaml": str(path.relative_to(ROOT)),
                "params": sum(p.numel() for p in model.parameters()),
                "output_shapes": shapes,
                "contains_wff": "WeightedFeatureFusion" in module_names,
                "contains_mkp": any("MKP" in n for n in module_names),
                "contains_dysample": any("DySample" in n for n in module_names),
                "contains_ldr": any("LocalDetailRefine" in n or n == "LDR" for n in module_names),
            }
        )
    out_path = ROOT / "results" / "model_check_1280.json"
    out_path.parent.mkdir(exist_ok=True)
    out_path.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Saved {out_path}")


if __name__ == "__main__":
    main()

