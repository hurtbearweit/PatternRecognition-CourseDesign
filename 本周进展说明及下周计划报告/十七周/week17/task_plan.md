# Week17 WFF Package Task Plan

## Goal
Create a clean runnable package for the week17 local WFF experiment and A/B multi-seed stability validation.

## Scope
- Add only `WeightedFeatureFusion` at the P3 -> P2 high-resolution neck fusion node.
- Keep the baseline as IF-YOLO + WIoU v3 + CSFM-Lite.
- Do not add MKP, DySample, LDR, Transformer blocks, or a fifth detection head.
- Do not modify `train_config.yaml`.

## Phases
1. Rebuild package structure under `week17/`.
2. Add WFF module and module installer for Ultralytics.
3. Add WFF model YAML.
4. Add train, five-GPU launcher, model check, and multi-seed summary scripts.
5. Write README and running commands for classmates.
6. Run syntax checks and focused smoke checks in `course_ai`.
7. Package `week17/` into a zip without large weights.

## Expected Outputs
- `week17/modules/weighted_fusion.py`
- `week17/configs/if_yolov8s_wiou_csfmlite_wff_p3p2.yaml`
- `week17/scripts/install_week17_modules.py`
- `week17/scripts/check_wff_model.py`
- `week17/scripts/train_experiment.py`
- `week17/scripts/run_parallel_experiments.py`
- `week17/scripts/summarize_multiseed.py`
- `week17/README.md`
- `week17_package.zip`

