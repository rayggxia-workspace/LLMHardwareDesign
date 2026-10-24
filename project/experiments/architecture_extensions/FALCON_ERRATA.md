# Falcon first-capture accounting correction — Issue 70

2026-10-24; Liangruizhi. Applies to the actual server job **90164**,
`capture-falcon03`, model revision `01087ec4c132d7f186908716b3530ea187f062a1`.
The first capture is retained as executed evidence, without rewriting its report,
manifest, NPZ arrays or hashes. This correction changes accounting/description;
it does not constitute another model run or numerical acceptance.

| Original evidence | Fixed identity |
| --- | --- |
| Capture source commit | `ac9d3f3d4785e3d855045744a8608d2b1885d643` |
| Original `falcon.py` SHA-256 | `4f99a449e21cb61e2225d33d2196f56ff94053f68176b6ea7ef863c2493cfd4c` |
| Original `report.json` SHA-256 | `21cff375f7ae430144ff139f9ae0e631ae02fa705ebf8eee53c11289d322e955` |
| Original `capture.npz` SHA-256 | `5aaf85fbc1f848325db3c9a2f1aba14b6d31b0f7f7b7825c5336123a46398a99` |
| Original `numeric.npz` SHA-256 | `5ad59f3d69edef2b49f1aa644021cf64e89a6a07a624fd3d5032f89a50ea926b` |
| Original `projection.npz` SHA-256 | `8441c718fcde748e124410c9d03d1339282a7c0bf6262f898b1af4a743617f4a` |

## Join inventory

The original `hybrid_branch_join_read_payload_per_layer_token_fp32=20480`
counts only the two hybrid branches and omits the residual. The actual equation
is `residual + (ssm_out_multiplier * R) + (attention_out_multiplier * A)`.
All three H2560 vectors must be supplied to the join: **30720B read**, plus
**10240B output write**, per layer/token at FP32. This is logical payload before
packet headers, alignment, unit descriptors, multicast/source reuse and port
service. The current source adds explicit read components and corrects the read
field to30720B. The original20480B is not a valid total join-read cost.

## Scale witness versus transfer

Both original projection rows report `activation_scale_bytes=576`: the NPZ
serializes a72x1 FP64 scale array for each scheme. For calibration-static tensor
scale those72 entries repeat one value. Its minimum unique parameter payload is
**8B**, while dynamic-per-row scale requires **576B for72 rows**. These minima
exclude resident/broadcast setup, packet/descriptor overhead and any conversion
to an eventual hardware scale format. They are not measured physical transfer.
The original scale values and codes remain unchanged. Current source retains the
legacy array-byte field, adds `serialized_activation_scale_metadata_bytes` and
`minimum_unique_activation_scale_parameter_bytes_fp64`, and states this boundary.

## Numerical and placement qualifications

- W8A8 measures16 selected raw input-projection outputs (gate/x/B/dt four each),
  complete K2560, **before MuP**. Independent FP64 recurrence/state-storage
  diagnostics instead use coefficients reconstructed from the **native FP32**
  projection after MuP and causal conv. They have not been connected into a
  W8A8→MuP→conv→state→gated-norm integer consumer chain. The observed S16/S32
  output errors near0.606% are not end-to-end W8A8 errors or application quality.
- Actual captured native states, conv/KV and branch tensors use FP32, converted
  from source BF16 weights. A transport experiment copying those tensors is an
  **FP32 COPY/port** experiment. Same four-byte width does not make that payload
  S32 integer computation. S32 codes are a separate head0 state-storage candidate
  with floating coefficients/updates; neither S16 nor S32 passed a no-saturation
  claim (both have4 saturation cells). Full32-head integer quality is untested.
- FP32/S32 SSM alone is4MiB/layer and128MiB for32 layers. The previous128MiB
  external backing inventory has no room left for conv (2.25MiB all layers),
  KV at72 tokens (4.5MiB), metadata, shadow or other state; **reject a full-model
  fit under that inventory**. One-layer/head transport may still be valid and
  must retain its selected-task scope. Model weights are an additional capacity
  obligation, not included in this state-only rejection.
- Head0 is128KiB at32bits and64KiB at16bits, both exceeding R32KiB. A D16 by
  complete N256 old/new S32 pair consumes32KiB before auxiliary data, unlike the
  earlier N128 case. Recheck D/N tiling, buffer and cross-N output reduction;
  the prior tile16 memory table is not portable unchanged.

Native chunk epoch/version labels remain analysis descriptors, not framework
epoch enforcement. The fixed scientific thresholds and independent reception
govern acceptance; this erratum does not relax thresholds or erase failures.
