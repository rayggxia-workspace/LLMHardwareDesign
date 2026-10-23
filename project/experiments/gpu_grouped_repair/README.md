# Fixed K128 matrix precision proposal

This candidate responds to activation outliers observed during prior development. It freezes K128 per-token activation and per-output weight scales before evaluating a **fresh WikiText validation split**, distinct from the train calibration and previously used test split. Original four authored sequences remain regression. Thresholds are unchanged. No threshold tuning or native exclusions are used to force a pass.

Every covered projection/FFN matrix uses actual INT8×INT8→INT32 partial GEMMs, one per K128 group. Dequantization and summing partial products are FP32, output FP16. Embedding/lm_head/convolution, attention/gates/nonlinear/state remain floating point. This is a candidate format requiring project review; it is not an end-to-end integer hardware implementation. Per-group scale storage and partial reduction/traffic must be budgeted.

Use shared CLI `--mode reference` then `--mode raw --reference-dir <native>`; the manifest protocol/version identifies this grouped method. Physical dataset manifest maps official `validation-00000-of-00001.parquet` to the shared runner's logical `test` key/file, retaining the original source path/SHA. No raw text is committed. The pinned dataset card lists CC BY-SA3.0/GFDL in YAML but CC BY-SA4.0 in prose; both are recorded and the upstream discrepancy remains unresolved.

All runs are observed quality measurements, never performance benchmarks. Full native logits stay in task-local storage with SHA index.
