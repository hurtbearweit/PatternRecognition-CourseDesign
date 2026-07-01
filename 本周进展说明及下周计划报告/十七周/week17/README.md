# Week17 Local WFF Experiment Package

本包用于完成第十七周两个任务：

1. 在 `IF-YOLO + WIoU v3 + CSFM-Lite` 基准模型上，只把 Neck 中 P3 -> P2 高分辨率融合节点替换为轻量 `WeightedFeatureFusion`。
2. 对 A/B 两个模型做 `seed=0/1/2` 多随机种子稳定性验证。

本包不包含大权重文件，不复制历史训练结果，不修改 `train_config.yaml`。

## 目录结构

```text
week17/
├── configs/
│   ├── train_config.yaml
│   ├── visdrone.yaml
│   ├── if_yolov8s_wiou_csfmlite.yaml
│   └── if_yolov8s_wiou_csfmlite_wff_p3p2.yaml
├── modules/
│   ├── weighted_fusion.py
│   └── week17_existing_modules.py
├── scripts/
│   ├── install_week17_modules.py
│   ├── check_wff_model.py
│   ├── train_experiment.py
│   ├── run_parallel_experiments.py
│   └── summarize_multiseed.py
├── results/tables/
├── logs/
├── task_plan.md
├── progress.md
└── findings.md
```

## 环境要求

- Python 环境中已安装 Ultralytics YOLOv8。
- 项目已有 WIoU v3 + DFL 实现。本包不重新实现 WIoU。
- 服务器有 5 张 RTX 3090 时可直接跑五卡并行脚本；少于 5 张时可手动执行单实验命令。
- 训练前只需要确认 `week17/configs/visdrone.yaml` 中的数据集路径适配服务器。
- `week17/configs/train_config.yaml` 保留统一训练参数，不要改 epochs/imgsz/batch/optimizer/学习率/增强。
- 训练脚本会自动生成 `week17/logs/runtime_train_config.yaml`，只把 `data` 指向 `week17/configs/visdrone.yaml`，避免使用本地 Windows 路径。
- 如果 Windows 环境遇到 OpenMP 重复运行库报错，可先设置 `KMP_DUPLICATE_LIB_OK=TRUE`；Linux 服务器通常不需要。

禁止修改统一训练参数：`epochs`、`imgsz`、`batch`、`optimizer`、学习率、数据增强。允许覆盖的运行参数只有 `model`、`name`、`device`、`seed`、`project`、`resume`。

## 1. 安装自定义模块

在项目根目录执行：

```bash
python week17/scripts/install_week17_modules.py
```

脚本会把以下模块注册到当前 Python 环境的 Ultralytics：

- `IPFA`
- `CSFMLite`
- `WeightedFeatureFusion`

并在 `tasks.py/parse_model` 中加入 `IPFA`、`CSFMLite` 和 `WeightedFeatureFusion` 的通道推导逻辑。

如果之前运行旧安装脚本报过 `IPFA.__init__() missing 1 required positional argument: 'c2'`，直接覆盖运行新版安装脚本即可：

```bash
python week17/scripts/install_week17_modules.py
```

## 2. 数据路径

默认 `week17/configs/visdrone.yaml` 为服务器相对路径模板：

```yaml
path: ../datasets/VisDroneYOLO
train: images/train
val: images/val
test: images/test
```

如果服务器数据集不在这个位置，只修改 `week17/configs/visdrone.yaml` 的 `path`。不要修改 `train_config.yaml` 的训练超参数。

## 3. 训练前检查 WFF 模型

```bash
python week17/scripts/check_wff_model.py --model week17/configs/if_yolov8s_wiou_csfmlite_wff_p3p2.yaml --device cuda:0
```

检查内容：

- YAML 可加载；
- `640` 和 `960` 输入均可 forward；
- Detect 仍为 P2/P3/P4/P5 四尺度；
- YAML 保持 `loss: wiou_v3`；
- 模型中无 MKP、DySample、LDR；
- 输出 Params，并由 `model.info(imgsz=960)` 打印 GFLOPs。

检查结果保存到：

```text
week17/results/tables/wff_model_check.json
```

