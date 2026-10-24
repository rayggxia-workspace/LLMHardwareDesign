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

Both original projection rows report `activation_scale_bytes=576`, computed as
`scale.size*8` rather than `scale.nbytes`. **This legacy field is wrong for the
dynamic scheme and is deprecated.** Actual array formats are:

| Scheme | Actual scale array | Scale element payload (`nbytes`) | Native parameter payload | If explicitly stored as FP64 |
| --- | --- | --- | --- | --- |
| Calibration-static tensor | float64,72x1 | 576B | One shared scalar:8B | 8B shared parameter |
| Dynamic-per-row | float32,72x1 | **288B** | 72 row parameters:288B | 72 parameters:576B |

The dynamic calculation retains the native FP32 activation dtype; reading an
input witness later as FP64 does not retroactively make its scale calculation
or stored array FP64. A previous version of this erratum repeated the incorrect
FP64 assumption; this table corrects that description without changing evidence.
Array payload sizes exclude NPY headers and ZIP compression/container overhead;
they do not describe the total NPZ file or compressed member size.

The parameter payloads assume one global static scalar or one value per dynamic
row, before broadcast/resident setup, descriptors, packets, physical packing,
ports or equality compression. Hardware scale format is **not determined**.
The conditional FP64 column requires an explicit representation/conversion
contract and its cost; it does not describe the actual dynamic NPZ array.
The original scale values, arithmetic, codes and hashes remain unchanged.

Current source reads actual `scale.dtype`/`scale.nbytes` and exposes
`activation_scale_metadata_dtype`, `serialized_activation_scale_metadata_bytes`
and `activation_scale_parameter_payload_bytes_native`. It removes the ambiguous
`activation_scale_bytes` field; the old assumption is retained only under the
explicitly deprecated name `legacy_activation_scale_bytes_assuming_fp64_deprecated`.
The optional FP64 representation is separately named
`candidate_activation_scale_parameter_payload_bytes_if_explicit_fp64`.

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
