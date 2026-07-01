"""Generate LDR/WFF configs after the DySample position ablation is known."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent

BACKBONE = [
    [-1, 1, "Conv", [64, 3, 2]],
    [-1, 1, "IPFA", [128]],
    [-1, 3, "C2f", [128, True]],
    [-1, 1, "IPFA", [256]],
    [-1, 6, "C2f", [256, True]],
    [-1, 1, "Conv", [512, 3, 2]],
    [-1, 6, "C2f", [512, True]],
    [-1, 1, "Conv", [1024, 3, 2]],
    [-1, 3, "C2f", [1024, True]],
    [-1, 1, "SPPF", [1024, 5]],
]

BASE_HEAD = [
    [[0, 2, 4], 1, "CSFMLite", []],
    [[2, 4, 6], 1, "CSFMLite", []],
    [[4, 6, 9], 1, "CSFMLite", []],
    [9, 1, "nn.Upsample", [None, 2, "nearest"]],
    [[-1, 12], 1, "Concat", [1]],
    [-1, 3, "C2f", [512]],
    [-1, 1, "nn.Upsample", [None, 2, "nearest"]],
    [[-1, 11], 1, "Concat", [1]],
    [-1, 3, "C2f", [256]],
    [-1, 1, "nn.Upsample", [None, 2, "nearest"]],
    [[-1, 10], 1, "Concat", [1]],
    [-1, 3, "C2f", [128]],
    [-1, 1, "IPFA", [128]],
    [[-1, 18, 11], 1, "Concat", [1]],
    [-1, 3, "C2f", [256]],
    [-1, 1, "IPFA", [256]],
    [[-1, 15, 12], 1, "Concat", [1]],
    [-1, 3, "C2f", [512]],
    [-1, 1, "Conv", [512, 3, 2]],
    [[-1, 9], 1, "Concat", [1]],
    [-1, 3, "C2f", [1024]],
    [[21, 24, 27, 30], 1, "Detect", ["nc"]],
]

DY_LAYERS = {
    "p4p3": {16},
    "p3p2": {19},
    "p4p3_p3p2": {16, 19},
}


def shift_ref(value: Any, insert_after: list[int]) -> Any:
    if isinstance(value, list):
        return [shift_ref(v, insert_after) for v in value]
    if isinstance(value, int) and value >= 0:
        return value + sum(1 for layer in insert_after if value > layer)
    return value


def fmt_scalar(value: Any) -> str:
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, str):
        return value
    return str(value)


def fmt_list(values: list[Any]) -> str:
    return "[" + ", ".join(fmt_list(v) if isinstance(v, list) else fmt_scalar(v) for v in values) + "]"


def fmt_layer(layer: list[Any]) -> str:
    f, n, module, args = layer
    return f"  - [{fmt_list(f) if isinstance(f, list) else fmt_scalar(f)}, {n}, {module}, {fmt_list(args)}]\n"


def build_head(best: str, *, ldr: bool = False, wff: bool = False) -> list[list[Any]]:
    dy_layers = DY_LAYERS[best]
    insert_after = sorted(dy_layers) if ldr else []
    out = []
    for i, layer in enumerate(BASE_HEAD):
        global_idx = 10 + i
        f, n, module, args = layer
        if global_idx in dy_layers and module == "nn.Upsample":
            module = "DySampleYOLO"
            args = []
        if wff and module == "Concat" and f == [-1, 11]:
            module, args = "WeightedFeatureFusion", [256]
        if wff and module == "Concat" and f == [-1, 10]:
            module, args = "WeightedFeatureFusion", [128]
        adjusted = [shift_ref(f, insert_after), n, module, args]
        out.append(adjusted)
        if ldr and global_idx in dy_layers:
            out.append([-1, 1, "LocalDetailRefine", []])
    return out


def write_yaml(path: Path, head: list[list[Any]], note: str) -> None:
    text = [f"# {note}\n", "loss: wiou_v3\n", "nc: 10\n", "scale: s\n", "scales:\n", "  s: [0.33, 0.50, 1024]\n", "backbone:\n"]
    text.extend(fmt_layer(layer) for layer in BACKBONE)
    text.append("head:\n")
    text.extend(fmt_layer(layer) for layer in head)
    path.write_text("".join(text), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--best", choices=sorted(DY_LAYERS), required=True)
    args = parser.parse_args()

    write_yaml(
        ROOT / "if_yolov8s_wiou_csfmlite_dys_best_ldr.yaml",
        build_head(args.best, ldr=True, wff=False),
        f"Generated LDR config from best DySample node: {args.best}",
    )
    write_yaml(
        ROOT / "if_yolov8s_wiou_csfmlite_dys_best_wff.yaml",
        build_head(args.best, ldr=False, wff=True),
        f"Generated WFF config from best DySample node: {args.best}",
    )
    print(f"Generated best LDR/WFF configs for best={args.best}")


if __name__ == "__main__":
    main()
