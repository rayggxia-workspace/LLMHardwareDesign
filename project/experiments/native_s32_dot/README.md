# Native exact S32 dot candidate — Refs #252

This is an explicit new functional compute resource in the P/M capability
family. It is not free LC arithmetic. First candidate: four signed32 lanes,
eight80-bit carry-save accumulators, full-K one final RNE and S32 saturation.
Each32×32 multiply is pipelined through signed16/unsigned16 partial products.
Final carry propagation is split into40-bit halves. Persistent S remains
16KiB. Core payload, metadata and gates must all be mapped and counted.

The current core is not a physical macro or a deployed service. The single
real S128 frontend, finite source owners, final two S write ACKs, serialized
control binding, actual source DDR/KV loads and physical300MHz acceptance
are required before capability registration. Internal core ports are not
new arbitrary M10 hard-block edges. Full vector/RTL/physical/system coverage
will be reported independently.

`oracle.py` uses independent Python integers and final ties-to-even rounding.
`reference/` preserves12 real PR220 Qwen2.5-3B first-attention QK/AV witnesses
and source hashes from PR251/Slurm102326. They are B1/S2/noKV evidence, not
decode512, new W8 model quality or integer KV qualification. Signed extrema,
K65535, overflow, ties, held responses, pending cancel and inflight reset are
tested separately. All numerical/RTL/EDA work runs on Slurm6×10; local tools
only freeze source, submit and audit recovered receipts.

The exact15-pass reference in PR251 remains immutable. Its real full N8
K128 QK/AV layouts cost1256 cycles per partial at BEGIN-first-flit→raw,
plus owner/merge/staging/program/result costs. Comparing this hardware with
the new functional resource is hardware co-design, not the20% pure DP target.

The first core candidate is frozen at `c6ee957731b484ca6ece829ab207710e63f39b20`.
Slurm102355 passed six seeds × three register initial states. Each seed had
68,293 accepted commands,68,291 responses and two explicitly reset-flushed
commands; held output and pending cancel were exercised. These are core-only
results, with no S or system throughput qualification. The earlier strict
build failure102349 is preserved. It rejected width/bench initialization
warnings; the successful version fixes those warnings without disabling them.

`work/YUZE-LU/252/run-02/` contains the exact source archive, SHA-indexed raw
vectors/build logs/RTL receipts split into blobs of at most1MiB, and an
independent offline audit. Run `python project/experiments/native_s32_dot/audit.py
--run work/YUZE-LU/252/run-02` to check every frozen source/member hash,
all18 conservation/held/cancel receipts, actual vector hashes and CPU
allocation. `run-01` audits the preserved expected build failure. The scripts
do not rerun simulation or numerics on the local computer/login node.
