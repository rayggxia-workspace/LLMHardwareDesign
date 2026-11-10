# Exact dynamic S32 dot provider candidate — Refs #250

This independent provider will feed the existing signed A16/W8 M through
registered pack/merge services. It does not change the M implementation.

The contracted result is `sat_s32(RNE(sum_full_K(A32*B32), shift))`, with only
one rounding after full K, as in PR220 `wide_program.execute` Dot and PR248
`native_s32_oracle.dynamic_terms`. Static W8 group-scaled prefix arithmetic is
a different profile. No per-K128 RNE is introduced into dynamic attention.

Split A as radix 2^15 digits `(A&32767, (A>>15)&32767, A>>30)` and B as radix
2^7 digits `(B&127, ..., (B>>21)&127, B>>28)`. The three A digits fit signed16;
the five B digits fit signed8, including INT_MIN/MAX. Each K128 chunk therefore
requires fifteen signed partial dots. Low unsigned16/unsigned8 digits cannot
be sent to signed M ports as if they were signed values.

Each raw partial fits S32. Scale FP16 1.0, A_shift 0, previous/bias 0 preserves
that integer exactly; this arithmetic identity still needs actual M/scale RTL
qualification in the independent provider test. Up to K=65535, an 80-bit lane
holds every signed-digit absolute-prefix triangle bound. Eight lanes use **80
bytes of transient accumulator registers**, with no new SRAM or wider
persistent state. Packer holding registers, control state, output hold and
all actual S128 reads/ACKs must be counted separately before area acceptance.

`oracle.py` supplies an independent Python integer/Fraction proof, saturation,
ties, full-K and extrema cases. `extract_checkpoint.py` reads frozen PR220 real
Qwen2.5-3B B1/S2/no-KV integer first-attention operands and preserves source and
program hashes. This is a model slice witness, **not** decode512, new W8 whole
model quality, RTL, full system timing or physical qualification. PR249's
attention/normalization quality screen remained float, so it supplies no
substitute integer-KV qualification.

Runs are frozen from committed canonical bytes by `stage.py` and executed by
Slurm c64 6×10; no simulation or numerical experiment runs locally/login.
The candidate must pass arithmetic, real S128 packing/ownership/backpressure,
existing M raw/scale and full-K merge RTL before physical/timing registration.

`dynamic_s32_weight_source` is an explicit `LOCAL_S_PACK64` source binding,
separate from DDR. It returns the full native17-beat W-first record through
the existing64B return interface only after actual local S reads. Binding,
64B address alignment, private16KiB bounds, tails, true returns, held offered
request cancellation, partial CLOSE/drain and quarantine/reset have dedicated
real-S tests. Typed fabric routing, A delivery and the complete LC scope are
still separate implementation work; no source-independent DDR credit shortcut
or complete-product qualification is inferred from component tests. Current
source and all failed/pass evidence are indexed in
`work/YUZE-LU/250/dynamic-s32/RESULTS.md`.
