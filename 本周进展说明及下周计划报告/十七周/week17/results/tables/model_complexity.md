# Model Complexity

| model | Params | GFLOPs @ 960 | note |
|---|---:|---:|---|
| A: IF-YOLO + WIoU v3 + CSFM-Lite | 11,290,506 | 105.9 | `model.info(imgsz=960)` |
| B: IF-YOLO + WIoU v3 + CSFM-Lite + WFF(P3->P2) | 11,294,604 | 106.4 | `model.info(imgsz=960)` |

WFF adds 4,098 parameters and about 0.5 GFLOPs at 960 input size.

