# Qwen3.5 K32 refinement

K128 passed the fresh4096-token WikiText validation but retained one old authored KL failure. This fixed K32 candidate increases scale overhead to12.5% and evaluates4096 **new** prediction tokens. The sampler excludes every source row used by the K128 validation and records the excluded ranges, then selects16 mutually disjoint windows. Original four authored sequences remain regression. No thresholds are changed.

Shares the actual grouped INT8→INT32 kernel and independent INT64 checks with `gpu_grouped_repair`; uses `--mode reference` then `--mode raw`. Protocol and sampler are committed before these new validation windows execute. FP32 partial reduction, scales and all non-matrix paths remain explicitly floating point. This is a project precision proposal, not an approved final contract.
