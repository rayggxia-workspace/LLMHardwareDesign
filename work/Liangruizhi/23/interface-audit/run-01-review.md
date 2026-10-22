# Issue 23 real-weight run-01 independent archive audit

2026-10-22. **PASS within the evidence boundary below; no inconsistent archive, shape, byte-count, source-binding, or recorded-control result was found.** This audit read the completed real-weight run; it did not execute any model, import torch/Transformers, modify the run, or modify the repository.

Run: D:/Projects/Codex/qwen3-inference-20261022/results/run-01/

Source commit: d63bc2d37a5f1457a4a170b17afba343fb54998d.

Manifest SHA-256: 98bde36d3e45a4292331a65658610509b6a4e3e6d1d97e50a78e02f72ce879c7.

## What was independently checked

The standalone stdlib script audit_run01.py does not import or reuse the production event validator. It independently enumerates the semantic tensor shapes from the frozen model config, reads all gzip JSONL events, verifies every per-call/layer/stage key, recomputes numel/logical bytes, and checks that the recorded strides and offsets fit the recorded storage size.

| Check | Actual scope and result |
| --- | --- |
| Trace event coverage | 13,720 events = 35 calls × 28 layers × 14 stages; exact stage sets, no duplicate/missing layer or event |
| Schedules | Single prefill 32 + 16 one-token calls; chunked prefill 16+16 + 16 one-token calls |
| Causal masks | 980 layer/call bindings; independently reconstructed row-major FP32 masks from absolute causal positions and matched every actual mask SHA-256 and allowed-count vector |
| Selected boundary reports | 1,365 reports = 35 × 3 selected layers × 13 sampled stages; exact key sets and finite/pass records |
| Numeric positive records | 35 primary + 19 length-confirmation = 54; exact token ranges and both schedule paths |
| All-layer numerical cache records | 3,024 positive K/V field reports = 54 × 28 × 2; all shapes/dtypes/finite/match fields internally consistent |
| Prefix integrity records | 2,800 before/after hash pairs across nonempty positive prefixes; complete layer/field coverage and identical recorded hashes |
| Semantic negative controls | Four total: wrong decode RoPE position and swapped K/V heads, each at prefix 32 and 96; valid baselines, finite valid layouts, recorded divergence and mutation records consistent |
| Trace metadata negative controls | All three recorded as detected |
| Result artifacts | Rehashed all eight manifest-listed result files; no missing/unlisted artifact |
| Formal source | All six manifest source files independently extracted from the recorded Git commit and SHA-256 checked |
| Model input files | Actually rehashed all eight files, including the 1,503,300,328-byte weights; sizes and SHA-256 match committed experiment and manifest |
| Runtime code | Rehashed installed Qwen3 and cache source files and matched both frozen official source copies |
| Input token binding | Reconstructed little-endian int64 bytes from archived token IDs; full 104-token input and both per-case used-token hashes match |

The numeric runner hashes only the tokens each case actually uses: 48 for primary and 104 for length confirmation. Its source explicitly records supplied/used/ignored counts. The initial audit assumption that both numeric hashes covered all 104 tokens was corrected to that documented scope; this was not a run-data discrepancy.

Model/config identity remains Qwen/Qwen3-0.6B at revision c1899de289a04d12100db370d81485cdf75e47ca. The independent parameter formula gives 596,049,920 unique parameters. Counting the tied embedding again gives the reported 751,632,384 state-dict elements; the archive records shared embedding/lm_head storage. Runtime is CPU FP32/eager under torch 2.10.0+cpu and Transformers 4.57.6. Checkpoint BF16 metadata is not the execution precision.

## KV growth and the observed probability tensor

From actual K/V event shapes and bytes, the complete 28-layer cache grows by:

2 × 28 × 8 KV heads × 128 head_dim × 4 bytes = **229,376 bytes/token** (224 KiB/token).

At 32 tokens, recorded logical cache bytes are **7,340,032** (7 MiB); at 48 tokens they are **11,010,048** (10.5 MiB). Every call's independently summed K/V events match the trace's logical and storage-byte totals. The observation/reference/control caches are separate experiment objects; the single-cache value is not the process memory footprint.

