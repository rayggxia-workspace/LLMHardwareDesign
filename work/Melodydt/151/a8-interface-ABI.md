# L4 A8 bounded Attention kernel ABI

Issue151 / PR152; parent 1d722477564e14f7dc93e39ce8e28b8e2d150cb0.
Native source lock 707878621b2add4ed218b8c43df2e95c9a56e2ba; unchanged W4 N controller.
This document coordinates isolated drafts, not hardware verification evidence.

## Scope and numeric contract

One query, one head, 8 keys/tokens, D=8, 8 output channels. All tokens valid.
QK -> Softmax -> PV uses one each native M/N/S/T; no E/G/R.
Q/K/V are signed S8 Fin7. K byte offset is 8*key+dimension.
V byte offset is 8*channel+key (host supplies this explicit n-major layout).
QK M scale_factor=11585 (signed16, round(2^15/sqrt(8))), left shift0.
M op5 RNE right19 clips to S16 Fin10 scores. Softmax uses unchanged native N
and exact U16 EXP save/replay, producing nonnegative S16 Fin14 probability.
PV consumes A16 Fin14 x B8 Fin7, M factor1/left0, op5 RNE right11 -> S16 Fin10.
Probability sum need not equal 16384 exactly; use native integer semantics.

## S word map and input

All S words are 128bit. Fixed address/program, variable tensor contents.

| Addresses | Contents |
| --- | --- |
| 448..451 | Q: low64 of448 has8S8; remaining56bytes canonical actual zero |
| 452..455 | K:64S8, key-major/dimension-minor |
| 456..459 | V:64S8, channel-major/key-minor |
| 460 | 8 scores, S16 Fin10 |
| 461 | 8 exact EXP, U16 |
| 462..463 | Reserved unused; no read/dependency |
| 464 | 8 probabilities, S16 Fin14 |
| 465..467 | Actual zero padding for wide M A loader |
| 468 | 8 output values, S16 Fin10 |

12 input128bit beats =192bytes,136bytes effective +56bytes canonical zeros.
All12 actual write ACKs required before start_ready. Both M A/B loader bases
must be4-word aligned. QK bases448/452 A/B8; PV bases464/456 A16/B8.
Both loads: rows1,tiles1,bank0,reuseB0. No runtime address/shape/op inputs.

## Commands / normal transaction counts

Each projection: M CLEAR(op6), SCALE(op4), EXEC(op10,index0), READ(op5,index0), READ(op5,index1).
QK EXEC descriptor0x9884; read data0x113. PV descriptor0x9885; read data0x10b.
Extract each op5 response's four S32-carrier low16 lanes; index0 lower4 output lanes.
N request: mode0,count8,src460,exp461,dst464,epsilon0,gamma0 ignored.
Ordinary S requests/ACKs23 =19writes+4reads:
12 inputW +1scoreW + N(2W+3R) +3probability-paddingW +1outputW +1finalR.
M10cmd/rsp,2loaders; N6cmd/rsp; T1word take,then RELEASE before DONE.

## Ports, ownership and lifecycle

Same external port names/widths as block_w4_f8_top. Top block_w4_a8_top.
Single ordinary S helper; explicit OWNER_LOCAL/OWNER_N. Loader is native fast path,
active only outside ordinary S transactions; owner changes only after response ACK.
State local sequencer, not chip mother controller or new physical bridge macro.
busy from first partial input through held DONE. Reset/abort coordinately resets
all participating leaves/controllers/helper; no rollback. Error held until DONE
consumed; subsequent admission must follow coordinated reset, not reuse poisoned N.
out_data stable while stalled; out_index0,out_last1. T RELEASE precedes done_valid.
Partial/last unACKed frame cannot start; input/done handshakes and held start are explicit.

Top observability names for TB: state, owner, m_phase, projection, input_index,
permit_s_req/rsp,permit_m_cmd/rsp,permit_load,permit_n_req/rsp,
h_req_*,h_rsp_*,load_*,m_cmd_*,m_rsp_*,n_cmd_*,n_native_rsp_*,t_*;
matching W4 F8 where relevant. Constant permit wires are TB-only stall points.
TB should preserve native error injection and all source/format/ACK assertions.

## Explicit limits

Not full A_plain: no QKV/output projections, preNorm, RoPE, GQA, masking,
multihead/multigroup, true-model shape/capacity mapping, external-memory integration,
product metal binding or PPA. External-memory flexibility remains reserved.
New RTL simulation/regressions server Verilator only. Python math/reference checks
may run locally and must not be described as RTL simulation.
