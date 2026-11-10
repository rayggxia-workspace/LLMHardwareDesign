# Shared native A pool and paired P integration

Issue [247](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/247),
PR [243](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/243).

`pu_p_shared_pair` connects two native P blocks to one immutable 32 KiB A
object. Eight 4 KiB 1RW macros supply one global 64 B read per cycle;
round-robin arbitration and four 64 B FIFO credits per P are unchanged.
This wrapper is an integration capability, not a complete model/DDR system.

## Operand interface

`A_WORDS_PER_BEAT` is 1 or 2. The paired wrapper defaults to 2 (32 B/P/cycle
container bandwidth); the standalone pool and M blocks default to 1 for
existing callers. `pu_p_group.SHARED_A_WORDS` defaults to 1 and its existing
`SHARED_A` enable remains disabled by default.

Each word contains eight S16 values or eight S8 values in its low 64 bits.
S8 still occupies a 128-bit container: 32 B of container bandwidth is
16 B of useful S8 payload, not 32 S8 elements. Bank and format are shared
by both lanes; row and tile accompany each word. The packed word index is
`P * A_WORDS_PER_BEAT + lane`, with the first word in the low slice.

For two lanes, the only nonempty valid masks are `01` and `11`. One
`valid[0] && ready` handshake accepts the complete offered mask atomically.
M rejects `10` and duplicate `{row,tile}` destinations by holding `ready`
low without writing either lane. The producer must correct such a malformed
offer; there is no separate error response on this operand channel. Both
lanes obey the existing bank execution, clear and start locks.

## Partial beats and backpressure

The pool takes up to two consecutive containers from the *same* FIFO head.
It does not gather across FIFO entries. Cursor 1 may supply words 1 and 2;
cursor 3 and a one-word tail use `01`. Row advances first and wraps into
tile independently for each word, including `rows=1`. Accepted word count,
completion and FIFO pop use the actual mask, not the maximum bus width.

A held head cannot change when another SRAM line returns. Thus valid mask,
data and destination tags remain stable under backpressure. Credit still
counts queued and in-flight 64 B lines, with no hidden skid entry.

The local-S feeder uses lane 0 only, with unused lanes zeroed; B ingress and
M arithmetic are unchanged. BEGIN/fill ACK/SEAL/RELEASE, epoch checking,
P LOAD join and cold-reset cancellation retain their previous contracts.
No SRAM bank, operand storage, multiplier or partial-sum slot is added by
the A-width parameter; routing, multiplexing and write-decode logic grow.

## Verification and limits

`project/experiments/shared_a32_native` contains Slurm-only functional,
equal-work cycle and mapped-area tests. The prior 16 B implementation is
byte-frozen in `project/experiments/shared_a32_baseline` for comparisons.
Run compilation, simulation and synthesis only in an authorized Slurm
allocation; follow `docs/REMOTE_RULES.md`.

The previous conditional S32/K256 model's token/s is a separate evidence
layer. Native S8/S16 K32 microbench cycles do not establish complete-model
token/s, conversion costs, DDR integration or a physically closed clock.
