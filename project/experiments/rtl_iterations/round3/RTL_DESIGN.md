# R3 finite S32/W8/S96 M service

Refs Issue247 / PR243. This is an independent optional service candidate.
It does not change production P16, R1, R2, DDR, precision or SRAM capacity.
The leaf is the exact PR241 source from commit
189e43c77a6277955c1be54281b0d6b0b0d55c1f, Git blob
071485d7040abe07a9bf3ad7791db02dc62197f8. Its independent numerical evidence
does not qualify this new wrapper before fresh tests.

## Scope and physical interface

`r3_m_finite #(BUFFERS=1 or 2)` contains exactly one K16/N8/ROWS8 instance
of `m_s32_stream_candidate`. It accepts one row of signed32 A and signed8 B,
uses the leaf's full96 accumulation, and performs its unique final RNE/S32
saturation. Other formats/rows use the existing timing-model fallback.

The wrapper connects to the read512 and write128 request/response ports of
one existing `block_feed_s16k_sram`, with four real 256x128 1RW macros.
It issues at most one physical read-or-write operation per edge. A wide read
uses all four banks; final narrow writes use one bank each. Read responses
have two finite metadata slots including pending operations. There is no
simultaneous64B read plus64B write assumption. No private SRAM is added.
The test harness must connect these ports to the actual SRAM model and
initialize through an exclusive ordinary port before commands begin.
All initialization responses must have retired before service starts.
The S request ports use the existing per-edge offer/accept contract, not AXI:
an unaccepted read offer may withdraw when the writer takes priority; only
valid-and-ready edges count. Accepted requests and their response metadata
remain owned until ACK. Command payload must be presented through its own
acceptance edge, and held completion payload remains stable until taken.

This is not a full `pu_p_group` native-ABI, DMA, shared-controller or DDR
integration. Reusing the old model's DMA/producer/ACK/two-A-bank schedule is
an explicit retained architectural condition. The service is not a native
P16 arithmetic qualification and not a numerically generated LLM token.

## Commands, layout and leases

Each accepted command contains ctx3, tag32, ki16, total_k16, k5, n4, shift6,
first/last, and three14-bit byte addresses inside the existing16KiB S.

- k1..16, n1..8, total_k1..65535; end=ki+k is calculated in17 bits.
- First requires a free context and ki0. Later commands must match tag,
  totalK, N, shift and output address, and start at reserved_nextK.
- Nonlast requires end<totalK; last requires end==totalK. A last acceptance
  closes further valid input until its output writes and completion retire.
- A is one64B-aligned S32 vector line. Only k values are active, but the
  actual controller reads the full64B line, including K tails.
- B is the original static K-major/N-interleaved W8 byte stream:
  `B[k_index*n+column]`. Its byte address may be unaligned. Up to three64B
  lines are gathered into a finite192B area and connected to the leaf's
  N-major input by a finite combinational transpose/selection network.
  There is no external free repacking or replicated B SRAM.
- Output is an exclusive16B-aligned32B staging region. Both128-bit words
  are physically written, even for N tails; unused leaf lanes are zero.
  Only n*4 bytes are logically useful to the later DMA/WB path. Padding
  belongs to this context and cannot overwrite a neighbour's tensor.

The wrapper rejects input/output overlap, overlapping active context output
leases, and a new output overlapping any live packet input. It permits
read-only input sharing. The caller must not externally overwrite A/B
before their packet transfers into the leaf and must not access reserved
output staging before its final S write ACK. `busy` means accepted commands
are in flight; an inactive gap in a still-open context does not release its
output lease. The wrapper does not snoop external writers or manufacture
cache-coherence/DDR-ownership hardware.

## Bounded ownership and completion

Each source packet has64B A plus192B B,256B total. BUFFERS is the only
single/double-source-buffer difference. Both versions release a source
slot on the exact leaf input acceptance edge, when its products capture
the operands, and allow safe allocation of that same slot on that edge.
The single-buffer comparison does not wait for leaf drain or final ACK.

A fixed eight-entry completion FIFO, identical in both versions, bounds all
accepted descriptors after their source slots have been released. Reserved
nextK advances only for a legal accepted descriptor. Committed nextK advances
only on the leaf's actual third advancing edge, synchronized with its global
output stall. Thus same-context successors can prefetch without committing
arithmetic early or overwriting FIRST state. Error descriptors consume a
finite completion reservation but issue no S/leaf operation and change no
context frontier. Error nextK reports the accepted prefix at their position.

Completions retire in acceptance order. Nonlast completion becomes ready at
leaf commit. A final leaf result transfers to one32B writer holding register;
its completion remains blocked until both actual128-bit write ACKs arrive.
The context/output lease releases only when that final completion is consumed.
A held final completion keeps the writer occupied and propagates finite
backpressure through the leaf pipeline, source slots and eight reservations.
Reset gates all service handshakes and discards every in-flight reservation.

## Measurement and old-model connection

For an aligned full K16/N8 packet, the real S workload is A64+B128 = three
64B reads. There is no A register cache or local-A read suppression. Two
buffers may overlap the next packet's real S reads with already accepted
leaf computation; whether this improves the continuous same-context stream
must be measured. Leaf II1 alone is not a service latency or a token/s result.

Headlines must exercise16 continuous same-context K16 packets per oldK256
tile, and the actual8/43-tile fullK2048/11008 chains. Eight interleaved contexts
are separate evidence, not a substitute for that workload schedule.

Tests should record cmd accept, read request accept/ACK, leaf accept and
global advance/commit, final result takeover, each write request/ACK, done
valid/consume and next command accept, plus bounded buffer/reservation peaks.
The old SystemC connection must reserve each actual S request once and use
the finite controller's dependencies. It must remove the old aggregate
send/adapter/compute/tail charge for qualified tiles and skip the old local
result store when the replacement already issues it. DDR, output DMA read,
WB and unqualified operations retain their old charges. A no-contention
wall-clock sample cannot simply be maxed against the old send time.

## Evidence status and backup

Local work is source preparation, AST and static contract review only.
No local RTL compilation/simulation, new latency, synthesis or physical
qualification is claimed. The parallel RTL test agent owns fresh numeric,
error/backpressure/reset, source-layout and cycle evidence. The model agent
owns independent finite-event/Calendar integration and workload attribution.

Keep this directory as a separate optional backup if the finite service does
not improve the old score or has excessive area. Production P16 and frozen
R1/R2 remain available without reverting unrelated changes. The resource
ledger lists source-level storage and large arithmetic separately; neither
that ledger nor prior leaf tests establish routed area or timing.
