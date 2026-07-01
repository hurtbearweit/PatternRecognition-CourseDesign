# IF-YOLO消融实验：最简单运行说明

这套文件已经把网络配置、IF-YOLO模块、训练参数和训练函数准备好了。每位同学只负责运行一个脚本，不需要自己修改Ultralytics源码。

## 一、本周实际只需要跑三组

原始YOLOv8s和完整IF-YOLO已经在上周使用统一参数训练完成，因此本周不需要重复训练。现有结果可以直接作为消融实验的首尾对照：

| 已有实验 | 已有结果位置 | 是否重跑 |
|---|---|---|
| 原始YOLOv8s | `week15_yolov8s_baseline` | 不需要 |
| 完整IF-YOLO | `train-5` | 不需要 |

本周三名同学分别运行下面三组：

| 本周实验 | 负责内容 | 直接运行的文件 | 输出文件夹 |
|---|---|---|---|
| 第1组 | 只加入IPFA | `train_02_ipfa.py` | `ablation_02_ipfa` |
| 第2组 | 只加入CSFM融合 | `train_03_csfm.py` | `ablation_03_csfm` |
| 第3组 | 只使用FGAFPN，不使用IPFA | `train_04_fgafpn.py` | `ablation_04_fgafpn` |

下面两个脚本只作为以后复现或检查使用，本周不要运行：

```text
train_01_baseline.py
train_05_full.py
```

## 二、完整的五组对照关系

| 实验 | 负责内容 | 直接运行的文件 | 输出文件夹 |
|---|---|---|---|
| 第1组 | 原始YOLOv8s基线 | `train_01_baseline.py` | `ablation_01_baseline` |
| 第2组 | 只加入IPFA | `train_02_ipfa.py` | `ablation_02_ipfa` |
| 第3组 | 只加入CSFM融合 | `train_03_csfm.py` | `ablation_03_csfm` |
| 第4组 | 只使用FGAFPN，不使用IPFA | `train_04_fgafpn.py` | `ablation_04_fgafpn` |
| 第5组 | 完整IF-YOLO | `train_05_full.py` | `ablation_05_if_yolo_full` |

## 三、每组网络到底改了什么

### 第1组：原始YOLOv8s

不加入任何IF-YOLO模块，使用普通Conv下采样和原始PAN-FPN，作为对照组。

配置文件：`01_yolov8s_baseline.yaml`

### 第2组：YOLOv8s + IPFA

把原始YOLOv8s中的部分步长为2的Conv替换为IPFA。IPFA先把相邻像素重新排列，再进行通道融合，目的是在下采样时尽量保留小目标信息。

配置文件：`02_yolov8s_ipfa.yaml`

### 第3组：YOLOv8s + CSFM

保留普通Conv下采样，加入三组CSFM，对浅层、中层和深层特征进行对齐与冲突抑制融合。后续使用普通的逐级特征金字塔，不加入FGAFPN的重复跨层连接。

配置文件：`03_yolov8s_csfm.yaml`

### 第4组：YOLOv8s + FGAFPN

保留普通Conv下采样，使用三组CSFM和FGAFPN的四尺度、跨层重复融合结构。该实验用于观察细粒度特征金字塔本身的作用。

配置文件：`04_yolov8s_fgafpn.yaml`

### 第5组：完整IF-YOLO

同时使用IPFA、CSFM和FGAFPN，与之前`train-5`对应的完整IF-YOLO结构一致。

配置文件：`05_if_yolov8s_full.yaml`

## 四、所有人只需要做这四步

### 第1步：复制整个文件夹

把完整的`IF-YOLO消融实验包`复制到自己的电脑或服务器。不要只复制训练脚本，YAML和模块文件必须放在同一个文件夹中。

### 第2步：修改数据集路径

打开`VisDrone_server.yaml`，只修改第一行：

```yaml
path: /home/username/datasets/VisDroneYOLO
```

Windows示例：

```yaml
path: D:/大三下/模式识别课设/Dataset/VisDroneYOLO
```

服务器示例：

```yaml
path: /root/autodl-tmp/VisDroneYOLO
```

该目录下面必须同时存在：

```text
VisDroneYOLO/
├── images/
│   ├── train/
│   ├── val/
│   └── test/
└── labels/
    ├── train/
    ├── val/
    └── test/
```

### 第3步：安装环境和IF-YOLO模块

所有人必须使用相同版本：

```bash
pip install ultralytics==8.4.53
python install_ifyolo.py
```

