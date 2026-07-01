"""Install week17 custom modules into the active Ultralytics package.

Example:
    python week17/scripts/install_week17_modules.py
"""

from __future__ import annotations

import logging
import shutil
import sys
from pathlib import Path


logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
ROOT = Path(__file__).resolve().parents[1]
MODULES_DIR = ROOT / "modules"
MARKER = "# WEEK17_WFF_REGISTERED"


def backup_once(path: Path) -> None:
    backup = path.with_suffix(path.suffix + ".bak_week17_wff")
    if not backup.exists():
        shutil.copy2(path, backup)
        logging.info("Backed up %s -> %s", path, backup)


def insert_after(text: str, needle: str, insertion: str) -> str:
    if insertion.strip() in text:
        return text
    if needle not in text:
        raise RuntimeError(f"Could not find insertion point: {needle!r}")
    return text.replace(needle, needle + insertion, 1)


def install_modules(ultralytics_root: Path) -> None:
    target = ultralytics_root / "nn" / "modules"
    shutil.copy2(MODULES_DIR / "weighted_fusion.py", target / "weighted_fusion.py")
    shutil.copy2(MODULES_DIR / "week17_existing_modules.py", target / "week17_existing_modules.py")

    init_path = target / "__init__.py"
    backup_once(init_path)
    init_text = init_path.read_text(encoding="utf-8")
    additions = (
        "\nfrom .weighted_fusion import WeightedFeatureFusion\n"
        "from .week17_existing_modules import IPFA, CSFMLite\n"
    )
    if "from .weighted_fusion import WeightedFeatureFusion" not in init_text:
        init_text += additions
    init_path.write_text(init_text, encoding="utf-8")


def patch_tasks(ultralytics_root: Path) -> None:
    tasks_path = ultralytics_root / "nn" / "tasks.py"
    backup_once(tasks_path)
    text = tasks_path.read_text(encoding="utf-8")

    import_line = "from ultralytics.nn.modules.weighted_fusion import WeightedFeatureFusion\n"
    existing_import = "from ultralytics.nn.modules.week17_existing_modules import IPFA, CSFMLite\n"
    if import_line not in text:
        text = insert_after(text, "import torch\n", import_line)
    if existing_import not in text:
        text = insert_after(text, "import torch\n", existing_import)

    for name in ("IPFA", "CSFMLite", "WeightedFeatureFusion"):
        token = f"            {name},\n"
        if token not in text and "base_modules = frozenset(" in text:
            text = text.replace("        base_modules = frozenset(\n            {\n", "        base_modules = frozenset(\n            {\n" + token, 1)

    if "elif m is IPFA:" not in text:
        branch = (
            "        elif m is IPFA:\n"
            "            c1, c2 = ch[f], args[0]\n"
            "            args = [c1, c2, *args[1:]]\n"
        )
        text = text.replace("        elif m is Concat:\n", branch + "        elif m is Concat:\n", 1)

    if "elif m is WeightedFeatureFusion:" not in text:
        branch = (
            "        elif m is WeightedFeatureFusion:\n"
            "            input_channels = [ch[x] for x in f]\n"
            "            c2 = args[0] if args else input_channels[0]\n"
            "            num_inputs = args[1] if len(args) > 1 else len(input_channels)\n"
            "            args = [input_channels, c2, num_inputs, *args[2:]]\n"
        )
        text = text.replace("        elif m is Concat:\n", branch + "        elif m is Concat:\n", 1)

    if "elif m is CSFMLite:" not in text:
        branch = (
            "        elif m is CSFMLite:\n"
            "            input_channels = [ch[x] for x in f]\n"
            "            c2 = input_channels[1]\n"
            "            args = [input_channels]\n"
        )
        text = text.replace("        elif m is WeightedFeatureFusion:\n", branch + "        elif m is WeightedFeatureFusion:\n", 1)

    if MARKER not in text:
        text += f"\n{MARKER}\n"
    tasks_path.write_text(text, encoding="utf-8")


def main() -> None:
    import ultralytics
    from ultralytics import YOLO

    ultralytics_root = Path(ultralytics.__file__).resolve().parent
    logging.info("Ultralytics root: %s", ultralytics_root)
    install_modules(ultralytics_root)
    patch_tasks(ultralytics_root)

    model_yaml = ROOT / "configs" / "if_yolov8s_wiou_csfmlite_wff_p3p2.yaml"
    YOLO(str(model_yaml))
    logging.info("Installed week17 modules and loaded %s successfully", model_yaml.name)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        logging.exception("Install failed: %s", exc)
        sys.exit(1)
