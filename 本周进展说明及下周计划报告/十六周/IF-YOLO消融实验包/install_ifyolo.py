"""Install IF-YOLO modules into the active Ultralytics environment."""

from pathlib import Path
import shutil
import subprocess
import sys

import ultralytics


ROOT = Path(__file__).resolve().parent
ULTRA = Path(ultralytics.__file__).resolve().parent
MODULES = ULTRA / "nn" / "modules"
MODULE_INIT = MODULES / "__init__.py"
TASKS = ULTRA / "nn" / "tasks.py"
TARGET = MODULES / "ifyolo.py"
MARKER = "# IFYOLO_ABLATION_REGISTERED"


def backup(path: Path) -> None:
    destination = path.with_suffix(path.suffix + ".bak_ifyolo")
    if not destination.exists():
        shutil.copy2(path, destination)


def insert_once(text: str, anchor: str, insertion: str) -> str:
    if insertion in text:
        return text
    if anchor not in text:
        raise RuntimeError(f"Cannot find patch anchor: {anchor!r}")
    return text.replace(anchor, anchor + insertion, 1)


def patch_files() -> None:
    shutil.copy2(ROOT / "ifyolo.py", TARGET)

    backup(MODULE_INIT)
    text = MODULE_INIT.read_text(encoding="utf-8")
    line = f"from .ifyolo import CSFM, IPFA  {MARKER}\n"
    if line not in text:
        text = line + text
    MODULE_INIT.write_text(text, encoding="utf-8")

    backup(TASKS)
    text = TASKS.read_text(encoding="utf-8")
    import_line = f"from ultralytics.nn.modules.ifyolo import CSFM, IPFA  {MARKER}\n"
    text = insert_once(text, "import torch.nn as nn\n", import_line)

    base_line = f"            IPFA,  {MARKER}\n"
    text = insert_once(text, "    base_modules = frozenset(\n        {\n", base_line)

    csfm_branch = (
        f"        elif m is CSFM:  {MARKER}\n"
        "            input_channels = [ch[x] for x in f]\n"
        "            args = [input_channels]\n"
        "            c2 = input_channels[1]\n"
    )
    if csfm_branch not in text:
        anchor = "        elif m is Concat:\n"
        if anchor not in text:
            raise RuntimeError("Cannot find Concat parser branch")
        text = text.replace(anchor, csfm_branch + anchor, 1)
    TASKS.write_text(text, encoding="utf-8")


def verify() -> None:
    code = (
        "from pathlib import Path; from ultralytics import YOLO; "
        f"r=Path(r'{ROOT}'); "
        "names=['01_yolov8s_baseline.yaml','02_yolov8s_ipfa.yaml','03_yolov8s_csfm.yaml',"
        "'04_yolov8s_fgafpn.yaml','05_if_yolov8s_full.yaml']; "
        "[(YOLO(str(r/n)).model.stride.tolist()) for n in names]; "
        "print('All five ablation models build successfully.')"
    )
    subprocess.run([sys.executable, "-c", code], check=True)


def main() -> None:
    if ultralytics.__version__ != "8.4.53":
        print(f"Warning: tested with ultralytics 8.4.53, current version is {ultralytics.__version__}")
    patch_files()
    verify()
    print(f"IF-YOLO module installed at: {TARGET}")


if __name__ == "__main__":
    main()
