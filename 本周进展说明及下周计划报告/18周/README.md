# 第18周 1280 输入尺寸逐个训练说明

本包用于最后一组结题对比实验：统一把 `imgsz` 改为 `1280`，依次训练并比较 4 个模型。

本次不使用并行训练，不使用 DDP。所有模型按顺序逐个训练，便于观察日志、显存占用和报错。

## 对比模型

| 模型简称 | 配置文件 | 说明 |
|---|---|---|
| `yolo` | `configs/yolov8s.yaml` | 基础 YOLOv8s |
| `if_yolo` | `configs/if_yolov8s.yaml` | 基础 IF-YOLO |
| `csfmlite` | `configs/if_yolov8s_wiou_csfmlite.yaml` | IF-YOLO + WIoU v3 + CSFM-Lite |
| `final_wff` | `configs/if_yolov8s_wiou_csfmlite_wff_p3p2.yaml` | IF-YOLO + WIoU v3 + CSFM-Lite + WFF(P3->P2) |

## 目录结构

```text
18周/
├── configs/
│   ├── train_config_1280.yaml
│   ├── visdrone.yaml
│   ├── yolov8s.yaml
│   ├── if_yolov8s.yaml
│   ├── if_yolov8s_wiou_csfmlite.yaml
│   └── if_yolov8s_wiou_csfmlite_wff_p3p2.yaml
├── modules/
├── scripts/
├── sample_images/
├── manifests/sample_images.txt
├── results/
└── logs/
```

## 服务器准备

进入项目根目录后，先确认当前 Python 环境已经安装 Ultralytics，并且之前项目中的 WIoU v3 实现可用。

只需要根据服务器实际数据位置修改：

```text
18周/configs/visdrone.yaml
```

默认配置：

```yaml
path: ../datasets/VisDroneYOLO
train: images/train
val: images/val
test: images/test
```

如果服务器数据集在 `/mnt/data/VisDroneYOLO`，就改成：

```yaml
path: /mnt/data/VisDroneYOLO
```

不要修改 `train_config_1280.yaml` 里的统一训练参数，尤其是：

```yaml
imgsz: 1280
batch: 4
optimizer: AdamW
lr0: 0.003
```

如果 1280 输入导致显存不足，可以把 `batch` 改小，但必须在报告中说明。

## 1. 安装自定义模块

```bash
python 18周/scripts/install_week18_modules.py
```

该脚本会注册：

- `IPFA`
- `CSFM`
- `CSFMLite`
- `WeightedFeatureFusion`

不会注册 MKP、DySample、LDR。

如果之前旧脚本已经把 Ultralytics patch 到一半并报错，可以先恢复备份再重新安装：

```bash
cp /home/lch/.conda/envs/week18/lib/python3.10/site-packages/ultralytics/nn/tasks.py.bak_week18 /home/lch/.conda/envs/week18/lib/python3.10/site-packages/ultralytics/nn/tasks.py
cp /home/lch/.conda/envs/week18/lib/python3.10/site-packages/ultralytics/nn/modules/__init__.py.bak_week18 /home/lch/.conda/envs/week18/lib/python3.10/site-packages/ultralytics/nn/modules/__init__.py
python 18周/scripts/install_week18_modules.py
```

## 2. 训练前检查

```bash
python 18周/scripts/check_models_1280.py
```

输出文件：

```text
18周/results/model_check_1280.json
```

如果 CPU 上检查很慢，可以只确认安装脚本通过，然后直接训练。

## 3. 逐个训练命令

下面 4 条命令按顺序执行。建议一个跑完并确认有 `best.pt` 后，再跑下一个。

### 3.1 基础 YOLOv8s

```bash
python 18周/scripts/train_1280_experiment.py \
  --model yolo \
  --name week18_yolov8s_1280 \
  --device 0 \
  --seed 0 \
  --project 18周/runs/detect
```

### 3.2 基础 IF-YOLO

```bash
python 18周/scripts/train_1280_experiment.py \
  --model if_yolo \
  --name week18_if_yolo_1280 \
  --device 0 \
  --seed 0 \
  --project 18周/runs/detect
```

### 3.3 IF-YOLO + WIoU v3 + CSFM-Lite

```bash
python 18周/scripts/train_1280_experiment.py \
  --model csfmlite \
  --name week18_if_wiou_csfmlite_1280 \
  --device 0 \
  --seed 0 \
  --project 18周/runs/detect
```

### 3.4 IF-YOLO + WIoU v3 + CSFM-Lite + WFF(P3->P2)

```bash
python 18周/scripts/train_1280_experiment.py \
  --model final_wff \
  --name week18_if_wiou_csfmlite_wff_1280 \
  --device 0 \
  --seed 0 \
  --project 18周/runs/detect
```

## 4. 每个模型训练后检查

每个模型训练完成后，检查对应目录中是否存在：

```text
18周/runs/detect/实验名称/weights/best.pt
18周/runs/detect/实验名称/results.csv
18周/runs/detect/实验名称/week18_metrics_summary.json
```

例如基础 YOLOv8s：

```bash
ls 18周/runs/detect/week18_yolov8s_1280/weights/best.pt
ls 18周/runs/detect/week18_yolov8s_1280/results.csv
```

## 5. 汇总四个训练结果

四个模型全部训练完成后执行：

```bash
python 18周/scripts/summarize_1280_results.py --project 18周/runs/detect
```

输出：

```text
18周/results/week18_1280_summary.csv
18周/results/week18_1280_summary.md
```

重点比较：

- Precision
- Recall
- mAP50
- mAP50-95
- best epoch

## 6. 固定 15 张图片预测

训练完成后，使用同一批固定图片比较四个模型的检测效果：

```bash
python 18周/scripts/predict_15_images.py \
  --weights yolo=runs/detect/week18_yolov8s_1280/weights/best.pt \
  --weights if_yolo=runs/detect/week18_if_yolo_1280/weights/best.pt \
  --weights csfmlite=runs/detect/week18_if_wiou_csfmlite_1280/weights/best.pt \
  --weights final_wff=runs/detect/week18_if_wiou_csfmlite_wff_1280/weights/best.pt \
  --device 0
```

输出目录：

```text
18周/results/predictions/
```

固定图片清单：

```text
18周/manifests/sample_images.txt
```

## 注意事项

- 本包已不提供并行训练入口，四个模型请按上面的命令逐个训练。
- 本包不包含 `.pt` 权重。
- WIoU v3 是已有项目能力，本包不重新实现 WIoU。
- 如果安装脚本报 WIoU 相关错误，先同步之前项目中的 WIoU v3 修改。
- 如果训练目录已存在，脚本会拒绝覆盖；需要保留旧结果时请换一个 `--name`。
