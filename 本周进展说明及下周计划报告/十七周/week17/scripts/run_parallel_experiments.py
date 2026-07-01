"""Launch the six week17 A/B seed experiments on up to five GPUs.

Example:
    python week17/scripts/run_parallel_experiments.py --project week17/runs/detect
"""

from __future__ import annotations

import argparse
import csv
import logging
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = ROOT / "logs"
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


@dataclass
class Job:
    model: str
    seed: int
    name: str
    gpu: int | None = None


FIRST_WAVE = [
    Job("A", 0, "week17_A_if_wiou_csfmlite_seed0", 0),
    Job("A", 1, "week17_A_if_wiou_csfmlite_seed1", 1),
    Job("A", 2, "week17_A_if_wiou_csfmlite_seed2", 2),
    Job("B", 0, "week17_B_if_wiou_csfmlite_wff_seed0", 3),
    Job("B", 1, "week17_B_if_wiou_csfmlite_wff_seed1", 4),
]
QUEUED = [Job("B", 2, "week17_B_if_wiou_csfmlite_wff_seed2")]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", default=str(ROOT / "runs" / "detect"))
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--rerun-failed", action="store_true")
    return parser.parse_args()


def is_complete(project: Path, name: str) -> bool:
    run_dir = project / name
    return (run_dir / "weights" / "best.pt").exists() and (run_dir / "results.csv").exists()


def command(args: argparse.Namespace, job: Job, gpu: int) -> list[str]:
    return [
        args.python,
        str(ROOT / "scripts" / "train_experiment.py"),
        "--model",
        job.model,
        "--name",
        job.name,
        "--device",
        "0",
        "--seed",
        str(job.seed),
        "--project",
        str(Path(args.project).resolve()),
    ]


def launch(args: argparse.Namespace, job: Job, gpu: int) -> tuple[subprocess.Popen, dict]:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    cmd = command(args, job, gpu)
    env = os.environ.copy()
    env["CUDA_VISIBLE_DEVICES"] = str(gpu)
    env.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
    stdout = (LOG_DIR / f"{job.name}.stdout.log").open("w", encoding="utf-8")
    stderr = (LOG_DIR / f"{job.name}.stderr.log").open("w", encoding="utf-8")
    proc = subprocess.Popen(cmd, cwd=str(ROOT.parent), env=env, stdout=stdout, stderr=stderr)
    meta = {"name": job.name, "model": job.model, "seed": job.seed, "gpu": gpu, "pid": proc.pid, "start": time.time()}
    logging.info("Launched %s on GPU %s pid=%s", job.name, gpu, proc.pid)
    return proc, meta


def main() -> None:
    args = parse_args()
    project = Path(args.project).resolve()
    jobs = FIRST_WAVE + QUEUED
    if args.dry_run:
        for job in FIRST_WAVE:
            print("CUDA_VISIBLE_DEVICES=%s %s" % (job.gpu, " ".join(command(args, job, job.gpu or 0))))
        print("After any GPU is free:")
        print("CUDA_VISIBLE_DEVICES=<free_gpu> %s" % " ".join(command(args, QUEUED[0], 0)))
        return

    active: list[tuple[subprocess.Popen, dict]] = []
    completed: list[dict] = []
    for job in FIRST_WAVE:
        if is_complete(project, job.name) and not args.rerun_failed:
            completed.append({"name": job.name, "status": "reused", "returncode": 0})
            continue
        active.append(launch(args, job, int(job.gpu)))

    queued = list(QUEUED)
    while active:
        for proc, meta in list(active):
            code = proc.poll()
            if code is None:
                continue
            active.remove((proc, meta))
            meta["end"] = time.time()
            meta["returncode"] = code
            meta["complete"] = is_complete(project, meta["name"])
            completed.append(meta)
            logging.info("Finished %s returncode=%s complete=%s", meta["name"], code, meta["complete"])
            if queued:
                next_job = queued.pop(0)
                active.append(launch(args, next_job, int(meta["gpu"])))
        time.sleep(15)

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with (LOG_DIR / "parallel_experiments_manifest.csv").open("w", encoding="utf-8", newline="") as f:
        fields = sorted({k for row in completed for k in row})
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(completed)


if __name__ == "__main__":
    main()

