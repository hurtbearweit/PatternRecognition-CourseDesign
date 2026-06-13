# 模式识别课程设计

课程设计题目：无人机视角下的目标检测。

本项目以 VisDrone 数据集为基础，使用 YOLOv8 系列模型开展无人机航拍场景下的多类别目标检测实验，包含数据格式转换、基线训练、改进模型配置、实验对比和阶段报告。

## 项目结构

```text
.
├─ assignment/                    # 课程设计题目
├─ Dataset/                       # 数据转换脚本（原始数据不纳入 Git）
├─ Model/                         # 训练脚本与模型配置
├─ Reference/                     # 参考论文
├─ tools/                         # 报告生成、文档提取与结果对比工具
├─ 本周进展说明及下周计划报告/       # 第 13-15 周阶段材料
├─ Dataset.md                     # 数据集下载与放置说明
├─ requirements.txt               # Python 依赖
└─ visdrone.yaml                  # VisDrone 数据集配置示例
```

训练产生的 `runs/`、模型权重、缓存以及完整数据集体积较大，均通过 `.gitignore` 排除，仅保留可复现实验所需的代码、配置和报告。

## 环境配置

建议使用 Python 3.10 或更高版本，并根据 CUDA 环境安装合适版本的 PyTorch。

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## 数据准备

按照 [Dataset.md](Dataset.md) 下载数据集。将转换后的 YOLO 格式数据放在 `Dataset/VisDroneYOLO/`，目录应包含 `images/train`、`images/val`、`images/test` 及对应的 `labels/`。

如需从 VisDrone 原始标注转换为 YOLO 格式，可运行：

```powershell
python Dataset/visdrone2yolo.py --dir_path <VisDrone数据集目录>
```

运行训练前，请按本机实际路径修改 `Model/visdrone.yaml` 或根目录的 `visdrone.yaml` 中的 `path`。

## 模型训练

基线训练示例：

```powershell
python Model/train_visdrone.py
```

改进模型与第十五周对比实验可使用 `Model/train_lud_visdrone.py`、`Model/train_yolov8s_week15.py` 和 `Model/train_lud_week15.py`。

训练结果默认保存在 `Model/runs/detect/`，该目录仅保留在本地。

## 说明

- `Reference/` 收录课程设计使用的相关论文。
- `本周进展说明及下周计划报告/` 收录阶段报告和小组材料。
- 大型数据集和模型权重不适合直接提交到普通 Git 仓库，可通过网盘或 GitHub Release 单独分发。
