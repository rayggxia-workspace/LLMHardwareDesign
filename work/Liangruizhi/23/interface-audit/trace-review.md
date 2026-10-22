# Issue 23 Qwen3 trace independent implementation review

Review date: 2026-10-22. Reviewer: independent interface-audit agent supporting Liangruizhi. Scope: read-only review of `project/experiments/qwen3_trace/{trace.py,run.py,experiment.json}` and the numeric result interface. No root-tree modifications, package installation, model execution, or GitHub mutations were performed by this reviewer.

**Disposition: no remaining must-fix issue found in the reviewed snapshot.** This is an implementation/API and protocol review before the formal real-weight run, not a claim that the real-weight experiment has passed.

## Reviewed versions

| File | SHA-256 |
| --- | --- |
| trace.py | `73bcd9d3adefa72ce96f2b4dcc0eceada63569840a736d64bc8d1894abe6b88d` |
| run.py | `f2456ad4aa834177f4c0ce4df9c986bc3a6a950e359e6b9430f30b48a9457849` |
| experiment.json | `6aa8da27a8d85374c84a592365df2597acf6b20d3d979fac1bed000559913482` |
| numeric.py, result/API compatibility only | `3c86fc20cc8027dd374f79a79e104eb15f1830ff2d2baf7dd6d2820c2c6c8d01` |

The worktree was still being prepared on `task/23-qwen3-trace`, with pre-freeze HEAD `adf077d04a5f0a3cc2ae13b77f16371bb637591d`. These file hashes identify the reviewed changes; that existing commit alone does not identify them. `run.py` refuses a dirty worktree and records the later formal source commit and per-file hashes. It checks commit, worktree state, source hashes, and model file hashes again at the end.

Official API evidence is frozen in the adjacent `source-manifest.json` and `qwen3-capture-api.md`: Transformers tag v4.57.6 resolves to commit `753d61104116eefc8ffc977327b441ee0c8d599f`. The runner checks the installed `modeling_qwen3.py` and `cache_utils.py` SHA-256 against those reviewed files. Model revision is `Qwen/Qwen3-0.6B@c1899de289a04d12100db370d81485cdf75e47ca`.

## Findings resolved before this disposition

1. **Model revision binding.** The earlier runner pinned only weight bytes; locally changed config or tokenizer bytes could retain the official-revision label. Current `experiment.json.model_files` freezes all eight input artifacts and `run.py` requires exact size/SHA equality before loading. This review independently checked all eight entries against the fixed-revision download receipt, including matching model/revision fields. The receipt records upstream Git blob or LFS metadata. This review did not redownload the files or rehash the 1.5 GB weights; the runner performs its own actual input hashes before and after execution. Actual loaded architecture, eager backend, full-attention layers, and CPU FP32 parameters are asserted.
2. **Numeric status interface.** The earlier numeric result used lower-case status strings while `run.py` required `PASS`. The reviewed numeric module now emits `PASS`/`FAIL`; the runner asserts that enumeration before aggregating results.

## Capture and API checks

- The temporarily wrapped official eager function receives the actual Q **after head RMSNorm and RoPE**, and actual K/V **after DynamicCache.update**. It forwards the original arguments and returns the original output unchanged. K/V values are compared with `cache.layers[layer].keys/values`; shared data pointers are recorded separately. Projection outputs are explicitly labelled before normalization/RoPE and are not substituted for cached K.
- v4.57.6 supports `logits_to_keep=1`. It slices hidden states only before `lm_head`; attention and KV computations still cover every input token. `attention.context_before_o_proj` is `[B,Q,Hq,d]`, while raw Q projection width is `Hq*d=2048`, even though residual hidden width is 1024. Decoder layers return tensors. The down-projection prehook receives the actual SwiGLU product through its positional first argument.
- `audit_events` requires exactly 14 stage labels for every one of 28 layers, rejects duplicates/unknown or missing stages, and checks semantic shape, FP32 dtype, item size, numel, and logical bytes. All layers are instrumented; selected layers control value snapshots only. The declared primary schedule implies 35 calls and 13,720 events; these are expected counts, not observed real-weight results at review time.
- The observed cache, unobserved control cache, and each fresh full-prefix reference cache are separate objects. The observation context restores the global eager function and removes registered module hooks in `finally`, including exceptional exits. The per-observer nesting guard is not a process-wide concurrency lock; the documented single-threaded, nonconcurrent use is required. Importing/running another model while the global wrapper is active is outside the contract.
- The wrapper inspects the actual additive mask and records its SHA-256 and allowed counts. For this batch-one, unpadded, full-attention workload, allowed positions are independently compared with absolute causal positions; disallowed entries must be strongly negative. A missing mask is accepted only for a one-token query whose complete existing cache is visible. No replacement mask is supplied to the arithmetic.

## Independent protocol checks actually executed

Command: `D:/APP/Python/python.exe -B D:/Projects/Codex/qwen3-inference-20261022/interface-audit/audit_trace_contract.py`.

The script extracts only the reviewed pure-Python `audit_events` function through AST, imports no torch/Transformers, and creates synthetic metadata independently from the published architecture. Three query/total lengths `(32,32)`, `(16,32)`, `(1,48)` cover prefill, continued prefill, and decode schemas.

Results: **3 normal schemas accepted; 27 mutations rejected; 8 frozen file entries matched the download receipt.** For each shape, rejected cases were one missing event, an entire missing layer, duplicate event, wrong GQA head count with self-consistent numel/bytes, raw-projection axes labelled as post-RoPE K with unchanged total elements, wrong dtype with internally consistent bytes, wrong byte count, unknown stage, and out-of-range layer. The self-consistent mutations ensure rejection is not solely due to mismatched bookkeeping.

Machine record: `trace-contract-results.json`, SHA-256 `78f4de5a4f77c46562509c640a78288adc9d58fd3740bfac8e75462930819248`. Script: `audit_trace_contract.py`. These are protocol tests, not synthetic numerical inference or real-weight evidence. The parent separately reported random miniature-model integration and exceptional cleanup tests; this reviewer did not execute those tests.

## Evidence boundaries to retain in formal reporting

All-layer coverage applies to **metadata** and instrumentation cache comparisons. Full-prefix boundary values cover the final token at layers 0/13/27, with 13 sampled stages per selected layer; probabilities are metadata-only. This does not establish all intermediate values at all tokens/layers. The separate numeric runner supplies full-cache comparisons under its own protocol.

Instrumentation logits are checked within declared tolerance. Cache comparisons in `trace.py` use `torch.equal`, which is numeric element equality and should not be described as bytewise hashing; numeric prefix integrity is a separate raw-byte hash test. Teacher-forced token replay does not establish free-running generation identity or model quality.

Per-event logical bytes, underlying storage size, stride, and offset describe observed tensors. Summing those event records does not measure unique resident memory, physical hardware traffic, energy, chip speed, or an optimal partition. Python hooks and copies change execution cost. Formal evidence still requires the clean-commit real-weight run and its manifest/results; this review alone cannot establish that run's success.
