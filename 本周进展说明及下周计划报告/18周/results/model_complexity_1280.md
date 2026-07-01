# Model Complexity At 1280

| model | Params | GFLOPs @ 1280 | notes |
|---|---:|---:|---|
| YOLOv8s baseline | 11,139,470 | 114.7 | original YOLOv8s structure |
| Basic IF-YOLO | 39,437,729 | 287.2 | IPFA + original CSFM structure |
| IF-YOLO + WIoU v3 + CSFM-Lite | 11,290,506 | 188.3 | current main lightweight IF-YOLO variant |
| IF-YOLO + WIoU v3 + CSFM-Lite + WFF(P3->P2) | 11,294,604 | 189.1 | final candidate |

These values were printed by `model.info(imgsz=1280)` during `check_models_1280.py`.

