# IF-YOLO 改进方案与实验结果分析计划

## 2026-06-18 DySample Package Addendum
| Phase | Status | Notes |
|---|---|---|
| Create week17 training package | complete | Generated DySample, LDR, WFF modules, YAMLs, check/train scripts, and operation guide |
| Verify week17 training package | complete | py_compile and generator checks passed; torch forward deferred to training environment |
| Analyze week17 training results | complete | Read results folder, compared DySample/LDR/WFF against CSFM-Lite baseline |

## Errors Encountered Addendum
| Error | Attempt | Resolution |
|---|---|---|
| New-Item did not accept -LiteralPath | directory creation attempt 1 | Retried with -Path |
| Bash-style python heredoc failed in PowerShell | planning log update attempt 1 | Switched to apply_patch |

## 2026-06-18 Addendum
| Phase | Status | Notes |
|---|---|---|
| MKP 结果追加分析 | complete | 已读取新增 MKP 训练结果，并与 WIoU、CSFM-lite、基础 IF-YOLO 对比 |

## Goal
读取 week15_final_training_package、week15_final_training_result 和 train-5 三个目录，梳理改进方案内容、两个方法的实验结果，以及相对基础 IF-YOLO 的表现变化。

## Phases
| Phase | Status | Notes |
|---|---|---|
| 1. 目录盘点 | complete | 方案包、两个改进实验结果、基础 train-5 结果均存在 |
| 2. 改进方案读取 | complete | 已读取 README、训练配置、数据配置、模型 yaml、模块实现、安装脚本、训练脚本 |
| 3. 实验结果读取 | complete | 已读取 WIoU 与 WIoU+CSFM-lite 的 results.csv、args.yaml、日志和曲线图 |
| 4. 基线结果读取 | complete | 已读取十五周 train-5 的基础 IF-YOLO 结果 |
| 5. 对比分析 | complete | 已汇总指标变化、训练曲线、优缺点和建议 |
| 6. IPFA_new 追加分析 | in_progress | 读取十六周 IPFA_new 重训结果并与已有结果比较 |

## Errors Encountered
| Error | Attempt | Resolution |
|---|---|---|
