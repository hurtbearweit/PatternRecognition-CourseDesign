# Week18 Findings

## Package Decisions
- `train_config_1280.yaml` keeps the previous unified training settings and changes image size to 1280.
- `visdrone.yaml` uses a relative server template path: `../datasets/VisDroneYOLO`.
- The fixed 15-image visualization set is copied from `VisDrone2019/test-challenge/images`, so it is not part of the train or validation split used for metric comparison.
- Custom module installation registers only IPFA, CSFM, CSFM-Lite, and WFF. MKP, DySample, LDR, and fifth detection head experiments are not included.

## Pending Server Results
- Four 1280 trainings are not run locally in this package.
- After server training, run `summarize_1280_results.py` to produce `results/week18_1280_summary.csv` and `.md`.

## Local Smoke Check
- `install_week18_modules.py` loaded `if_yolov8s.yaml`, `if_yolov8s_wiou_csfmlite.yaml`, and `if_yolov8s_wiou_csfmlite_wff_p3p2.yaml`.
- `check_models_1280.py` forward check passed for all four models.
- 1280 complexity:
  - YOLOv8s: 11,139,470 params, 114.7 GFLOPs.
  - Basic IF-YOLO: 39,437,729 params, 287.2 GFLOPs.
  - IF-YOLO + WIoU v3 + CSFM-Lite: 11,290,506 params, 188.3 GFLOPs.
  - Final WFF: 11,294,604 params, 189.1 GFLOPs.
