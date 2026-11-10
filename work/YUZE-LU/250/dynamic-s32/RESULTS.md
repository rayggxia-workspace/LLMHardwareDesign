# Exact dynamic S32 provider components — Refs #250 / PR251

Implemented independently of the M array: signed digit packer, full-K merge,
and explicitly typed `LOCAL_S_PACK64` weight-record source. All numerical/RTL
work ran on Slurm c64 6×10; source and receipts are SHA-bound. The complete
product LC/control chain, source fabric and combined physical flow are **not
yet qualified**, and the old 5.342443M dynamic timing placeholder is not used
as this provider's cost.

## Actual product closure and observed bottleneck

Runs102296/102299 execute the actual physical-port M leaf with real four-bank
local S, one serialized S owner, independent A/W packers and exact merge.
Six seeds×three initial states pass, with120 real partials,2040 LOCAL64
returns,21225 S128 read/ACKs,960 A32 beats,1560 LC128 command flits and1680
response flits. Sources are staged by2304 real S write ACKs; this fixture
staging traffic is separate from the zero DDR bytes inside LOCAL_S_PACK64.
Run102299 additionally holds final merge data through8 real S128 result
write ACKs and8 validation readbacks. These readbacks are validation only.
The controller is a finite testbench program, not a deployed LC/MC image.

Runs102310/102317 add no-artificial-backpressure traces and preserve the
same numerical/traffic results. The bounded37-bit cursor replaces repeated
address products without changing source addresses, read counts or cycles.
Run102326 binds unchanged canonical M modules from commit
`f08aefb93df071535f461da24b6829c5949bf5bf`: every partial really pays its
registered initial DMA offer. Ideal fixture105759→105879 is exactly120
additional cycles for120 partials; steady64B refill is not charged twice.

| Actual boundary: BEGIN first flit→raw response capture | Base M | Registered-offer M |
| --- | ---: | ---: |
| actual QK witness K128/N2 |543|544|
| actual AV witness K2/N8 |133|134|
| synthetic AV K128/N3 |735|736|
| synthetic AV tail K1/N3 |107|108|
| synthetic AV full K128/N8 |1255|1256|

Each full signed S32 K128 dot uses15 partials. Therefore the last row alone
costs18840 cycles per eight-output group, before source staging, final merge
and result ACKs, deployed program fetch or competing chip traffic. This
is a real hardware bottleneck and is not a DP optimization opportunity.
The former5.342443M dynamic placeholder cannot qualify complete token/s.
Issue252 tracks an explicit native signed32 service alternative;15-pass
arithmetic and all positive/negative evidence remain the reference.

Original-Liberty mapping102321 passes and independent `map_audit.py`
checks source, actual SCL and netlist-stat receipt binding:

| LC-owned component | mapped cell area µm² | DFFs |
| --- | ---: | ---: |
| full-K merge |33685.442|1503|
| separate A packer |23127.370|895|
| W source including its own packer |35446.096|1680|
| three actual instances |92258.908|4078|

There is no added SRAM. These are real standard-cell gates and registers,
not free LC arithmetic. They have no independent hard-block boundary and
are not P&R/300MHz certificates. The pre-cursor packer/source mapping areas
were27845.412/40072.368µm²; this is a hardware implementation improvement,
not pure DP gain. The source raw tile used by the product fixture occupies
4608B in existing private S and must be included in phase lifetime accounting.

Additional failures retained:102293 strict product bench warnings;
102297 affinity expression;102298 missing container PATH entry;102300/102305
library-cache/quoted-path receipt handling;102318 correctly rejected a new
packer against an old proof SHA. Original mapping still ran on original
Liberty; none of these failures relaxed numerical or electrical rules.
Recovery initially filled D; incomplete duplicate transfer bytes were
preserved at `C:/Users/wine10/.codex/issue250-cache/dynamic-incomplete-recovery-20261111`.
Complete recovered archives and hashes remain under the corresponding runs.

## Actual semantic contract

PR220 frozen `wide_program.py` Dot performs exact full-K integer sum, then one
RNE and S32 saturation. PR248's `native_s32_oracle.dynamic_terms` has the same
boundary. Per-K128 rounding would change results. The full signed S32 domain
requires three signed A16 radix15 digits × five signed W8 radix7 digits; low
unsigned16/unsigned8 values cannot be sent to the signed ports unchanged.
Every raw K128 partial fits S32; actual `m_group_s32` → `scale_group_s32` with
FP16 1.0/Ashift0/previous0/bias0 preserves it bit-for-bit. The new merge uses
eight80-bit transient accumulators (80B), maintains kk/ai/bi order, and rounds
only at full K. The absolute triangle bound for every intermediate ordering
at K65535 is `510007797560335317139455 < 2^79`.

The original decode512 timing trace has 36 QK `(rows8,N512,K128,batches2,
shift24,layout1)` and 36 AV `(rows8,N128,K512,batches2,shift24,layout2)` calls.
Its tensor payloads/per-tensor exponents are absent. Its shift must not silently
be changed to16 or interpreted as new Q16 whole-model quality evidence.

