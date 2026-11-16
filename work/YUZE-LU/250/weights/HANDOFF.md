# W8 record frontend handoff — Refs #250

## Candidate and real evidence

`project/rtl/w8a16_v1/weight_records.sv` now implements the finite four-bank
W-first frontend. Production RTL changed in `e308ab2d3`; final protocol
test source is `aa490534bc6198fec016de87258523ecc32996ec`. The complete branch
is based on root integration `551b4251f` and only changes assigned weight
paths and this evidence directory.

Final Slurm job **102097** completed successfully on c64 with six tasks ×
ten CPUs. All six seeds × three initial states passed strict Verilator
5.042 production `--Wall` lint and actual `m_group_s32` integration. Every
run checks **307 W handshakes, 87 raw outputs, nine protocol rejections**
plus six complete-record payload errors; different-bank DMA fill/M read
and independent MC issue/LC-command acceptance are exercised concurrently.
The 34 fixed public records alone supply 272 operand beats and 83 raw groups.

`run-05/receipts.tar.gz` SHA256:
`48d0cf7865abc5643b8f9f45974dda817d9ea1fd070a4a453773a44752da839f`.
Its 68 members are individually checked in `collection.json`/`audit.json`.
The fixture SHA256 is
`5abf48c82a4ad5efa4f4473bf64f5604519f1059546a7067fd39c2a684cd27d1`.
Archives retain exact committed sources, generated top, strict lint/build
logs, all 18 results, model/header/payload hashes, fixture and allocation.
Expanded local receipt folders are ignored because their complete verified
contents are already in the immutable archives.

The first job 102090 printed functional PASS but failed on C++ destruction
order after Verilator context teardown. Commit `7100bda43` destroys the
model explicitly before process exit. Runs 102091/102094 then passed;
102096 added independent MC issue and passed; 102097 additionally passed
same-bank cancel/new-issue exclusion, drain/other-bank issue concurrency,
and final-DMA-return/cancel same-cycle precedence. All old logs are kept.

## Byte contract

Ordinary: **1088 B = 1024 signed W8 + 16 FP16 scales + 48 zero pad**,
17 real 64 B DMA beats. Head: **1152 B = 1024 W8 + 8×16 B scales**,
18 real beats. Both start at a 64 B aligned record address. W bytes are
`[K16 tile][N lane][K lane]`; each native 128 B M beat is eight N lanes
of sixteen signed weights. Ordinary emits one K128 group; head emits
eight K16 groups with separate scale vectors and tags, never a reused
group128 scale.

The scalar codec reads the public checkpoint at model SHA256
`73d70c78b55123ff89d5c3b333f169934703c1fd8138ca1d4942b35b58e2d7d6`
and revision `1fed15cb34975bc0bd699e62b95a539bb06eed42`.
It hashes the whole 3,465,861,104-byte model on a Slurm compute node,
unpacks qweight/qzeros/g_idx independently, compares all original W bytes
against 24 frozen real run38 groups and attaches actual source FP16 scales.
Four head records derive declared head16 W8/scales from real tied embedding
FP16; six N=1/2/7 tails are also actual-weight records. Active FP16 scales
must be positive finite nonzero; inactive W must be zero, inactive scales
are ignored/output-zero. Ordinary padding is checked.

The codec and an additional independent receipt parser both compare the
full encoded payload, native order, scale grouping and signed integer dots.
Head activations are directed. Down activations come from the historical
Mid64 vector. This does not establish new Mid32 whole-model accuracy.

## Actual resources and integration rules

- **4608 B = four × 1152 B data registers**, plus approximately 1788
  metadata/control register bits (default key128), decoder, W/scale mux and
  byte validity logic. No additional SRAM or private X storage is added.
  Final area/clock/power must come from the integrated M physical flow.
- The 1024-bit raw W unit port and scale128 are internal to the new M leaf;
  root must internalize them. They are not proposed M10 escape interfaces.
  This module is not a new physical P hard box.
- Allocation, start and input-consumed commands share one finite LC
  acceptance per cycle. Real MC issue is independently one beat/cycle with
  **32 per-M total outstanding credits**. Real DMA return is independently
  one 64 B beat/cycle. A global shared MC arbiter enforces the chip-wide
  bandwidth/credit limit. Every actual allocation, start, consumed, DMA
  latency and arbitration delay remains in the native schedule.
- The frontend accepts reordered DMA returns once, only after actual MC
  request acceptance. A bridge must rendezvous both handshakes. `fill_last`
  denotes highest beat address, not arrival order. Full actual bytes,
  scale/padding validity and accepted held FILLACK precede READY.
- Start uses full job/object key128, record32, bank2/gen16 and use16.
  On each actual operand handshake, the integrated raw/scale owner captures
  its scale and independent result identity. It cannot fetch them later
  from a bank already reused by a new record.
- The last W handshake leaves WAIT_CONSUMED. Only a matching explicit
  input-consumed ACK frees W. The external control guard owns **two 32 B
  result slots**, independently leased until the two native S128 result
  word ACKs complete. Do not identify a delayed result ACK by a recycled
  W-bank generation or pretend the four W banks contain four free results.
- Cancel suppresses further DMA issue/current W delivery. Already accepted
  DMA must all return. Drain requires external raw/A cancellation proof.
  Simultaneous last return/cancel cannot publish FILLACK/READY. This module
  does not roll back a partial M accumulation. Global reset requires real
  DMA drain and a fresh full key; finite wrapping bank generations alone
  do not provide arbitrary-history ABA protection.

## Qualification boundary and next work

This task qualifies deployment bytes, W buffer/protocol and actual raw-M
integer operands/results. It does not integrate scale/context/result FIFO
ownership, MC/LC native programs, new Mid32 numerical decode or final P&R.
Those remain root/control/storage integration work. There is no energy,
token/s or final 300 MHz claim in this unit receipt.

In particular the old SystemC `cl_wave` held W banks through result ACK;
production early input release is a real lifecycle change. The old 9.223
token/s result also retained legacy64 B/cycle costs for some native S
services. Root is recalibrating all S128 services and finite pipelines; this
unit must not be presented as preserving that conditional performance gate.

The original performance report distinction is also explicit:
`read_bus_bytes=3,388,365,824` and `logical_read_bytes=3,365,952,512` are two
different fields in run08/report.json. Padding/alignment is real bus work;
the latter must not be relabeled as the former.
