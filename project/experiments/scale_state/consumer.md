# Issue66: complete-hidden consumer chain

This module reuses the authorized Qwen3.5-4B checkpoint and one bounded native
capture. No model download, GPU timing or remote scheduling is performed by
the program. The root task schedules immutable source/input-bound CPU jobs.
Phi remains reserved and is rejected as input.

The actual chain is layer3 MLP down -> residual -> layer4 input RMSNorm ->
layer4 linear-attention `in_proj_qkv[:16]`. Down/residual/norm cover **all2560
hidden channels**. The next projection covers its first16 of8192 outputs,
the beginning of the Q branch; it does not validate the whole projection/GDN.

## Captured input contract

`--input` contains `manifest.json` and indexed `consumer-raw.npz`. The manifest
records accepted native capture, exact checkpoint revision, source/framework
hashes, original token IDs and deterministic positions, model-file hashes,
and artifact size/SHA. `chain` identifies layers3/4, no biases and epsilon1e-6.
Every indexed artifact is checksum-verified, including associated captures;
all indexed files must therefore be present on the server intake.

The NPZ has FP32 `weight.down[2560,9216]`,
`weight.next_norm[2560]` (stored raw weight, effective gamma=1+weight), and
`weight.next_projection[16,2560]`. For `calibration`, `prefill`, `decode`,
save `A[R,9216]`, `down/residual/sum/norm[R,2560]`,
`projection[R,16]`, and integer absolute `rows[R]`, prefixed by the case name
and a dot. R is16/8/32. Calibration selects first8/last8 of its own128token
prefix; evaluation prefill selects first4/last4, cached decode preserves32
successive real tokens. Residual is the **unnormalized** input to layer3's
post-attention RMSNorm. `sum` and `norm` are the real input/output of layer4's
input RMSNorm. No sixteen-channel slice can substitute for the full norm.

Native chain reconstruction is checked before any candidate: FP32 down,
residual sum, complete RMSNorm, selected next projection. Frozen tolerance is
relative L2<=1e-5 and maximum absolute error<=2e-3 per stage. This accommodates
independent FP32 reductions, not a quantization quality budget.

## Frozen candidates and integer boundaries

The same full down W8K128 and dynamically encoded A8K128 feed every variant.
S8 group dots execute as I32, all partial values match a separate I64 matmul;
mixed-unit complete sums use a checked I64/spread35 contract with independent
arbitrary-integer witnesses. No partial-group RQ occurs. W/Y offline compilers
use FP64 and endpoint Fraction checks; not every original W float gets a
Fraction check. Calibration Y is per-output twice the maximum magnitude.

The four outputs are static ACT8; ACT16 with exactly the same physical
endpoints (step/256, codes[-32768,32512]); per-row/per16-output-tile delta ACT8;
and that delta ACT8 explicitly converted to shared K128 units. Delta searches
[-16,16] using integer accumulators and base exponents, never evaluation Y.
Zero tiles use delta0. Every output code is independently checked by Fraction.
The per-output base exponents may differ **within** one16-output tile: a
single delta is not a complete common scale. The K128 arm aligns the actual
per-channel units, scans a checked wide maximum and RNE re-encodes to symmetric
S8. It saves all original and converted codes/units and its extra error.

Residual FP32 crosses a checked S32Q20 bridge. Each actual outlet channel and
the residual align to min(outlet_unit,-20), using checked I64 operands/adds.
All residual sums match an independent Fraction reference. Only then is the
complete row converted to FP32 for RMSNorm: FP32 square, full-hidden FP32 mean,
epsilon, sqrt/reciprocal, and effective(1+weight) scaling. **This norm remains
floating point**, with no integer-hardware support claim. Its output crosses
S32Q20 and is freshly quantized to A8K128 for the same next W8K128 matrix.
Consequently, ACT16 before norm does not by itself require3x products in the
next matrix: its input format was explicitly replaced. Norm conversion,
arithmetic, gamma streaming, extra reads and future integer implementation
remain costs/limitations.

Errors separate upstream down before outlet RQ, outlet/transport, residual,
norm, next projection, fixed-native-norm W8A8 reference, and a no-outlet-RQ
reference. These are paired diagnostics on the newly frozen short capture,
not a new independent quality acceptance or a rewrite of older failed gates.

## Outputs, costs and reproducibility

`common.npz` saves fixed full-hidden integer down and selected-next weights,
all down partials/units/accumulators, native references and two oracle chains.
Each of eight case/profile NPZs preserves outlet/transport codes and units,
delta/K128 units, residual codes, exact sum, explicit FP32 bridges, and complete
next-projection integer intermediates. `consumer.json` has8 metric/cost rows;
manifest binds exact input/source/environment and every output size/SHA.
Fraction and I64 checks are counted separately; they are not an independent
re-run of the native full model.

Costs show whole-row and16-output-tile packet alternatives, static base versus
dynamic metadata, actual16bit widths, scan/align/RNE work, 128bit1RW read/write
lower bounds and finite buffers. For H2560, exact S64 sums+I16 units take25.6KB
per row, exceeding V16KiB; a single in-place FP32 row is10.24KB but row+FP32
gamma is20.48KB. A legal schedule must stream/spill/re-read, not silently add
RAM. Full down W8 and metadata also require backing/tiling; a per16-output
working set is distinguished from the full layer. No bank lower bound or
packet difference is called a scheduled cycle/PPA improvement.

Run only within the root task's existing allocation after checking current
member jobs. Use a new output directory for each independent round:

```text
python -B -m unittest discover -s project/experiments/scale_state -p 'test_consumer*.py' -v
python -B project/experiments/scale_state/consumer.py --input <accepted-capture> --out <new-output> --binding <binding.json>
```

Binding has `commit` and `consumer_sha256`. The module is self-contained
(Python/NumPy only). Formal clean source is frozen before the root submits
two server rounds. All scientific NPZ/JSON should be byte-identical between
rounds; manifest includes real runtime/environment and may differ. Preserve
failed logs and outputs, never overwrite a prior run. Full weights/large
captures remain authorized-server artifacts, with repository indices/SHA.