## Scope and results

| Job | Actual frozen result |
| --- | --- |
| 102263 / run05 | six seeds×three initial states: full-K merge536 commands, native M/scale345 groups, host packer55 commands, all passed |
| 102264 / run06 | above plus real four-bank local SRAM packer54 commands×ideal/backpressure×three initial states =36 real-S runs, all passed |
| 102273 / run08 | four-scalar same-response extraction, same storage/ports/byte counts; all previous unit/real-S runs passed |
| 102275 / run09 | real-S LOCAL_S_PACK64, 30 configurations×17 complete64B returns; six seeds×three initial states passed |
| 102282 / run11 | above plus held unaccepted offer across cancel, accepted partial CLOSE/drain, wrong-owner/address/shape, S identity fault quarantine/reset; all18 source runs passed |

Independent `audit.py` checks canonical source/archive/member/part SHAs,
six math receipts, actual model vectors, every unit PASS, warning-free builds,
real-S read/ACK counts and native S range. For run11 it verifies exactly512
successful local64B returns: 30×17 ordinary plus two canceled true returns.
`LOCAL_S_PACK64` makes **zero DDR requests**; its S reads and17 native M return
beats are separate traffic classes, and a surrounding fabric must not charge
or return global DDR credits for them.

Twelve actual first-attention QK/AV witnesses were re-executed from frozen
PR220 Qwen2.5-3B integer program SHA `5e5791f5...f2bc` for `[[1,2]]`. Original
program/reference source and instrumentation hashes are recorded. Instrumentation
only observes the original np.matmul call in memory and returns np.matmul;
original RNE/clamp and archived files are unchanged. Captured shapes are QK
K128/N2 and AV K2/N8. They validate a real B1/S2/no-KV model slice, **not**
decode512, new W8 whole-model quality, integer KV quality or full RTL inference.
Fraction/edge tests separately cover K1/2/16/127/128/129/512/65535,
INT_MIN/MAX, negative top digits/carry, shifts0/1/16/31/47/63 and saturation.

## Finite hardware accounting

| Resource | Real payload registers | Boundary |
| --- | ---: | --- |
| Merge accumulator | 80B | eight signed80-bit lanes, one owner |
| Merge raw input hold | 32B | accepted partial until apply |
| Merge final output hold | 32B | held until consumer acceptance |
| Digit packer output | 64B | A uses low32B; W uses64B |
| Digit packer source cache | 16B | one actual S128 response |
| Weight source wrapper | no additional payload | binding/tag/mask/cancel metadata; reuses packer |

Control/identity/cursor registers and mapped gates are additional to this
table and will be measured. No SRAM or persistent S32 growth is introduced.
An A packer instantiated independently of the W-source packer would require
its own80B and gates; sharing cannot be claimed until an actual arbiter is
implemented. Existing 4×1152B W banks/2×256B A leases are not expanded.

The real-S four-scalar improvement uses four digits already present in the
same128-bit return, with no extra read owner/cache/port. Example observed
command→output cycles in otherwise identical first-seed ideal tests:

| Case | S reads | scalar walker | four-scalar walker |
| --- | ---: | ---: | ---: |
| aligned A16 packet | 4 | 28 | 16 |
| misaligned A16 packet | 5 | 31 | 20 |
| representative W64 packet | 20 | 124 | 80 |

These are component costs, not complete record/M/control latency or token/s.
Old run06 log `%t` values were in ps; the audit explicitly normalizes to the
10ns functional clock, while current logs print integer cycles directly.
This extraction change is a **hardware implementation improvement**, not DP.

## Source/control boundary still required

A binding freezes owner,64B-aligned native record range, local S scalar range,
K/N strides, digit and length until actual returns drain. Full ordinary native
records are1088B (17×64B):1024B W8 plus16B FP16(1.0) and48B zero padding.
Short K/N tails generate explicit zero payloads; no S read escapes16KiB.
Cancellation retains an already offered request; CLOSE does not imply its
accepted data returned. Wrong S identity cannot fabricate a good MC return:
the source quarantines until reset because the existing M MC return API has
no error-data wire. Full fabric error recovery is therefore still required.

Complete deployment needs the typed source router, real source-specific
CLOSE/FENCE/credits, A digit delivery,15 actual BEGIN/CREATE/ALLOC/EXEC/RF
services and final merge→twoS128 writes/ACKs, all with finite ownership and
real program fetch costs. Current W bank frees after every INPUT EOP; three
uses of one digit record must not be assumed free. A bi-major three-use W
lease would be a separate hardware change with its own verification/area.

Failures retained:102246 frozen callback API mismatch;102252 bench clock
initialization warning;102257 peer initialization warning;102258 unused
scalar alias warning;102271 first-address low bits warning;102277 unused
test oracle bits. No numerical standard or warning severity was reduced.
All run source archives, logs and source/receipt hashes are retained; base64
receipt parts are each≤1MiB for upload, with decoded original archive SHA.
