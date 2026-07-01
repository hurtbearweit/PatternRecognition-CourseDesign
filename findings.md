# Findings

## Directory Inventory
- `week15_final_training_package` includes: `README_训练说明.md`, `train_config.yaml`, `VisDrone.yaml`, `if_yolov8s.yaml`, `if_yolov8s_wiou.yaml`, `if_yolov8s_wiou_csfm_lite.yaml`, `if_yolov8s_wiou_csfm_lite_mkp.yaml`, `week15_modules.py`, `install_week15_modules.py`, `train_week15_experiment.py`, and `yolov8s.pt`.
- `week15_final_training_result` includes two completed experiment folders: `week15_if_yolov8s_wiou-2` and `week15_if_yolov8s_wiou_csfm_lite-3`, plus `wiou.log` and `csfm.log`.
- Baseline `十五周/train-5` includes matching YOLO output artifacts: `results.csv`, `args.yaml`, metric curves, confusion matrices, train/val batch images.

## Improvement Package
- Training config: 100 epochs, image size 960, batch 4, AdamW, lr0 0.003, lrf 0.01, patience 20, mosaic 1.0, copy_paste 0.2, mixup 0.1, cls 2.0, box 7.5, iou 0.5, AMP enabled, seed 0.
- Dataset config: VisDroneYOLO with 10 classes: pedestrian, person, bicycle, car, van, truck, tricycle, awning-tricycle, bus, motor.
- Base IF-YOLO yaml uses IPFA downsampling in early backbone, CSFM three-scale fusion in the head, and four-scale Detect outputs.
- WIoU yaml keeps the same IF-YOLO structure and adds `loss: wiou_v3`; the trainer applies WIoU v3 by monkey-patching Ultralytics `v8DetectionLoss` / `BboxLoss` while keeping DFL.
- CSFM-lite yaml keeps WIoU v3 and replaces CSFM with CSFMLite in three head fusion nodes.
- MKP yaml adds `P5MKPLite` after SPPF and shifts the later indices accordingly; no result folder for this method was found in the provided result path.
- `CSFMLite` replaces heavier CRC/CCSM/SCSM style fusion with GAP/GMP+ECA channel weighting plus depthwise spatial branch, likely aiming to reduce compute and improve small-object multi-scale fusion.
- `P5MKPLite` concatenates identity plus depthwise 3x3/5x5/7x7 branches on P5, then pointwise conv + BN + SiLU with residual if channels match.

## Experiment Results
- WIoU run: 100 epochs. Best mAP50-95 at epoch 84: mAP50-95 0.29014, mAP50 0.51042, precision 0.60004, recall 0.50065. Final epoch: mAP50 0.50001, mAP50-95 0.28665, precision 0.59317, recall 0.49676. Final val box loss 1.41569. Logged fused model: 149 layers, 39,427,585 parameters, 71.5 GFLOPs.
- CSFM-lite run: 100 epochs. Best mAP50-95 at epoch 89: mAP50-95 0.30003, mAP50 0.51578, precision 0.60453, recall 0.50807. Best mAP50 at epoch 79: mAP50 0.51616, mAP50-95 0.29831. Final epoch: mAP50 0.50665, mAP50-95 0.29490, precision 0.60299, recall 0.49863. Final val box loss 1.37288. Logged fused model: 134 layers, 11,280,362 parameters, 46.8 GFLOPs.
- Final validation logs show WIoU all-class final post-train validation mAP50-95 0.28866 and CSFM-lite 0.29855; both are consistent with CSV final/best values.
- CSFM-lite per-class best-run log at training end: strong classes car mAP50-95 0.608, bus 0.482, van 0.384; weak classes remain awning-tricycle 0.120, bicycle 0.130, person 0.188.
- Curves: all three runs converge smoothly; mAP50-95 generally peaks around epochs 80-90 and then slightly eases, suggesting mild late overfitting or post-peak noise rather than training failure.

## Baseline Results
- Baseline IF-YOLO train-5: 100 epochs. Best mAP50-95 at epoch 89: mAP50-95 0.27970, mAP50 0.51025, precision 0.59654, recall 0.49985. Best mAP50 at epoch 88: mAP50 0.51069, mAP50-95 0.27895. Final epoch: mAP50 0.50024, mAP50-95 0.27557, precision 0.59633, recall 0.49296. Final val box loss 1.49732.