## 4. 单实验训练命令

候选 A：`IF-YOLO + WIoU v3 + CSFM-Lite`

```bash
python week17/scripts/train_experiment.py --model A --name week17_A_if_wiou_csfmlite_seed0 --device 0 --seed 0
```

候选 B：`IF-YOLO + WIoU v3 + CSFM-Lite + WFF(P3->P2)`

```bash
python week17/scripts/train_experiment.py --model B --name week17_B_if_wiou_csfmlite_wff_seed0 --device 0 --seed 0
```

当前模型复杂度检查结果：

```text
A: 11,290,506 Params, 105.9 GFLOPs @ imgsz=960
B: 11,294,604 Params, 106.4 GFLOPs @ imgsz=960
```

训练入口内部使用：

```python
model.train(
    cfg=str(TRAIN_CFG),
    model=模型配置,
    name=实验名称,
    device=device,
    seed=seed,
    exist_ok=False,
)
```

训练完成后会加载对应 `weights/best.pt` 重新验证，并保存：

```text
week17_metrics_summary.json
week17_metrics_summary.csv
week17_inputs/
```

## 5. 五卡并行启动

```bash
python week17/scripts/run_parallel_experiments.py --project week17/runs/detect
```

默认分配：

```text
GPU0: week17_A_if_wiou_csfmlite_seed0
GPU1: week17_A_if_wiou_csfmlite_seed1
GPU2: week17_A_if_wiou_csfmlite_seed2
GPU3: week17_B_if_wiou_csfmlite_wff_seed0
GPU4: week17_B_if_wiou_csfmlite_wff_seed1
任意 GPU 空闲后: week17_B_if_wiou_csfmlite_wff_seed2
```

先查看命令但不启动：

```bash
python week17/scripts/run_parallel_experiments.py --project week17/runs/detect --dry-run
```

日志位置：

```text
week17/logs/*.stdout.log
week17/logs/*.stderr.log
week17/logs/parallel_experiments_manifest.csv
```

## 6. 多种子结果汇总

六次训练完成后执行：

```bash
python week17/scripts/summarize_multiseed.py --project week17/runs/detect
```

输出：

```text
week17/results/tables/multiseed_raw.csv
week17/results/tables/multiseed_summary.csv
week17/results/tables/multiseed_summary.md
```

汇总指标：

- Precision
- Recall
- mAP50
- mAP50-95
- best epoch
- best.pt 路径
- 权重大小

选择规则：

1. 第一优先级：三次平均 `mAP50-95`。
2. 若 A/B 平均 `mAP50-95` 差异不超过 `0.002`，优先选择结构更简单、GFLOPs 更低、标准差更小的模型。
3. 不根据单次最高结果选最终模型。

## 7. 六组训练命令

```bash
python week17/scripts/train_experiment.py --model A --name week17_A_if_wiou_csfmlite_seed0 --device 0 --seed 0
python week17/scripts/train_experiment.py --model A --name week17_A_if_wiou_csfmlite_seed1 --device 1 --seed 1
python week17/scripts/train_experiment.py --model A --name week17_A_if_wiou_csfmlite_seed2 --device 2 --seed 2
python week17/scripts/train_experiment.py --model B --name week17_B_if_wiou_csfmlite_wff_seed0 --device 3 --seed 0
python week17/scripts/train_experiment.py --model B --name week17_B_if_wiou_csfmlite_wff_seed1 --device 4 --seed 1
python week17/scripts/train_experiment.py --model B --name week17_B_if_wiou_csfmlite_wff_seed2 --device 0 --seed 2
```

## 8. 注意事项

- 不要把 `.pt` 权重放进 `week17/` 包里。
- 如果运行目录已存在，`train_experiment.py` 默认拒绝覆盖。
- 如需续训，先确认对应目录存在 `weights/last.pt`，再加 `--resume`。
- 如果服务器上的 Ultralytics 已经注册过同名模块，安装脚本会保留备份文件并重复写入最小必要注册。
- 若 `check_wff_model.py` 提示 WIoU 不存在，说明服务器环境缺少项目已有的 WIoU v3 改动，需要先同步原项目的 WIoU 实现。
