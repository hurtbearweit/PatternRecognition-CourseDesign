# Week17 Findings

## Model Structure
- Baseline config is copied from the week15 final model: IF-YOLO + WIoU v3 + CSFM-Lite.
- The P3 -> P2 fusion node is the neck node `[[ -1, 10 ], 1, Concat, [1]]` after the third top-down upsample.
- The WFF variant replaces only that node with `WeightedFeatureFusion`; all other neck fusions remain unchanged.
- Detect still receives four feature maps: P2, P3, P4, P5.

## Constraints
- `train_config.yaml` is copied for convenience but not modified.
- WIoU v3 is treated as existing project functionality and is not reimplemented in this package.
- MKP, DySample, LDR, and a fifth detection head are not included in the new WFF YAML.

## Test Notes
- `install_week17_modules.py` passed in `course_ai`.
- `check_wff_model.py` passed in `course_ai` on CUDA.
- WFF model check output: 201 layers, 11,294,604 parameters, 106.4 GFLOPs.
- A baseline model info: 200 layers, 11,290,506 parameters, 105.9 GFLOPs.
- B WFF model info: 201 layers, 11,294,604 parameters, 106.4 GFLOPs.
- `WeightedFeatureFusion([64,128],128)` CUDA forward/backward passed.
- `run_parallel_experiments.py --dry-run` printed the expected five-GPU launch commands.
- `summarize_multiseed.py` handles missing training outputs and writes placeholder tables without fabricating metrics.
- Error note: Bash-style heredoc is not supported in PowerShell; use `python -c` or a script file for inline checks on Windows.
- Error note: On this Windows environment, standalone Torch checks need `KMP_DUPLICATE_LIB_OK=TRUE` to avoid duplicate OpenMP runtime aborts.
