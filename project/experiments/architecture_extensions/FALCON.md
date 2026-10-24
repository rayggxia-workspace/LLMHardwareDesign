# Falcon-H1 bounded hybrid experiment — Issue 70

This protocol adds a distinct parallel Attention/Mamba-2 workload. It is not a
GDN implementation and does not prove the Qwen3.5 integer state contract transfers.
The official 3B configuration has H2560, 32 hybrid layers, attention 10Q/2KV heads
of width128; Mamba has 32 heads, width128, state256 and one shared B/C group.

## Decisions and minimal measurements

1. **R state ownership/capacity.** FP32 SSM is 4MiB per layer,128MiB across32
   layers, before conv/KV/metadata. One complete head is128KiB. Therefore retain
   an explicit backing/tile/owner contract; a32KiB R scratch cannot silently hold
   even one complete FP32 head. Actual trajectories and separate-calibration
   S16/S32 state-storage candidates test whether width changes that conclusion.
2. **A/R parallelism and V join.** Both branches consume the same normalized
   hidden vector and join after their configured MuP multipliers. Capture true
   branch outputs, residual and next-norm input; account fanout, two join reads,
   output write, distinct growing KV and fixed conv/SSM state. Sequential CPU
   execution is not a hardware concurrency or PPA result.
3. **Matrix/scale boundary.** One true Mamba input projection, complete K2560,
   first16 outputs; W8 per-output, A8 calibration-static versus dynamic-per-row,
   signed symmetric[-127,127], RNE, INT32 checked before cast. Dequantization and
   scale handling remain floating references. Do not quantize only K slices and
   claim the complete dot product passed.

Run only `B1,pre64,cached-decode8`; calibration16 uses disjoint fixed random token
IDs. These are deterministic structural diagnostics, not text or model quality.
Capture layer0 complete hybrid branches and full KV/conv/SSM final state. Replay
the same real layer0 inputs in native chunks1/8/16 with continuous DynamicCache;
retain a deliberate reset-every8 negative. No all-layer attention matrices.

## Numerical boundary

Independent NumPy FP64 reconstructs depthwise causal conv plus SiLU and computes
`dt=clip(softplus(raw_dt+dt_bias), limits)`, `a=exp(-exp(A_log)*dt)`.
For one complete head0 D128xN256:

```
S_t = a_t * S_(t-1) + (dt_t * B_t[None,:]) * x_t[:,None]
y_t = S_t @ C_t + D * x_t
```

B/C are the entire shared group; the other31 heads use that group but have their
own dt/A/x/state. Full-layer initial zero/final states and native head0 tokenwise
states are retained. Group sharing is not an extra cross-head state reduction.
Gate/RMSNorm/output projection stay native FP32; the independent FP64 recurrence
checks the pre-gate/pre-norm state/output only.

S16/S32 candidates use one power-of-two unit per head, frozen from calibration16
state maximum alone: `2^ceil(log2(max_abs/(2^(bits-1)-1)))`. Each step reconstructs
the prior quantized state, performs the stated FP64 update, RNE and signed-width
saturation. These are **integer state storage with floating coefficient/update
bridges**, not integer recurrence or W8A8 hardware qualification. Record every
step saturation, output/final-state error and complete codes. No eval-fitted scale,
adaptive range claim, cycle/throughput claim or implicit free wide multiplication.

## CLI / evidence

```
python -B project/experiments/architecture_extensions/falcon.py \
  --weights /authorized/read-only/model --revision FIXED_COMMIT \
  --binding SOURCE_BINDING.json --out NEW_DIRECTORY --threads 8
```

`out` must not exist. Runtime uses offline local files, FP32 CPU/eager, no external
kernels or package/environment changes. Record downloaded safetensors header
dtypes separately from converted execution dtype. Source binding, actual modeling
and cache source SHA, environment, exact token arrays and all output SHA are saved.
`capture.npz` holds real branches/cache; `numeric.npz` holds coefficients, native
states, FP64 reference and state-storage candidates; `projection.npz` holds complete
K inputs/weights/codes/scales/INT32 accumulators. `manifest.json` binds every file.

Official references: [model config](https://huggingface.co/tiiuae/Falcon-H1-3B-Instruct/blob/main/config.json),
[Falcon-H1](https://github.com/tiiuae/Falcon-H1), and the installed Transformers
5.20.2 implementation, whose exact SHA is saved by the actual server execution.
The current installed version supplies CPU fallback conv/scan and explicit prior
state; no older local implementation is substituted.

Tests: `python -B -m unittest discover -s project/experiments/architecture_extensions -p test_falcon.py`.
They exercise scalar recurrence, RNE/saturation, chunk/reset/epoch/unit/position
errors, causal prefix, complete-K INT32 and bit-specific capacity accounting.
They are boundary tests, not actual model execution or hardware tests.