看到下面这句话表示安装成功：

```text
All five ablation models build successfully.
```

安装脚本会自动完成以下工作：

1. 把`ifyolo.py`复制到当前Python环境的Ultralytics中。
2. 注册IPFA和CSFM模块。
3. 修改模型解析器。
4. 自动检查五个YAML能否正常构建。

不要手工修改`site-packages`。更换Conda环境后，需要在新环境中重新运行一次`install_ifyolo.py`。

### 第4步：运行自己负责的实验

第1组：

```bash
python train_01_baseline.py
```

第2组：

```bash
python train_02_ipfa.py
```

如果第2组训练过程中出现 `NaN/Inf` 或 `EMA contains NaN/Inf`，不要继续用原脚本重跑，改用稳定版：

```bash
python train_02_ipfa_stable.py
```

稳定版输出到 `ablation_02_ipfa_stable`，不会覆盖原来的 `ablation_02_ipfa`。它只把 `lr0` 从 `0.003` 降到 `0.001`，并把 `amp` 从 `true` 改为 `false`，其余训练设置保持一致。

第3组：

```bash
python train_03_csfm.py
```

第4组：

```bash
python train_04_fgafpn.py
```

第5组：

```bash
python train_05_full.py
```

也可以使用统一入口，例如：

```bash
python train_ablation.py --experiment ipfa
python train_ablation.py --experiment csfm
python train_ablation.py --experiment fgafpn
python train_ablation.py --experiment full
```

## 五、训练参数不要随意改

五组实验共同使用`train_config.yaml`：

```text
epochs=100
imgsz=960
batch=4
optimizer=AdamW
lr0=0.003
lrf=0.01
patience=20
seed=0
workers=0
```

为了保证消融实验公平，不能单独修改学习率、输入尺寸、数据增强、训练轮数和随机种子。

如果显存不足，只允许修改：

```yaml
batch: 2
```

仍然不足再改为`batch: 1`，并在最终表格中注明。`nbs: 64`不要修改。

CSFM和FGAFPN模型约有3900万至4000万参数，比原始YOLOv8s更占显存。8GB显卡建议直接使用`batch: 1`或交给服务器训练。

## 六、训练结果在哪里

所有结果保存在：

```text
IF-YOLO消融实验包/runs/detect/实验名称/
```

训练结束后，每个人需要上交自己的整个结果文件夹，至少包含：

```text
args.yaml
results.csv
results.png
confusion_matrix.png
confusion_matrix_normalized.png
BoxPR_curve.png
val_batch0_pred.jpg
weights/best.pt
weights/last.pt
```

## 七、训练中断后怎么继续

假设第2组的训练中断：

```bash
python train_ablation.py --experiment ipfa --resume runs/detect/ablation_02_ipfa/weights/last.pt
```

`--experiment`仍然要填写，但断点训练会直接读取`last.pt`中的原设置。

## 八、常见错误

### 报错`IPFA is not defined`或`CSFM is not defined`

当前环境没有完成模块注册：

```bash
python install_ifyolo.py
```

### 报错`CUDA out of memory`

关闭其他占用GPU的软件，并把`train_config.yaml`中的`batch`改为2或1。

### 报错`No images found`

检查`VisDrone_server.yaml`第一行。`path`必须指向同时包含`images`和`labels`的目录。

### 模型下载`yolov8s.pt`失败

把已有的`yolov8s.pt`放到本文件夹中，然后将`train_ablation.py`中的：

```python
model.load("yolov8s.pt")
```

改为：

```python
model.load(str(ROOT / "yolov8s.pt"))
```

## 九、最后怎么比较

每个人训练完成后，统一记录最佳轮次的以下指标：

| 实验 | Precision | Recall | mAP50 | mAP50-95 | 参数量 | GFLOPs |
|---|---:|---:|---:|---:|---:|---:|
| 原始YOLOv8s |  |  |  |  |  |  |
| +IPFA |  |  |  |  |  |  |
| +CSFM |  |  |  |  |  |  |
| +FGAFPN |  |  |  |  |  |  |
| 完整IF-YOLO |  |  |  |  |  |  |

主要观察：

1. IPFA是否提高了小目标Recall。
2. CSFM是否减少了特征融合冲突并提高mAP。
3. FGAFPN是否提高了P2小目标检测效果。
4. 完整IF-YOLO的提升是否值得增加的参数量和显存消耗。

参考论文：<https://www.mdpi.com/2072-4292/16/14/2590>
