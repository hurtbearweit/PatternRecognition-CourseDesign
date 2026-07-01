# Progress Log

## 2026-06-21 Week17 Results
- Read week17 `results` folder.
- Extracted best/final metrics from each `results.csv` and latency/model-size/class AP from `week17_summary.json`.
- Read logs for Params/GFLOPs and confirmed all runs used the same key training hyperparameters.
- Compared week17 variants against the previous WIoU+CSFM-lite baseline.
- Errors: PowerShell `ConvertFrom-Yaml` was unavailable; a multiline `conda run python -c` command failed because conda does not support newline arguments. Resolved by using `Select-String` for args checks.

## 2026-06-18 DySample Package
- Started week17 DySample/LDR/WFF package generation.
- Directory creation first failed because New-Item did not accept -LiteralPath; retrying with -Path succeeded.
- A Bash-style Python heredoc failed under PowerShell, so planning files are being updated with apply_patch.
- Created week17 module, installer, model YAMLs, best-config generator, pre-training checker, trainer, copied train_config/VisDrone/yolov8s.pt, and wrote operation guide.
- Verified Python syntax with py_compile.
- Verified generate_best_configs.py for p4p3, p3p2, and p4p3_p3p2; fixed a channel-number shift bug before finalizing.
- Could not run tensor forward locally because the active Python environment has no torch module; check_week17_models.py is provided for the training environment.
- Re-ran tensor checks in conda env `course_ai`. Initial run hit duplicate OpenMP runtime; setting `KMP_DUPLICATE_LIB_OK=TRUE` allowed checks to run.
- `course_ai` module tensor checks passed for DySampleYOLO, LocalDetailRefine, and WeightedFeatureFusion.
- `course_ai` install_week17_modules.py passed.
- `course_ai` check_week17_models.py passed for all five YAMLs at imgsz=320 and imgsz=960 on CPU.

## 2026-06-18
- Added MKP result analysis from `week15_final_training_result`.
- Extracted MKP best/final CSV metrics, run args, log summary, curve behavior, and weight metadata.
- Compared MKP against baseline, WIoU, and WIoU+CSFM-lite.

## 2026-06-17
- Created planning files for IF-YOLO improvement package and result analysis.
- Completed directory inventory for improvement package, two week-15 experiment outputs, and baseline train-5.
- Read improvement package configs, model YAMLs, custom modules, install script, and training script.
- Extracted best/final metrics from baseline, WIoU, and CSFM-lite `results.csv`; inspected run arguments, logs, and results curves.
- Completed comparative analysis and recorded conclusions.
- Read metadata for all result images and model weight artifacts in the provided directories.
- Started additional analysis for `十六周/IPFA_new`.