## Comparative Notes
- Compared against baseline best mAP50-95 0.27970:
  - WIoU best mAP50-95 0.29014, +0.01044 absolute, about +3.7% relative.
  - WIoU+CSFM-lite best mAP50-95 0.30003, +0.02033 absolute, about +7.3% relative.
- Compared against baseline best mAP50 0.51069:
  - WIoU best mAP50 0.51042, essentially flat (-0.00027 if using each run's best mAP50).
  - WIoU+CSFM-lite best mAP50 0.51616, +0.00547 absolute.
- Compared using best mAP50-95 epochs:
  - Baseline epoch 89: P 0.59654, R 0.49985, mAP50 0.51025, mAP50-95 0.27970.
  - WIoU epoch 84: P 0.60004, R 0.50065, mAP50 0.51042, mAP50-95 0.29014.
  - CSFM-lite epoch 89: P 0.60453, R 0.50807, mAP50 0.51578, mAP50-95 0.30003.
- Main interpretation: WIoU improves stricter localization quality more than loose IoU detection, visible as mAP50-95 gain with nearly unchanged mAP50. CSFM-lite adds further gains in precision, recall, mAP50, and mAP50-95.
- Validation box loss drops from baseline final 1.49732 to WIoU 1.41569 and CSFM-lite 1.37288, supporting better localization/regression quality.
- CSFM-lite is the stronger result among the two methods because it improves accuracy while logged fused model size is far smaller than WIoU/original CSFM structure (11.28M params, 46.8 GFLOPs vs WIoU 39.43M params, 71.5 GFLOPs).
- Artifact metadata check: WIoU `best.pt`/`last.pt` are about 79.45 MB; CSFM-lite `best.pt`/`last.pt` are about 23.14 MB; baseline `best.pt`/`last.pt` are about 79.42 MB. This supports the conclusion that CSFM-lite substantially reduces model size.
- Caveat: training times are not directly comparable because baseline uses different device/workers path setup; metric comparison is more reliable because hyperparameters and dataset are matched.

## MKP Addendum 2026-06-18
- New MKP run found at `week15_final_training_result/week15_if_yolov8s_wiou_csfm_lite_mkp/week15_if_yolov8s_wiou_csfm_lite_mkp`.
- MKP args match the prior week-15 setup: 100 epochs, image size 960, batch 4, AdamW, lr0 0.003, lrf 0.01, same augmentation and loss weights. Model is `if_yolov8s_wiou_csfm_lite_mkp.yaml`.
- MKP best mAP50-95 at epoch 88: mAP50-95 0.28740, mAP50 0.50919, precision 0.60144, recall 0.50032.
- MKP best mAP50 at epoch 85: mAP50 0.50984, mAP50-95 0.28539.
- MKP final epoch 100: mAP50 0.49652, mAP50-95 0.28304, precision 0.59012, recall 0.49251, final val box loss 1.41797.
- MKP final validation log: all-class mAP50 0.49328, mAP50-95 0.28558. Logged fused model: 140 layers, 12,372,458 parameters, 47.7 GFLOPs.
- MKP weight metadata: `best.pt` and `last.pt` are about 25.33 MB.
- Compared with baseline best mAP50-95 0.27970, MKP improves by +0.00770 absolute, about +2.8% relative.
- Compared with WIoU best mAP50-95 0.29014, MKP is lower by -0.00274.
- Compared with CSFM-lite best mAP50-95 0.30003, MKP is lower by -0.01263 and also lower in best mAP50, final mAP, and final val box loss.
- Interpretation: adding P5-MKP-Lite on top of WIoU+CSFM-lite did not produce additive benefit. It keeps the model lightweight but slightly larger than CSFM-lite and degrades accuracy. Current best method remains WIoU+CSFM-lite.

## Week17 DySample Package Addendum 2026-06-18
- Created week17 package under `本周进展说明及下周计划报告/十七周`.
- Implemented pure PyTorch `DySampleYOLO` with 1x1 offset conv and `F.grid_sample`; default args are scale=2, style=lp, groups=4, dyscope=False, and channels are preserved.
- Implemented `LocalDetailRefine` and `WeightedFeatureFusion`.
- Created DySample ablation YAMLs for P4->P3, P3->P2, and P4->P3+P3->P2. No YAML includes MKP structures.
- Created default best LDR/WFF YAMLs from the P3->P2 placeholder and provided `generate_best_configs.py` to regenerate them after ablation identifies the true best DySample node.
- Created `install_week17_modules.py`, `check_week17_models.py`, `train_week17_experiment.py`, and `README_十七周DySample实验操作说明.md`.
- Verification done locally: Python files compile and config generator works for all best-node options. Tensor forward checks are deferred to the training environment because local Python lacks torch.
- Follow-up verification in `course_ai`: module tensor checks passed. DySampleYOLO maps (1,128,20,30) to (1,128,40,60); LocalDetailRefine preserves shape; WeightedFeatureFusion produced (1,128,20,20).
- `course_ai` Ultralytics registration passed via `install_week17_modules.py`.
- `course_ai` model checks passed for `dys_p4p3`, `dys_p3p2`, `dys_p4p3_p3p2`, `dys_best_ldr`, and `dys_best_wff` at imgsz=320 and imgsz=960. Checks confirmed DySample execution, Concat/WFF spatial consistency, four-scale Detect sources, WIoU+DFL criterion, and no MKP in YAMLs.

## Week17 Results Addendum 2026-06-21
- Results folder analyzed: `本周进展说明及下周计划报告/十七周/results`.
- All five week17 runs used the same key training config: 100 epochs, imgsz 960, batch 4, AdamW, lr0 0.003, lrf 0.01, seed 0, iou 0.5, box 7.5, cls 2.0, mosaic 1.0, mixup 0.1, copy_paste 0.2.
- Best mAP50-95 ranking:
  - WFF: best mAP50-95 0.29896 at epoch 86, best mAP50 0.51520, final mAP50-95 0.29443, post-val mAP50-95 0.29827, 11.313M fused params, 47.3 GFLOPs, 22.14 MB, 17.05 ms, 58.67 FPS.
  - DySample P4->P3 + P3->P2: best mAP50-95 0.29768 at epoch 89, best mAP50 0.51493, final mAP50-95 0.29394, post-val mAP50-95 0.29633, 11.293M fused params, 46.9 GFLOPs, 22.09 MB, 16.64 ms, 60.09 FPS.
  - LDR: best mAP50-95 0.29007 at epoch 85, best mAP50 0.51823, final mAP50-95 0.28857, post-val mAP50-95 0.28828, 11.380M fused params, 48.7 GFLOPs, 22.27 MB, 16.23 ms, 61.62 FPS.
  - DySample P3->P2: best mAP50-95 0.28799 at epoch 90, best mAP50 0.51489, final mAP50-95 0.28579, post-val mAP50-95 0.28563, 11.284M fused params, 46.8 GFLOPs, 22.08 MB, 15.41 ms, 64.90 FPS.
  - DySample P4->P3: best mAP50-95 0.28734 at epoch 88, best mAP50 0.51030, final mAP50-95 0.28131, post-val mAP50-95 0.28518, 11.289M fused params, 46.8 GFLOPs, 22.09 MB, 15.23 ms, 65.64 FPS.
- Compared with the previous best baseline WIoU+CSFM-lite best mAP50-95 0.30003, none of the week17 variants surpass it. WFF is closest at -0.00107 absolute mAP50-95; dual DySample is second at -0.00235.
- Compared with WIoU+CSFM-lite best mAP50 0.51616, LDR has the highest best mAP50 at 0.51823 but its mAP50-95 drops to 0.29007, indicating looser-threshold detection improves while localization quality worsens.
- Class AP from summary suggests WFF is the best week17 variant, especially on car 0.6093, bus 0.4759, van 0.3796, pedestrian 0.2870, motor 0.2819. It is still slightly weaker than prior CSFM-lite on bus/van/tricycle/truck and overall mAP50-95.
- Interpretation: DySample alone did not help in this setup. Replacing both P4->P3 and P3->P2 is much better than replacing either single node, but still slightly below CSFM-lite baseline. LDR should not be kept because it increases mAP50 but hurts strict localization. WFF is worth keeping only as a candidate for a repeat/combined experiment, not as a new baseline yet.
- AP_small remains unavailable in these summaries because the current YOLO-txt validation flow does not expose COCO-style AP_small.
