import csv
from pathlib import Path


base = Path(r"D:\大三下\模式识别课设\Model\runs\detect")
files = {
    "YOLOv8s": base / "week15_yolov8s_baseline" / "results.csv",
    "LUD-YOLO": base / "week15_lud_yolo" / "results.csv",
    "HS-FPN": Path(
        r"D:\大三下\模式识别课设\本周进展说明及下周计划报告\十五周\train-2\results.csv"
    ),
    "FBRT-YOLO": Path(
        r"D:\大三下\模式识别课设\本周进展说明及下周计划报告\十五周\fbrt_yolov8s_visdrone_pretrained_week18-2\results.csv"
    ),
}

for name, path in files.items():
    with path.open(encoding="utf-8") as file:
        rows = list(csv.DictReader(file))
    value = lambda row, key: float(row[key])
    best = max(
        rows,
        key=lambda row: 0.1 * value(row, "metrics/mAP50(B)")
        + 0.9 * value(row, "metrics/mAP50-95(B)"),
    )
    print(
        name,
        "epochs=", len(rows),
        "hours=", round(value(rows[-1], "time") / 3600, 3),
        "best_epoch=", best["epoch"],
        "P=", best["metrics/precision(B)"],
        "R=", best["metrics/recall(B)"],
        "mAP50=", best["metrics/mAP50(B)"],
        "mAP50-95=", best["metrics/mAP50-95(B)"],
    )
