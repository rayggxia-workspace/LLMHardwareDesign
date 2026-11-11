# Issue247 / PR243: R2 stateless relative EXP RTL

This isolated delivery changes four synthesizable modules. The parent agent
owns production integration, source commit, remote execution and reports.
R1's actual calibration and model runs are run16/101835 and run17/101838.
R1 files and results are frozen; this directory does not overwrite them.

## Interface

All four modules add `parameter integer NEXP_DIRECT=0`:

| Module | Opt-in behavior |
| --- | --- |
| `block_v2_n` | Admit reserved opcode12 for stateless relative EXP |
| `nexp_batch_adapter` | Replace R1's four native commands with one opcode12 |
| `pu_nexp_shared` | Forward the parameter; retain capture, packing and ownership |
| `pu_u_group` | Enable native opcode12 only when both NEXP_BATCH and NEXP_DIRECT are nonzero |

Both parameters default to zero in U. With `NEXP_BATCH=1,NEXP_DIRECT=0`,
R1's four-command destructive/clobber ABI is retained. `NEXP_BATCH=0`
does not enable native opcode12 even if NEXP_DIRECT is nonzero. A standalone
native N may explicitly enable NEXP_DIRECT without the U wrapper.

Native opcode12 requires count1..8, param0, aux0 and zero in every unused
complete S16 input lane. It accepts every signed16 value in used lanes.
Invalid descriptors produce the existing error response, without entering
CALC. Parameter0 retains the original reserved-opcode error behavior.

Each used output lane is the existing native `exponential(signext16(x))`.
The function returns32768 for nonnegative inputs, so this is exactly R1's
`exp(x-max(x,0)) = exp(min(x,0))`, using the same lookup, interpolation and
rounding. Outputs are unsigned16 bit patterns; unused lanes are zero.
There is no approximation change and no new exponential function or table.

The outer U opcode15 contract remains unchanged: NEXP/0x4e455850 supports
count1..8 packed16; NX32/0x4e583332 supports count1..4 S32 containers with
signed-low16 extraction and unsigned16-to-S32 zero extension. Used S32 high
halves remain ignored; unused complete S32 lanes must be zero. Existing
source-count, address, direct-route and payload rejection rules remain.

## Persistent state and ownership

Opcode12 does not require, read for its result, or modify the statistics,
normalization, replay or top-selection session. In particular it does not
update context_valid, statistics_final, factor_valid, mode, epsilon,
factor, exp_sum, count, exp_count, replayed, sum, sumsq, maximum, minimum,
top_id/top_score, selected, top_count, scan_index, best_index, top_k,
top_round, top_loading, best_valid/value/id, or chosen.

It reuses transient command, pair-compute and result registers. In ACCUM,
only legacy operation3 may update exp_sum/exp_count; operation12 only
assembles its result. No group-unit divide/root command is started.
The same N remains exclusively owned until response retirement; no second
N and no concurrent ordinary execution are introduced. Reset and held
response handling follow the existing service/router paths.

Thus R2 direct-mode batches may be inserted between completed commands in
a normal session without destroying that session. R1 mode remains
explicitly destructive. This distinction must be checked by continuation
tests as well as register snapshots. In-flight commands still cannot be
interleaved; the command/response handshake enforces serialization.

## Cost and model mapping

No new RTL register declaration, private SRAM, EXP lane or EXP table is
added. The incremental logic is opcode/guard decode, an exponential-input
mux and control qualifications. This source-level account does not establish
area, timing, routing or physical qualification. The existing clamp, captured
payload, step state, response buffering and U read/write costs remain.

Only actual measured S32 wrapper accept-to-next-accept service may replace
R1's NExp supplemental fee in the old S32/S96 SystemC evaluation. S32 n8
still requires two actual NX32 n4 frames. Old vector_region E service,
private-S, cache/DDR and barrier costs remain. S16-input/S32-output prefill
remains the complete legacy fallback. A guessed n4 interval is not a
calibration and must not be used as a reported result.

## Source preparation and validation

`baseline/` contains the exact four pre-R2 production files and SHA index.
`generate.py` uses unique source anchors and fixed baseline SHA values.
`candidates()` returns the four filename-to-text candidates.
`generate(repo,out,integrated=True)` requires actual production files to
equal the delivered candidates, writes the candidates to a new directory,
and records hashes. `--prepare` permits the exact R1 files before integration.
Neither mode runs EDA. Flat delivered sources must equal reconstruction.

The separate test agent owns bench/runner/job under
`iterations-research/rtl/round2`. Its contract includes R1/DIRECT0 compatibility,
all signed16 values, S32 alias inputs, native count/padding/param/aux errors,
state preservation and legal session continuation, reset, held responses,
real U S read/write ACK and measured compute/full-U stage costs.

Local checks are limited to Python AST, exact baseline/candidate reconstruction
and static diff inspection. RTL compilation/simulation, new throughput and
physical checks are not executed locally and remain pending remote receipts.
