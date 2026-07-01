"""Install week-17 custom modules into the active Ultralytics environment."""

from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import sys

import ultralytics


ROOT = Path(__file__).resolve().parent
ULTRA = Path(ultralytics.__file__).resolve().parent
MODULES = ULTRA / "nn" / "modules"
TASKS = ULTRA / "nn" / "tasks.py"
INIT = MODULES / "__init__.py"
TARGET = MODULES / "week17_modules.py"
MARK = "# WEEK17_IF_REGISTERED"


def backup(path: Path) -> None:
    backup_path = path.with_suffix(path.suffix + ".bak_week17")
    if not backup_path.exists():
        shutil.copy2(path, backup_path)


def insert_once(text: str, needle: str, insertion: str, *, before: bool = False) -> str:
    if insertion in text:
        return text
    if needle not in text:
        raise RuntimeError(f"Cannot find insertion point: {needle!r}")
    return text.replace(needle, insertion + needle if before else needle + insertion, 1)


def main() -> None:
    shutil.copy2(ROOT / "week17_modules.py", TARGET)

    backup(INIT)
    init_text = INIT.read_text(encoding="utf-8")
    init_line = (
        "from .week17_modules import CSFM, CSFMLite, DySampleYOLO, IPFA, "
        f"LocalDetailRefine, WeightedFeatureFusion  {MARK}\n"
    )
    if init_line not in init_text:
        init_text = init_line + init_text
    INIT.write_text(init_text, encoding="utf-8")

    backup(TASKS)
    task_text = TASKS.read_text(encoding="utf-8")
    import_line = (
        "from ultralytics.nn.modules.week17_modules import CSFM, CSFMLite, DySampleYOLO, IPFA, "
        f"LocalDetailRefine, WeightedFeatureFusion  {MARK}\n"
    )
    task_text = insert_once(task_text, "import torch.nn as nn\n", import_line)

    ipfa_reg = f"            IPFA,  {MARK}\n"
    if ipfa_reg not in task_text:
        task_text = insert_once(task_text, "    base_modules = frozenset(\n        {\n", ipfa_reg)

    custom_branch = (
        f"        elif m in {{CSFM, CSFMLite}}:  {MARK}\n"
        "            input_channels = [ch[x] for x in f]\n"
        "            args = [input_channels]\n"
        "            c2 = input_channels[1]\n"
        f"        elif m in {{DySampleYOLO, LocalDetailRefine}}:  {MARK}\n"
        "            c1 = ch[f]\n"
        "            args = [c1, *args]\n"
        "            c2 = c1\n"
        f"        elif m is WeightedFeatureFusion:  {MARK}\n"
        "            input_channels = [ch[x] for x in f]\n"
        "            c2 = args[0] if args else input_channels[0]\n"
        "            args = [input_channels, c2, *args[1:]]\n"
    )
    if custom_branch not in task_text:
        task_text = insert_once(task_text, "        elif m is Concat:\n", custom_branch, before=True)

    TASKS.write_text(task_text, encoding="utf-8")

    smoke = ROOT / "if_yolov8s_wiou_csfmlite_dys_p3p2.yaml"
    subprocess.run(
        [sys.executable, "-c", f"from ultralytics import YOLO; YOLO(r'{smoke}'); print('week17 module install ok')"],
        check=True,
    )


if __name__ == "__main__":
    main()
