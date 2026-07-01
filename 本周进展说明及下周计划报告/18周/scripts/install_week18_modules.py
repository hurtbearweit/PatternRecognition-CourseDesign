"""Install week18 custom modules into the active Ultralytics package.

Run from the project root on the server:
    python 18周/scripts/install_week18_modules.py
"""

from __future__ import annotations

import logging
import shutil
import subprocess
import sys
import textwrap
import importlib.util
from pathlib import Path


logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
ROOT = Path(__file__).resolve().parents[1]
MODULES_DIR = ROOT / "modules"
MARKER = "# WEEK18_1280_REGISTERED"


def backup_once(path: Path) -> None:
    backup = path.with_suffix(path.suffix + ".bak_week18")
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
    shutil.copy2(MODULES_DIR / "week18_existing_modules.py", target / "week18_existing_modules.py")

    init_path = target / "__init__.py"
    backup_once(init_path)
    text = init_path.read_text(encoding="utf-8")
    additions = (
        "\nfrom .weighted_fusion import WeightedFeatureFusion\n"
        "from .week18_existing_modules import IPFA, CSFM, CSFMLite\n"
    )
    if "from .week18_existing_modules import IPFA, CSFM, CSFMLite" not in text:
        text += additions
    init_path.write_text(text, encoding="utf-8")


def patch_tasks(ultralytics_root: Path) -> None:
    tasks_path = ultralytics_root / "nn" / "tasks.py"
    backup_once(tasks_path)
    text = tasks_path.read_text(encoding="utf-8")

    for line in (
        "from ultralytics.nn.modules.weighted_fusion import WeightedFeatureFusion\n",
        "from ultralytics.nn.modules.week18_existing_modules import IPFA, CSFM, CSFMLite\n",
    ):
        if line not in text:
            text = insert_after(text, "import torch\n", line)

    # Keep these modules out of Ultralytics' generic base_modules path. Their
    # YAML arguments need custom channel inference below.
    for name in ("IPFA", "CSFM", "CSFMLite", "WeightedFeatureFusion"):
        text = text.replace(f"            {name},\n", "")

    if "elif m is IPFA:" not in text:
        branch = (
            "        elif m is IPFA:\n"
            "            c1, c2 = ch[f], args[0]\n"
            "            args = [c1, c2, *args[1:]]\n"
        )
        text = text.replace("        elif m is Concat:\n", branch + "        elif m is Concat:\n", 1)

    if "elif m in frozenset({CSFM, CSFMLite}):" not in text and "elif m is CSFM:" not in text:
        branch = (
            "        elif m in frozenset({CSFM, CSFMLite}):\n"
            "            input_channels = [ch[x] for x in f]\n"
            "            c2 = input_channels[1]\n"
            "            args = [input_channels]\n"
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

    if MARKER not in text:
        text += f"\n{MARKER}\n"
    tasks_path.write_text(text, encoding="utf-8")


def main() -> None:
    spec = importlib.util.find_spec("ultralytics")
    if spec is None or spec.origin is None:
        raise RuntimeError("Ultralytics is not installed in the current Python environment")

    ultralytics_root = Path(spec.origin).resolve().parent
    logging.info("Ultralytics root: %s", ultralytics_root)
    install_modules(ultralytics_root)
    patch_tasks(ultralytics_root)

    # Ultralytics may already be imported in this process before tasks.py is
    # patched. Verify in a fresh Python process so parse_model sees the new
    # imports and custom channel-inference branches.
    check_code = textwrap.dedent(
        f"""
        from ultralytics import YOLO
        paths = [
            r"{ROOT / 'configs' / 'if_yolov8s.yaml'}",
            r"{ROOT / 'configs' / 'if_yolov8s_wiou_csfmlite.yaml'}",
            r"{ROOT / 'configs' / 'if_yolov8s_wiou_csfmlite_wff_p3p2.yaml'}",
        ]
        for path in paths:
            YOLO(path)
            print("Loaded", path)
        """
    )
    subprocess.run([sys.executable, "-c", check_code], check=True)
    logging.info("Installed week18 modules and verified custom YAML files in a fresh Python process")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        logging.exception("Install failed: %s", exc)
        sys.exit(1)
