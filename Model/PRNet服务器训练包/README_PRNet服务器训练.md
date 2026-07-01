# PRNet-YOLOv8s 服务器训练说明

这个文件夹已经包含训练所需的全部自定义文件。无需理解 PRNet 源码，只需按下面顺序执行。

## 1. 文件夹内容

```text
PRNet服务器训练包/
├── README_PRNet服务器训练.md    本说明
├── prnet_module.py              ESSamp 自定义模块
├── install_prnet.py             自动安装并注册 ESSamp
├── prnet_yolov8s.yaml           PRNet-YOLOv8s 网络结构
├── VisDrone_server.yaml         VisDrone 数据集配置
├── train_config.yaml            训练参数
└── train_prnet.py               训练入口
```

训练前把整个 `PRNet服务器训练包` 文件夹上传到服务器。文件之间的相对位置不要改变。

## 2. 数据集目录要求

VisDrone 数据集应保持下面的 YOLO 格式：

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

打开 `VisDrone_server.yaml`，只修改第一行 `path`，填服务器上 `VisDroneYOLO` 的真实绝对路径：

```yaml
path: /home/用户名/datasets/VisDroneYOLO
```

不要把 `path` 写到 `images/train`，它必须指向同时包含 `images` 和 `labels` 的目录。

## 3. 创建环境

推荐使用 Python 3.10 或 3.11。先安装与服务器 CUDA 匹配的 PyTorch，再安装固定版本的 Ultralytics：

```bash
conda create -n prnet python=3.10 -y
conda activate prnet

# 如果服务器已经装好支持 CUDA 的 torch，可以跳过下一行。
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu126

pip install ultralytics==8.4.53
```

检查 GPU 是否可用：

```bash
python -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0))"
```

第一个结果必须是 `True`。

## 4. 安装 PRNet 模块

进入训练包目录后执行：

```bash
cd /你的路径/PRNet服务器训练包
python install_prnet.py
```

脚本会自动完成以下修改：

1. 将 `prnet_module.py` 复制到 `ultralytics/nn/modules/prnet.py`。
2. 在 `ultralytics/nn/modules/__init__.py` 中导出 `ESSamp`。
3. 在 `ultralytics/nn/tasks.py` 中导入并注册 `ESSamp`。
4. 构建一次模型，输出 `PRNet installation verified successfully.` 即安装成功。

脚本可重复执行，不会重复插入代码。它也会在修改前生成 `.bak_prnet` 备份。

## 5. 开始训练

```bash
python train_prnet.py
```

脚本会自动下载 `yolov8s.pt` 预训练权重，并把能匹配的权重加载到 PRNet-YOLOv8s。

训练结果保存在：

```text
PRNet服务器训练包/runs/detect/week15_prnet/
```

主要文件：

```text
weights/best.pt     验证集效果最好的模型
weights/last.pt     最后一个 epoch 的模型
results.csv         每轮训练指标
results.png         损失和精度曲线
confusion_matrix.png
```

## 6. 训练参数

训练参数与原始 YOLOv8s 和 LUD-YOLO 对比实验保持一致：

```text
epochs=100
imgsz=960
batch=4
optimizer=AdamW
lr0=0.003
patience=20
```

PRNet 使用 P2 高分辨率特征，显存占用明显高于原始 YOLOv8s。如果服务器仍然显存不足，只修改 `train_config.yaml`：

```yaml
batch: 2
```

不要修改图片尺寸、学习率、数据增强或网络 YAML，否则会影响与其他模型的公平对比。`nbs: 64` 会保留统一的标称批量设置。

## 7. 继续中断的训练

如果已经产生 `last.pt`，执行：

```bash
python train_prnet.py --resume runs/detect/week15_prnet/weights/last.pt
```

## 8. 常见错误

### `KeyError: 'ESSamp'` 或 `ESSamp is not defined`

说明当前环境没有注册模块。确认已激活训练环境，然后重新执行：

```bash
python install_prnet.py
```

### `CUDA out of memory`

将 `train_config.yaml` 中的 `batch: 4` 改为 `batch: 2`；仍不足时改成 `batch: 1`。

### `No images found`

检查 `VisDrone_server.yaml` 第一行路径，以及数据集是否同时存在 `images/train` 和 `labels/train`。

### PyTorch 显示 `CUDA available: False`

这是 PyTorch/CUDA 环境问题，与 PRNet 网络无关。需要让服务器管理员安装与驱动匹配的 CUDA 版 PyTorch。

## 9. 网络改动概述

相对于原始 YOLOv8s，本模型只改变网络结构：

1. 使用 ESSamp 进行保留细节的下采样。
2. 使用三轮渐进式特征精炼，将深层语义逐步传递到 P2 小目标特征。
3. 使用 P2、P3、P4 三个检测尺度，增强 VisDrone 中密集小目标的检测能力。
4. 数据集、训练轮数、输入尺寸、优化器、学习率和增强参数与对比实验一致。

参考方法讲解：<https://blog.csdn.net/m0_62919535/article/details/153969350>
