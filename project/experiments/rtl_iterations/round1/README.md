# Issue247 round1: integrated NExp control path

The source is derived from PR241 commit
`189e43c77a6277955c1be54281b0d6b0b0d55c1f`, whose candidate
`nexp_batch_adapter.sv` is copied without arithmetic changes. The new code
adds a real optional path to production `pu_u_group`: default
`NEXP_BATCH=0`, with one existing native N and unchanged private16KiB S.
This experiment does not instantiate a second production N or widen its
arithmetic. A separate reference N exists only in the numerical testbench.

## Explicit destructive ABI

The40-bit N metadata is `{param32,count4,opcode4}`. Opcode15 remains an
error for param0 and whenever the feature is disabled. With the feature
enabled, only two exact tags are legal:

| Param | Input | Count | Output |
|---|---|---|---|
| `0x4e455850` (NEXP) | packed signed16 values in one128-bit word |1..8| packed unsigned16 EXP results, unused lanes zero |
| `0x4e583332` (NX32) | four32-bit containers in one128-bit word |1..4| each unsigned16 result zero-extended into its original32-bit container |

Both require exactly one S source, no direct N→E route, and zero unused
source-address bits. A descriptor error is rejected before any S access.
Only unused complete data lanes must be zero. In NX32, a *used* word's high
16 bits may be arbitrary: the signed low16 is deliberately selected. This
is the old packed-integer bridge assumption, not generic S32/FP32 EXP,
saturating narrowing or a new quantization contract.

For every signed16 x, the original five-command scalar relative EXP uses
BEGIN, STATS(x), STATS(0), FINALIZE, EXP(x), and computes
`exp(x-max(x,0))`. The batch uses BEGIN, STATS(n zeros), FINALIZE,
EXP(min(x,0)). Both have exactly the same signed difference and native
lookup/interpolation result. The unsigned output at x=0 is32768, so the
S32 bridge must zero-extend rather than sign-extend or saturate it.

**Opcode15 clobbers the native N's previous statistics context.** The magic
tag is explicit consent to that destructive operation. It does not preserve
or resume an earlier multi-command RMS/Softmax session. Software must own N
for this transaction and begin a fresh normal session with op0 afterward.
There is no hidden live-session save/restore mechanism. The one existing
`ucf_s_compute_client` holds command ownership through response and S-write
ACK; ordinary N commands cannot interleave with the four internal commands
or bypass a held completion. E remains a separate sibling resource.

Payload/owner selection is captured at execution acceptance. Used high bits
and live external metadata cannot redirect an active transaction. Malformed
payloads cause an execution error before internal BEGIN and do not write S.
Reset masks all publication valid signals and drops in-flight responses.

## Fees and model boundary

Production S read/write, byte layout, command and ACK traffic are exercised
in `tb_nexp_u.sv`. Its input, compute and output intervals are reported
separately. A second direct compute test measures actual wrapper acceptance
to next acceptance, with no S operations. Only that supplemental compute
service replaces the old `NExp n*16` term. The old model's `vector_region`
E packet fee, S32 reads/writes, U cache, DDR and all other operators stay.

An old eight-value S32 packet requires **two actual NX32 four-value frames**;
it is not priced as the25-cycle packedS16 eight-value upstream adapter.
The runner builds the profile exclusively from measured NX32 count1..4
acceptance intervals. Prefill's NExp has S16 input and S32 output; round1
leaves that whole old service unchanged. PackedS16 timings are numerical
and local-interface evidence only, not a free prefill conversion.

Explicit additional state before synthesis: shared dispatch has135bits,
the copied batch adapter266bits, and descriptor rejection1bit:402bits
(50.25bytes), plus packing/clamping/mux/guard logic. Native N arithmetic,
tables, and existing client operand/result registers are reused. No private
SRAM capacity is added. This is a structural register account, not measured
cell area, routing, STA, power or physical qualification.

## Execution and evidence

`generate.py` reconstructs the production candidate from frozen
`pu_u_group_upstream.sv` (SHA-256
`f2136115a15aa34260f598770b5576970dfadea407879d897e5571630989bd59`).
Its default integrated mode requires the *actual production* U and both new
RTL modules to be byte-identical to the delivered candidate. Server tests
compile those production paths. `--prepare` permits code generation before
integration, but does not run or qualify anything.

Root places runtime/source files under
`project/experiments/rtl_iterations/round1` and the three production files
under `project/rtl/pu_leaf_base`. `delivery.json` lists exactly which files
belong to the experiment and the corresponding production map.

From an allocated new run root containing `source/` and its source/input
manifest, invoke `sbatch --parsable job.sh`. The job uses the existing
Singularity image and at most4 allocated cores. The runner executes:

- strict lint of the new synthesizable router;
- original full U regression on original, new default0, and new enabled1;
- exact accepted command/response/S event equality for original vs default0;
- every signed16 input against the unchanged scalar native sequence,
  S32 high/low aliases, invalid payloads, held replies, exclusive ownership
  and reset; count1..8 S16 and count1..4 S32 compute timing;
- actual U/private-S read/write ACK and readback, clobber/new-op0 recovery,
  invalid-descriptor no-read/no-write, invalid-payload no-write, real S
  arbitration holding a write ACK, and reset during local error/batch;
- three randomized initial-state configurations per build.

`results/result.json` records commands, exit codes, source/tool/log SHA,
measurement origins, and six explicit gates. A profile is emitted only if
all actual tests pass. `measurements.compute_s32` records count,
`accepted_to_next_accept_cycles`, command and log SHA. `profile.rows`1..8
sum those actual subframes. No guessed latency is used. Full-U timings
include S and must never be added a second time over the old model's S fees.

Local work performed here is preparation/generation/AST only. Actual RTL,
throughput, synthesis and physical outcomes remain pending server receipts.
