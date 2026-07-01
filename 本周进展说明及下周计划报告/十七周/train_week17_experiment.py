"""Unified week-17 experiment trainer.

Only --model, --name, and --device are accepted. All training hyperparameters
are read from train_config.yaml.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import statistics
import time
import types


ROOT = Path(__file__).resolve().parent
TRAIN_CFG = ROOT / "train_config.yaml"
PROJECT = ROOT / "runs" / "detect"

MODEL_MAP = {
    "dys_p4p3": ROOT / "if_yolov8s_wiou_csfmlite_dys_p4p3.yaml",
    "dys_p3p2": ROOT / "if_yolov8s_wiou_csfmlite_dys_p3p2.yaml",
    "dys_p4p3_p3p2": ROOT / "if_yolov8s_wiou_csfmlite_dys_p4p3_p3p2.yaml",
    "dys_best_ldr": ROOT / "if_yolov8s_wiou_csfmlite_dys_best_ldr.yaml",
    "dys_best_wff": ROOT / "if_yolov8s_wiou_csfmlite_dys_best_wff.yaml",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True, help="Model key or YAML path.")
    parser.add_argument("--name", required=True, help="Run name.")
    parser.add_argument("--device", default=None, help="Visible CUDA device id, e.g. 0 or 1.")
    parser.add_argument("--latency-runs", type=int, default=100, help="Batch=1 latency repeats after training.")
    parser.add_argument("--latency-warmup", type=int, default=20, help="Batch=1 latency warmup repeats.")
    return parser.parse_args()


def resolve_model(model_arg: str) -> Path:
    path = MODEL_MAP.get(model_arg, Path(model_arg))
    if not path.is_absolute():
        path = ROOT / path
    if not path.exists():
        raise FileNotFoundError(f"Model file not found: {path}")
    return path


def patch_wiou_v3(model) -> None:
    import torch
    from ultralytics.utils.loss import BboxLoss, v8DetectionLoss
    from ultralytics.utils.metrics import bbox_iou
    from ultralytics.utils.tal import bbox2dist

    class WIoUv3BboxLoss(BboxLoss):
        def __init__(self, reg_max: int = 16, momentum: float = 0.01):
            super().__init__(reg_max)
            self.register_buffer("iou_mean", torch.tensor(1.0))
            self.momentum = momentum

        def forward(
            self,
            pred_dist,
            pred_bboxes,
            anchor_points,
            target_bboxes,
            target_scores,
            target_scores_sum,
            fg_mask,
            imgsz,
            stride,
        ):
            weight = target_scores.sum(-1)[fg_mask].unsqueeze(-1)
            pred = pred_bboxes[fg_mask]
            target = target_bboxes[fg_mask]
            iou = bbox_iou(pred, target, xywh=False, CIoU=False).clamp(0, 1)

            with torch.no_grad():
                batch_mean = (1.0 - iou).detach().mean().clamp(min=1e-6)
                self.iou_mean.mul_(1 - self.momentum).add_(batch_mean * self.momentum)

            px = (pred[:, 0:1] + pred[:, 2:3]) * 0.5
            py = (pred[:, 1:2] + pred[:, 3:4]) * 0.5
            tx = (target[:, 0:1] + target[:, 2:3]) * 0.5
            ty = (target[:, 1:2] + target[:, 3:4]) * 0.5
            cw = torch.max(pred[:, 2:3], target[:, 2:3]) - torch.min(pred[:, 0:1], target[:, 0:1])
            ch = torch.max(pred[:, 3:4], target[:, 3:4]) - torch.min(pred[:, 1:2], target[:, 1:2])
            distance = ((px - tx).pow(2) + (py - ty).pow(2)) / (cw.pow(2) + ch.pow(2) + 1e-7)
            wiou = torch.exp(distance.detach()) * (1.0 - iou)

            beta = ((1.0 - iou).detach() / self.iou_mean.clamp(min=1e-6)).clamp(min=1e-6)
            alpha, delta = 1.9, 3.0
            focusing = (beta / (delta * (alpha ** (beta - delta)))).clamp(0.25, 4.0)
            loss_iou = (wiou * focusing * weight).sum() / target_scores_sum

            if self.dfl_loss:
                target_ltrb = bbox2dist(anchor_points, target_bboxes, self.dfl_loss.reg_max - 1)
                loss_dfl = self.dfl_loss(pred_dist[fg_mask].view(-1, self.dfl_loss.reg_max), target_ltrb[fg_mask])
                loss_dfl = (loss_dfl * weight).sum() / target_scores_sum
            else:
                loss_dfl = torch.zeros((), device=pred_dist.device)
            return loss_iou, loss_dfl

    class WIoUv3DetectionLoss(v8DetectionLoss):
        def __init__(self, model, tal_topk: int = 10, tal_topk2: int = 1):
            super().__init__(model, tal_topk=tal_topk, tal_topk2=tal_topk2)
            self.bbox_loss = WIoUv3BboxLoss(self.reg_max).to(self.device)

    model.model.init_criterion = types.MethodType(lambda self: WIoUv3DetectionLoss(self), model.model)
    print("Using WIoU v3 + DFL for bbox regression.")


def benchmark_latency(model, runs: int, warmup: int) -> dict[str, float]:
    import torch

    device = next(model.model.parameters()).device
    model.model.eval()
    x = torch.randn(1, 3, 960, 960, device=device)
    with torch.no_grad():
        for _ in range(warmup):
            _ = model.model(x)
        if device.type == "cuda":
            torch.cuda.synchronize()
        times = []
        for _ in range(runs):
            start = time.perf_counter()
            _ = model.model(x)
            if device.type == "cuda":
                torch.cuda.synchronize()
            times.append((time.perf_counter() - start) * 1000.0)
    latency_ms = statistics.mean(times)
    return {"latency_ms_batch1_imgsz960": latency_ms, "fps_batch1_imgsz960": 1000.0 / latency_ms}


def class_ap_summary(model, metrics) -> dict[str, float]:
    maps = getattr(getattr(metrics, "box", None), "maps", None)
    if maps is None:
        return {}
    names = getattr(model.model, "names", None) or getattr(model, "names", {})
    summary = {}
    for i, ap in enumerate(maps):
        name = names.get(i, str(i)) if isinstance(names, dict) else str(i)
        summary[name] = float(ap)
    return summary


def main() -> None:
    args = parse_args()
    if args.device is not None:
        os.environ["CUDA_VISIBLE_DEVICES"] = str(args.device)

    from ultralytics import YOLO

    model_path = resolve_model(args.model)
    model = YOLO(str(model_path))
    if (ROOT / "yolov8s.pt").exists():
        model.load(str(ROOT / "yolov8s.pt"))

    patch_wiou_v3(model)
    model.info(detailed=False)
    train_results = model.train(cfg=str(TRAIN_CFG), project=str(PROJECT), name=args.name, exist_ok=False)
    metrics = model.val()
    latency = benchmark_latency(model, runs=args.latency_runs, warmup=args.latency_warmup)

    save_dir = Path(getattr(train_results, "save_dir", PROJECT / args.name))
    best_pt = save_dir / "weights" / "best.pt"
    summary = {
        "model": str(model_path),
        "name": args.name,
        "metrics": getattr(metrics, "results_dict", {}),
        "class_ap50_95": class_ap_summary(model, metrics),
        "ap_small_note": "Ultralytics detect val does not expose AP_small unless COCO-json eval is enabled; use save_json=True with COCO-format labels if needed.",
        "model_size_bytes": best_pt.stat().st_size if best_pt.exists() else None,
        **latency,
    }
    (save_dir / "week17_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print("Week17 summary:", json.dumps(summary, indent=2, ensure_ascii=False))
    return train_results, metrics


if __name__ == "__main__":
    main()
