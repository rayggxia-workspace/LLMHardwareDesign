# Integer RMSNorm candidate after the complete-hidden consumer sums

This is a new frozen candidate. It does not rewrite the existing FP32 norm
evidence. Inputs are accepted capture gamma plus the eight saved consumer
`sum_acc64/sum_units` arrays; no down/model execution is repeated. Each
full2560-channel row aligns to its finest unit using checked I64, dynamically
RNE-encodes to symmetric X16 with near-full magnitude, then forms a U64 square
sum. Its new X16 error is reported separately from the normalization error.

Offline constants: epsilon1e-6 -> U64Q40; sqrtH -> U32Q20; effective gamma
FP32(1+stored weight) -> S32Q20. Decimal60 checks epsilon/sqrtH, Fraction checks
gamma. The runtime candidate has no float conversion: Den=(Z<<16)+rounded
epsilon term is checked U64; actual32-step restoring integer sqrt agrees with
math.isqrt; actual64-step U64/U32 restoring division/RNE agrees with Fraction.
InverseQ30, signed16xU32, normQ20 and signed32xgammaQ20 have explicit checked
range/rounding. Every pre/post-gamma norm value and fresh A8 code has a Fraction
oracle. Fresh A8K128 consumes integer S32Q20 directly, never `encode_rows` or a
FP32 round trip. The next selected16 projection reuses the same fixed W8K128.

Zero rows return zero. Nonzero tiny rows whose epsilon shift/Den cannot fit
the frozen domain are saved as failures; parameters are not silently clamped
or retuned. Sqrt/divider, 15/25 S8-product wide-multiply alternatives,
shift/add/RNE, gamma and state buffers/1RW traffic are explicit candidates;
there is no claim of existing hardware, target clock/cycles, PPA or complete
integer model. Root scheduling uses new immutable server outputs and two
independent rounds. Only synthetic tests run locally.

```text
python -B -m unittest discover -s project/experiments/scale_state -p test_norm.py -v
python -B project/experiments/scale_state/norm.py --capture <capture01> --consumer <consumer01> --out <new-norm01> --binding <norm-binding.json>
```

Binding contains commit, norm_sha256 and consumer_sha256. Source/dependency,
capture/consumer manifests, environment and every artifact SHA are recorded.
Compare integer norm to both the old same-input FP32 norm and FP32 norm on
the newly recoded X16; compare next projection to the old chain and native
selected16 outputs. Passing these short local diagnostics is not application
quality or the complete8192-output GDN. No model weights are downloaded.
