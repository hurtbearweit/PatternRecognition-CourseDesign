"""Install and register ESSamp in the active Ultralytics environment."""

from pathlib import Path
import shutil
import subprocess
import sys

import ultralytics


ROOT = Path(__file__).resolve().parent
ULTRALYTICS_ROOT = Path(ultralytics.__file__).resolve().parent
MODULES_DIR = ULTRALYTICS_ROOT / "nn" / "modules"
MODULE_INIT = MODULES_DIR / "__init__.py"
TASKS_FILE = ULTRALYTICS_ROOT / "nn" / "tasks.py"
SOURCE_MODULE = ROOT / "prnet_module.py"
TARGET_MODULE = MODULES_DIR / "prnet.py"
MARKER = "# PRNET_ESSAMP_REGISTERED"


def backup(path: Path) -> None:
    target = path.with_suffix(path.suffix + ".bak_prnet")
    if not target.exists():
        shutil.copy2(path, target)


def patch_module_init() -> None:
    backup(MODULE_INIT)
    text = MODULE_INIT.read_text(encoding="utf-8")
    import_line = f"from .prnet import ESSamp  {MARKER}\n"
    if import_line not in text:
        text = import_line + text
    MODULE_INIT.write_text(text, encoding="utf-8")


def patch_tasks() -> None:
    backup(TASKS_FILE)
    text = TASKS_FILE.read_text(encoding="utf-8")

    import_line = f"from ultralytics.nn.modules.prnet import ESSamp  {MARKER}\n"
    if import_line not in text:
        anchor = "import torch.nn as nn\n"
        if anchor not in text:
            raise RuntimeError("Cannot find torch import anchor in ultralytics/nn/tasks.py")
        text = text.replace(anchor, anchor + import_line, 1)

    registration = f"            ESSamp,  {MARKER}\n"
    if registration not in text:
        anchor = "    base_modules = frozenset(\n        {\n"
        if anchor not in text:
            raise RuntimeError("Cannot find base_modules in ultralytics/nn/tasks.py")
        text = text.replace(anchor, anchor + registration, 1)

    TASKS_FILE.write_text(text, encoding="utf-8")


def verify() -> None:
    code = (
        "from ultralytics import YOLO; "
        f"m=YOLO(r'{ROOT / 'prnet_yolov8s.yaml'}'); "
        "s=m.model.stride.tolist(); "
        "assert s == [4.0, 8.0, 16.0], s; "
        "print('Detection strides:', s); "
        "print('PRNet installation verified successfully.')"
    )
    subprocess.run([sys.executable, "-c", code], check=True)
    print(f"Ultralytics: {ultralytics.__version__}")
    print(f"Installed module: {TARGET_MODULE}")


def main() -> None:
    if ultralytics.__version__ != "8.4.53":
        print(f"Warning: tested with Ultralytics 8.4.53, current version is {ultralytics.__version__}.")
    shutil.copy2(SOURCE_MODULE, TARGET_MODULE)
    patch_module_init()
    patch_tasks()
    verify()


if __name__ == "__main__":
    main()
