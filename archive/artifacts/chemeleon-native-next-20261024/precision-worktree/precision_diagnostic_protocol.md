# Bounded CheMeleon mixed-precision diagnostic

Question: did a native CheMeleon own750 2d6isoform6 fold0 call stop after a nonfinite validation loss, silently restore its finite epoch0 checkpoint, and report finite final predictions? The observed short duration and bestepoch0 motivate this check; they do not prove that explanation.

Replay the exact same prepared pool/fold/seed/checkpoint/native model/loss/LR schedule under16-mixed andbf16-mixed, two workers onGPU0/1. Native vendor files are unchanged. The wrapper changes only the precision treatment and adds observational/budget callbacks. Trainer.max_epochs remains400, patience40, warmup2, nativeLR1e-4/1e-3/1e-4, batch64, frozen-model epochs0. The added callback stops after zero-based epoch3, preserving the original400epoch scheduler horizon; native EarlyStopping may stop earlier.

The runtime's actual EarlyStopping._evaluate_stopping_criteria is wrapped, called exactly once per check, and its returned boolean/reason and before/after state are saved. Its decision logic and verbose flag remain unchanged. Epoch validation loss, finite flag, LR, scaler state, should_stop, callback state and checkpoint information are recorded. fit_end also records model-state nonfinite keys BEFORE the native core restores its best checkpoint. Final native-call results include finite-prediction/parameter flags AFTER checkpoint restoration. NaN/infinities are represented as strings plus finite flags, with strict JSON serialization.

The installed Lightning2.5.5 code has check_finite=True by default; any nonfinite monitored loss immediately requests stopping, independently of patience. With verbose=False its textual reason is not printed. This behavior was checked in source, but the suspected real fold still requires replay evidence.

Inputs: /workspace/cyp-repro/results/chemeleon_mae/own750/prepared (the completed nativeCheMrun), plus the existing verified /workspace/cyp-repro/assets/weights/chemeleon_mp.pt. Outputs: /workspace/cyp-repro/precision_diagnostic/{16_mixed,bf16_mixed}/report.json and audit.json, per-precision rootlogs, combined-report.json. Checkpoints and diagnostic validation predictions are retained for diagnosis ONLY, never candidates or submission assets.

CPU checks passed: wrapping leaves native finite/nonfinite stopping decisions and state transitions unchanged; NaN immediately stops with the native reason; epoch cap does not alter max_epochs, estimatedsteppingbatches or LR; output remains valid strictJSON. No GPU launched by helper.

Interpretation: a recorded native nonfinite stop establishes that issue for the replay. Four finite bf16 epochs only establish short-horizon numerical behavior, not convergence or superior scientific performance. A silent-stop hypothesis is not inferred solely from epoch0, duration, or a finite bestcheckpoint.
