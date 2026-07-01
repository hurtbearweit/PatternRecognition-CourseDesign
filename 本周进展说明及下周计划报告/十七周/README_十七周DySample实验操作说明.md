# 十七周 DySample / LDR / WFF 实验操作说明

## 0. 本轮结论基准

已删除 MKP 方向，新的基准模型为：

```text
IF-YOLO + WIoU v3 + CSFM-Lite
best mAP50    = 0.51616
best mAP50-95 = 0.30003
```

所有新实验必须严格读取本目录的 `train_config.yaml`，不得修改：

```text
epochs, imgsz, batch, optimizer, lr0, lrf,
mosaic, copy_paste, mixup, degrees, scale,
cls, box, iou, amp, seed
```

## 1. 文件说明

```text
week17_modules.py
  IPFA, CSFM/CSFMLite, DySampleYOLO, LocalDetailRefine, WeightedFeatureFusion

install_week17_modules.py
  将 week17_modules.py 注册到当前 ultralytics 环境，并修改 parse_model 解析逻辑

check_week17_models.py
  正式训练前检查 YAML：随机 forward、DySample 2x、Concat 尺寸、四尺度 Detect、WIoU+DFL、无 MKP

train_week17_experiment.py
  统一训练入口，只允许 --model、--name、--device 控制实验；训练参数全部来自 train_config.yaml

generate_best_configs.py
  DySample 位置消融完成后，根据最佳 DySample 节点生成 best_ldr / best_wff 配置
```

## 2. 安装自定义模块

进入十七周目录：

```bash
cd "D:/大三下/模式识别课设/本周进展说明及下周计划报告/十七周"
python install_week17_modules.py
```

成功时会打印：

```text
week17 module install ok
```

## 3. 先做 DySample 位置消融

本阶段只替换 P4->P3、P3->P2，不替换 P5->P4，不一次替换全部上采样。

训练前先检查：

```bash
python check_week17_models.py --models dys_p4p3 dys_p3p2 dys_p4p3_p3p2 --imgsz 960 --device cuda
```

如果显存不够，检查阶段可以先用较小输入做结构 smoke test：

```bash
python check_week17_models.py --models dys_p4p3 dys_p3p2 dys_p4p3_p3p2 --imgsz 320 --device cuda
```

正式训练：

```bash
python train_week17_experiment.py --model dys_p4p3 --name week15_if_wiou_csfmlite_dys_p4p3 --device 0
python train_week17_experiment.py --model dys_p3p2 --name week15_if_wiou_csfmlite_dys_p3p2 --device 0
python train_week17_experiment.py --model dys_p4p3_p3p2 --name week15_if_wiou_csfmlite_dys_p4p3_p3p2 --device 0
```

训练脚本会在每个 run 目录下写入：

```text
week17_summary.json
```

其中包含：

```text
Precision, Recall, mAP50, mAP50-95
class_ap50_95
model_size_bytes
latency_ms_batch1_imgsz960
fps_batch1_imgsz960
```

注意：严格意义的 `AP_small` 需要 COCO-json 风格标注和 COCO eval。当前 VisDrone YOLO txt 验证流程通常不会直接给出 AP_small；如果需要 AP_small，需要先准备 COCO 格式标注并用 `save_json=True` 做 COCO 评估。

## 4. 根据最佳 DySample 结果生成 LDR / WFF 配置

比较三组 DySample 消融的 `best mAP50-95`，选择最佳节点。

如果最佳是 P4->P3：

```bash
python generate_best_configs.py --best p4p3
```

如果最佳是 P3->P2：

```bash
python generate_best_configs.py --best p3p2
```

如果最佳是同时替换 P4->P3 和 P3->P2：

```bash
python generate_best_configs.py --best p4p3_p3p2
```

该命令会覆盖生成：

```text
if_yolov8s_wiou_csfmlite_dys_best_ldr.yaml
if_yolov8s_wiou_csfmlite_dys_best_wff.yaml
```

## 5. 训练 LocalDetailRefine

LDR 只允许加在最佳 DySample 节点后，不在所有层使用。

检查：

```bash
python check_week17_models.py --models dys_best_ldr --imgsz 960 --device cuda
```

训练：

```bash
python train_week17_experiment.py --model dys_best_ldr --name week15_if_wiou_csfmlite_dys_best_ldr --device 0
```

## 6. 训练 WeightedFeatureFusion

WFF 只替换 P2、P3 路径中仍存在的普通 Concat，不替换 CSFM-Lite 内部融合。

检查：

```bash
python check_week17_models.py --models dys_best_wff --imgsz 960 --device cuda
```

训练：

```bash
python train_week17_experiment.py --model dys_best_wff --name week15_if_wiou_csfmlite_dys_best_wff --device 0
```

## 7. 建议记录表

每个实验都记录以下内容：

```text
Experiment
Params
GFLOPs
Precision
Recall
mAP50
mAP50-95
AP_small
Class AP
Model size
Latency, batch=1, imgsz=960
FPS, batch=1, imgsz=960
```

如果 `AP_small` 暂时无法输出，在表格里写：

```text
AP_small: not available under YOLO-txt validation; requires COCO-json eval
```
