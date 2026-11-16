# Complete native M and product-aperture evidence — Refs #250

## Current source and evidence (2026-11-11)

The historical timing and physical attempts below remain evidence of their
own sources. Current source combines RF late-read three-stage arithmetic
with head STEP II1 (`53b9edf5e` upstream), `COMMON_A_SHIFT=1` in the product,
real partial MC CLOSE, and the M metadata repair `637c51787`. The latter adds
four 37-bit response metadata entries (18.5 B plus pointers/count), because
the earlier single response latch was invalid with multiple RF commands in
flight. The failed integration jobs102223/102224 are retained in run31/32.

After repair, jobs102228/102229 pass six seeds x three initial states for
product and generic native/W units. Product run33 has761 real MC64 requests
and returns,352 real A32 operands,92 external RF completions and86 actual
guard S128 ACKs per run. Generic head tests retain eight independent RNEs,
actual-prefix cancellation, N-tail and backpressure, rather than changing
the oracle to accept the former metadata error. Recovered run33 archive SHA
is `1494c69010342a3ea4dd50e42d1980106f2420626a3af0be8e2cd1fd3e3a1afb`;
run34 SHA is `3fea1421d4e168de1677599214bd00262d4ba139c9ff7462fce3c215d5e7adfe`.

Current product timing (run33, ideal host S RTT2, actual frozen guard):
native EXEC to INPUT EOP11, CONTINUE EOP16, FINAL EOP18 cycles, for ordinary
and head. Head consecutive CONTINUE-to-FINAL actual EXEC II21 includes the
guard's single active native issue and the next two command flits; a bare
pending-command theoretical II is not claimed. The prior conservative RF
single-pending three-stage source measured head INPUT19/CONTINUE30/FINAL32,
actual guard II35 (run28). Its full physical-port map102208 is723132.704um2,
1330 pins including34 real partial-CLOSE pins; this is not the new II1 map.

Old single-stage physical102182 reached real CTS WNS-1.81ns and then failed
TritonRoute on `one_` incorrectly arriving as a non-special POWER logic
net. Read-only OpenDB evidence shows the problem already at1_synth: actual
logic loads, not an empty harmless net. Mapping repair `4f159122d` adds
real LOGIC1_X1/LOGIC0_X1 tie cells with standard hilomap, charged to area
and processed by unchanged native repair_tie_fanout. It does not relabel
logic as special PG, change Liberty or relax the300MHz constraint. Old
single-stage source and conservative three-stage physical runs are retained
as comparisons; current II1 qualification still needs fresh map/P&R,
function, formal, DRC, PG/electrical and actual outline/core utilization.

Large raw mapping/physical artifacts remain in the authorized immutable
server directories with byte/SHA indexes per AGENTS.md. In particular,
run09/17 raw map archives must not be re-added to Git. Run21/26 use
index-only collection; source packages and compact logs remain reviewable.

This supersedes only the integration/timing scope of `HANDOFF.md`; the immutable model and W-first byte contract there remain valid.

## Implemented ownership and data resources

`m_native_s32.sv` instantiates four real W records (4608 B registers), raw K16xN8 A16/W8 compute, a four-item scale/tag pipeline, and the root's 16x8 S32 context RF (512 B). Ordinary K128 uses one FP16 scale vector and one RNE update; head K128 uses eight K16 scale vectors and eight independent RNE updates. A is eight actual 32 B beats, with exact key/record/slot/generation/kk/use/beat matching. W input storage releases only after last actual operand and the matching INPUT handshake, independently from the result's S write ACK.

RF contexts CREATE/RESTORE/STEP/SPILL/DROP retain actual owner/fullK/nextK/group/n. SPILL returns owned metadata; invalid numeric/cursor requests return fault metadata zero. Snapshot RF entries may release after actual captured output, but a snapshot can be restored only after matching owner/context/ticket/cursor/shape proof from the real external S-write guard. Cancel is a prefix drain, never assumed rollback. The logical unit's head-cancel regression observes the real completed prefix.

`m_native_leaf_s32.sv` adds the actual physical product interface, not an unbounded software shim. `M_APERTURE.json` is the single opcode-specific ABI 0x02504d02. A 128-bit LC frame buffer feeds one pending command. Sixteen finite BEGIN_SCOPE entries cache independent input-object key and RF output owner, fullK/n/profile/final bias. Four finite record descriptors drive real 64 B MC beat requests with held ready/valid. A remains 256 bits; DMA return remains 512 bits. No 1024-bit raw W bus escapes the M leaf. Serial responses hold their exact flits under backpressure; source-event ACK occurs on the actual EOP. Normal CONTINUE reports only RF commit, never a fake 32 B S result. FINAL/SPILL has two metadata and two 128-bit payload flits; the external actual two-slot guard must then obtain two true S128 write ACKs.

The scope base budget is 8800 bits including 512 B of final bias; live/epoch/nextK add 416 bits, making scope storage 1152 B. The command frame is 128 B and transmit frame is 64 B. Four record tables, request lock, all owner metadata, decode/mux and pipeline registers are additional counted active M logic. W4, RF16, M1 executing record, external guard2 and candidate LC range6 issued tickets are distinct bounds; an INPUT ACK does not retire a FINAL/SPILL range ticket. None of this storage is described as free merely because it is registers rather than SRAM.

MC tags encode epoch9/bank2/generation16/beat5. A record remains on channel `(record_start_byte/2048)%2`, even if it crosses a stripe boundary. Each actual request accepts one 64 B beat. Native private credit32 is only an upper bound; the real MC separately limits each channel to32 beats and32 descriptors. Duplicate/stale returns cannot overwrite a record or refund a legitimate credit. Cancellation cannot withdraw an offered request; issued traffic drains before DRAIN. Generation reuse requires a matching real MC fence purge plus coordinated LC/A drain, not merely an observed empty queue. Exhaustive 65536-generation wrap is not claimed by the unit run.

