# Issue32 Qwen quality repair

Companion to `gpu_model_evidence`, with the same pinned models and isolated GPU environment.
`protocol.json` freezes calibration, validation, alpha selection and numerical acceptance before held-out execution.
WikiText-2 raw comes from the pinned Salesforce/wikitext revision. Its dataset card is inconsistent: YAML lists CC BY-SA3.0/GFDL, while its licensing paragraph says CC BY-SA4.0. Preserve both facts; this task does not resolve the upstream license discrepancy. Source/card SHA and attribution are recorded; no full raw corpus is committed.
16 evenly spaced train sequences calibrate; 16 test sequences validate 4096 next tokens. The prior four authored sequences remain a separate 512-token regression group. This is an English diagnostic sample, not general multilingual acceptance.

Run `prepare_data.py --out D:/Data/llm-gpu32/datasets/wikitext2` first. Run `run.py --mode reference` and then `--mode w8`, `a8`, `raw`, `smooth` in independent model processes, using `--reference-dir` for each candidate. All require `--model-dir`, `--data-dir`, `--out` and a clean commit. Output paths must not exist. Default allocator cap9728MiB, no offload. Efficient SDPA only with explicit GQA repeat, no backend fallback.

W8 and A8 are isolated **fake quantization** ablations. Raw and smooth use actual INT8×INT8→INT32 CUDA matrices, independently checked with INT64 samples. SmoothQuant channel rescaling and per-layer alpha choices use only calibration rows; factors/selection SHA and freeze time precede validation. Scale, dequantization, bias, nonlinear, attention and state updates remain floating point, as listed in the protocol. No candidate timing is a hardware speed claim.

`results.json` streams each held-out sample's KL, NLL, NLL delta, top1 and finite checks. Per-sample and aggregate gates are distinct; one failure is not all-sample acceptance. `calibration-frozen.json`, `inputs.json`, source/model SHA and artifact index allow reproducibility. Full native logits/calibration rows stay outside Git. Candidate outputs retain only the first representative sequence; all errors are computed during execution.

CUDA arithmetic check: `python -m unittest discover -s project/experiments/gpu_model_repair -p test_repair.py -v`.
