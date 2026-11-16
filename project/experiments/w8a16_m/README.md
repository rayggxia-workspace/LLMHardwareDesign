# W8A16/S32 group arithmetic candidate

Refs #250. This prepares new active logic; it does not change the qualified main M, inherit its physical acceptance, or claim full-model integer execution. New RTL is in `project/rtl/w8a16_v1/`.

`m_group_s32` accepts sixteen A16 values and eight columns of sixteen signed W8 values per beat. Contiguous groups have K=16 or128, up to eight output lanes, with explicit tag/offset/first/last. Eight S32 raw accumulators hold **one current group**, not sixteen projection contexts. The multiplier and reduction pipeline accepts one beat per cycle when unstalled; the response persists until accepted. A malformed beat returns an error without changing the current valid group. Reset discards live raw state and pending responses; system-level cancellation still needs coordinated owners/epochs.

`scale_group_s32` independently converts a group dot with positive finite nonzero FP16 weight scale. The A input is normalized from S32/Q16 with shift0–17. The exact scaled term is RNE to Q16, added to previous S32 state; final bias is S32/Q16. Every group term and accumulated prefix must fit S32. A 44-bit temporary product and range-before-left-shift avoid persistent S64/S128 or an oversized exact common-exponent accumulator. Any active lane error rejects and zeros the whole packet. This one-entry arithmetic response does **not** implement projection context allocation, generation, memory load/write ACK or native-controller lowering.

Projection state (16×8×4=512 B/P), A slots, weight banks, tags/metadata, input/output ownership and actual SRAM adapters remain separate resources. Existing single-M data formats and contexts cannot be relabelled as this interface. Assembly into an independently routed new M may internalize the raw/scale boundary; final macro pins must be inventoried from that real top.

## Unit verification

`check.py` uses exact Python integers for dot products and `fractions.Fraction`/Python round for FP16 scale/RNE expectations. RTL and oracle do not share the shift/remainder implementation. Six seeds exercise signed extrema, head/group128, inactive lanes, RNE ties, subnormal/invalid FP16, prefix/bias overflow, partial beats, wrong offsets, rejected-command retries, output backpressure and reset of live/pending state.

Run on Slurm, not the workstation/login node:

```sh
python -B project/experiments/w8a16_m/deploy.py \
  --root /public/home/yuzelu/project-circuit/issue250-m-s32-YYYYMMDD-NN \
  --package-dir /an/unused/local/package/path
```

The real root must have numeric date/attempt fields. The script freezes committed Git bytes with LF, hashes every input, refuses an existing remote root, and submits c64 six tasks×ten CPUs. Verilator builds use ten jobs; each unit simulation is single-threaded. Testbench-only BLKSEQ and cross-module TIMESCALEMOD warnings are scoped out; width warnings remain fatal.

Collected results and failure history: [unit evidence](../../../work/YUZE-LU/250/m/README.md). The receipt auditor is an offline source/hash/log check, not a replacement for simulation:

```sh
python -B project/experiments/w8a16_m/audit_receipts.py --root work/YUZE-LU/250/m
```

Not yet verified: actual checkpoint/byte packing vectors, projection context/controller integration, joint A/B service, meaningful end-to-end RTL throughput, synthesis/area/energy, M10 escape, native DRC/300MHz and final-netlist programs. The SystemC performance gate remains independent; unit correctness does not prove it.