## Actual source-bound tests

| Job | Result and scope |
| --- | --- |
| 102115 | Original joint C++ strict-build indentation failure retained, repaired in76657278c. |
| 102116 | Logical M + actual frozen two-result guard, six seeds x three initial states passed. |
| 102118 | Logical M timing and head/cancel/real-ACK regression, six x three passed. Per run127 planned groups,122 actual RAW/RF groups,339 operand beats,93 RF responses,42 inputACKs,82 S128ACKs. |
| 102120 | Logical API map passed:589605.492um2,5484 port bits. This is not the product physical interface. |
| 102143/102146/102148 | Product strict lint failures retained; width/callback identity/continuous-channel dependencies/cancel-ready loop repaired. |
| 102151 | Product strict `--Wall` lint passed. |
| 102157 | TB offered A before EXEC header, correctly rejected; TB fixed to offer only after complete matching EXEC EOP. |
| 102162 | Actual product ports + frozen RTL guard; six x three passed. |
| 102166 | Five physical transport negative cases and actual held-request cancellation added; six x three passed. |
| 102170 | Exact tested complete product mapping passed,711030.502um2 and1296 actual port bits. No physical timing/DRC qualification inferred. |
| 102171 | W unit and logical M re-run after cancel-priority production change; both six x three passed. W307 beats/87 raw outputs/nine faults; native122 actual RAW/RF groups. |
| 102172 | Final expanded product run, six x three passed. Each725 actual MC64 requests/725 valid returns,336 A32 beats,89 RF completions,84 actual S128 ACKs, peak guard2, private credit32, five transport rejections. |

Each public fixture starts from the frozen full model SHA256 `73d70c78b55123ff89d5c3b333f169934703c1fd8138ca1d4942b35b58e2d7d6`. The 34 source records include24 original run38 FFN records,4 declared symmetric-head16 records and6 actual-weight N-tail1/2/7 records. Additional cross-record K256 tests deliberately compose declared source slices; they do not claim those first/last public K slices are adjacent. Common runtime A shift8 in the product test is directed unit coverage; actual whole-model normalization metadata remains the LC/U/E service. Logical tests also cover independently varied legal head shifts.

`run-19/receipts.tar.gz` SHA256 `bcc03af3c026123ac14e95b57a1359a1352c83e5e2a386b279082f81454d671b` contains117 individually SHA-verified members. `audit.json` separately checks all18 runs' real request/return conservation, one instance of each DMA beat, exactly two S words for each snapshot, zero writes for RF-only records, all8 A beats and actual serial product costs. It inspects recovered evidence; it does not locally simulate RTL.

## Calibrated product timing

No-stall product trace `run-19/receipts/leaf-seed-25011/timing-0.csv` observes:

- EXEC uses two128-bit command flits; native execution starts one cycle after EOP. Eight actual A32 handshakes follow.
- Native EXEC to INPUT EOP is11cycles, to CONTINUE EOP14cycles, and to FINAL EOP16cycles. Add one from LC EXEC EOP. Head and ordinary have the same measured product timing despite head's8 independently committed numeric subgroups.
- CREATE LC acceptance to two-flit EOP is4cycles. SPILL LC3503/core3504/RF3505/response3506..3509. Its real guard S requests3511/3514 and host ACK3513/3516 precede terminal3517.
- RESTORE has8 actual input flits3521..3528, core3529/RF3530/response3531..3532/terminal3534. Two true S reads of its32 B previous state and normalization input preparation are external costs, not hidden inside these numbers.
- The host S provider is finite one-outstanding, ideal RTT2 or random3..9. It exercises actual frozen guard RTL but is not the SRAM macro. The real local_s_base/LC bridge test supplies the actual SRAM contract separately. `run-16` ideal RTT1 is historical and must not replace the current RTT2.

Core-only12cycles is retained as an arithmetic boundary measurement, never substituted for complete command/INPUT/RECORD traffic or actual S ACK time. A following native record cannot start before the prior RF-response EOP; a prepared descriptor may wait at the finite command slot.

## Physical status and capability boundary

Original main Nangate45 Liberty SHA `8d540a4d4cf6d09d27c87ad067857a9c0c2eeb023ab7a56e058cd3113db4e9b1`, original full FreePDK45 deck SHA `4e35cad6786f21c6e233fb606bea59bb44e1a12713008cf7367d65a1a3de2147`, and original `block_v2/physical.py` are unchanged. The explicit batch ABC transport preserves the generated mapping script. Product mapped area includes all physical wrapper logic. P&R is currently running at1380x1380um, not accepted yet. Final qualification requires real final-ODB function, strict native equivalence, independent setup/hold/electrical/PG, full native GDS DRC and active outline/core density at least mainM35.187442%/38.4745965%. M11/M12 system routes and hierarchical timing are separate.

This M supports registered **static W8A16 S32 projection** only. Dynamic S32xS32 QK/AV is explicitly unsupported. A15-partial-pass balanced-digit candidate is unimplemented/unregistered and would require up to71-bit exact K128 recombination; current S32 RF cannot claim that feature or old one-pass timing for free. These unit and physical M results do not establish whole Qwen numerical quality, token/s or system physical closure.

ABORT recovery: head returns the actual K16 prefix (e.g. nextK48), but product EXEC still requires a whole K128 record at an aligned offset. Current recovery drains, drops partial RF state and reopens from the last committed K128 snapshot; direct K48 resume is unsupported.
