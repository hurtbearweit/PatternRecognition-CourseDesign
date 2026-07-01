# Week18 1280 Experiment Plan

## Goal
Train and compare four models at `imgsz=1280`, then run all trained models on the same fixed 15 VisDrone test-challenge images.

## Models
1. YOLOv8s baseline
2. Basic IF-YOLO
3. IF-YOLO + WIoU v3 + CSFM-Lite
4. IF-YOLO + WIoU v3 + CSFM-Lite + WFF(P3->P2)

## Execution Order
1. Edit `configs/visdrone.yaml` on the server so `path` points to the YOLO-format VisDrone dataset.
2. Install custom modules with `scripts/install_week18_modules.py`.
3. Run model checks with `scripts/check_models_1280.py`.
4. Train four models one by one with `scripts/train_1280_experiment.py`.
5. Summarize metrics with `scripts/summarize_1280_results.py`.
6. Run fixed-image prediction with `scripts/predict_15_images.py`.

## Constraints
- Keep `imgsz=1280`.
- Do not add MKP, DySample, LDR, or a fifth detection head.
- Do not change batch, optimizer, learning rate, or augmentation unless the final report explicitly records the change.