Actual eager probability tensors have shape [1,16,Q,K] in FP32:

| Prefill call | Per-layer logical bytes | Sum over 28 layer events |
| --- | ---: | ---: |
| One call: Q=32, K=32 | 65,536 | 1,835,008 |
| Chunk 1: Q=16, K=16 | 16,384 | 458,752 |
| Chunk 2: Q=16, K=32 | 32,768 | 917,504 |
| Two chunks combined | 49,152 | 1,376,256 |

Thus the two chunks reduce this particular probability tensor's cumulative logical elements by 25% and its largest per-call tensor by 50%. The full prefill still has the same 528 causally allowed query/key pairs per head: the two chunks avoid computing some dense masked entries. Summing across sequential layers is an event sum, not simultaneous residency. These observations do not establish a 25% reduction in hardware traffic, runtime, energy, or total live memory.

## Recorded numerical evidence and controls

| Case | Positive comparisons | Maximum reported logits absolute error | Maximum reported cache absolute error |
| --- | ---: | ---: | ---: |
| Primary, 32+16 tokens | 35 | 2.47955322265625e-5 | 3.0517578125e-4 |
| Length confirmation, 96+8 tokens | 19 | 2.6464462280273438e-5 | 4.0435791015625e-4 |

The declared rule is elementwise abs(actual-reference) <= 1e-4 + 1e-4*abs(reference), so a maximum absolute error above 1e-4 alone is not a failure. All positive finite/layout/match and aggregate status fields are consistent with the runner's recorded PASS.

Across all 35 observed calls, the instrumentation/control logits report maximum difference **0**; all-layer K/V equality and cache-binding flags are true. The maximum selected-layer boundary error against fresh full-prefix reference is **3.509521484375e-4**. These are archived error reports, not recalculated raw tensor differences in this audit.

| Semantic negative | Prefix | Reported logits max absolute difference | Changed result fields |
| --- | ---: | ---: | ---: |
| Position forced to zero, correct cache position retained | 32 | 12.707403182983398 | 56 |
| K/V heads 0 and 1 swapped at layer 14 | 32 | 1.7408437728881836 | 29 |
| Position forced to zero, correct cache position retained | 96 | 9.345857620239258 | 56 |
| K/V heads 0 and 1 swapped at layer 14 | 96 | 1.1179194450378418 | 29 |

All four negatives have successful independent baseline records, finite outputs, valid cache shapes, a nonempty recomputed list of mismatching recorded fields, and preserved prefix hashes during the subsequent append. Each head-swap mutation changes exactly the recorded layer's two K/V prefix hashes before the append. Negative failure detection is therefore not explained by malformed/nonfinite tensors in the archived protocol.

## Reproduction and limits

Audit command: D:/APP/Python/python.exe -B D:/Projects/Codex/qwen3-inference-20261022/interface-audit/audit_run01.py

Machine result: run-01-audit-results.json, SHA-256 **9cf455b215e00287417c5353b835a0a92c2d8ecb9245fef0a3acc99ba8e736e3**. The script completed 130,211 structural/hash/closed-form assertions with zero failures; this count is bookkeeping, not 130,211 independent inference experiments.

The gzip contains metadata, and numeric JSON contains errors and digests, not full raw intermediate tensors/logits. This audit can independently recompute byte layouts, token/source hashes, and causal-mask hashes, but cannot recompute numerical errors or stored K/V prefix hashes from absent raw values. Their numerical provenance depends on the inspected, frozen implementation and recorded execution; a fresh model replay is separate work. The parent is conducting run-02; it was not used to establish this run-01 audit.

Likewise, the historical clean-worktree flags are runner records. The audit independently establishes that all six source hashes match the recorded Git commit, rather than claiming to reconstruct the past filesystem state. No external signature or independent trusted timestamp is implied.

All-layer metadata coverage does not mean every intermediate value at every token/layer was numerically compared. Boundary snapshots cover the final token at layers 0/13/27; cache and logits checks have their separate scopes. Teacher-forced equivalence does not prove free-running generation identity, model quality, a physically realizable Block partition, hardware performance, or a hardware optimum.
