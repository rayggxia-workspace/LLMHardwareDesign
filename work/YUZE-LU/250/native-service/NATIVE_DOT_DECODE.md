# Native exact S32 attention service in the decode512 replay

Refs #250, #252, #253. These are full-trace SystemC timing comparisons at an
assumed 300 MHz, not executed full-model RTL, physical signoff, or energy.
Run 24 / 102434 preserves the bad usable-S assertion: 16 KiB is the physical
capacity, but 256 B is already reserved in this replay. Only its historical
placeholder control completed. Run 25 / 102443 corrects the assertion and
repeats all eight variants on the same frozen input.

| Variant | Cycles | token/s | Dot span (cycles) |
|---|---:|---:|---:|
| Historical placeholder | 36,872,345 | 8.136179 | 10,689,310 |
| Four lanes, cold A/B | 109,901,651 | 2.729713 | 83,718,617 |
| Eight lanes, cold A/B | 74,420,138 | 4.031167 | 48,237,103 |
| Sixteen lanes, cold A/B | 56,564,167 | 5.303711 | 30,381,132 |
| Sixteen lanes, A resident | 51,389,483 | 5.837770 | 25,206,449 |
| Sixteen lanes, A and QK B resident | 48,451,066 | 6.191814 | 22,268,032 |
| Same residency, two bounded raw-return slots per P | 42,263,912 | 7.098255 | 16,080,877 |
| Same, measured primitive S-pressure sample | 43,777,186 | 6.852885 | 17,594,152 |

All native rows account for the same 75,497,472 S32 MACs, exact S32 profile,
216 worker calls, two-channel DDR budgets, and identical static FFN span
(18,625,835 cycles). They use actual native S128 leaf service timings from
102419, including K128 intermediate versus final chunks and final S write
ACKs. Producer staging, slot choice, DDR traffic, and S result export remain
explicit in SystemC. The current source stage is a model with finite slots,
not an implemented DMA/LC integration.

At the same sixteen lanes and **same single raw-return slot per P**, A/QK B
residency raises throughput by 16.75%, equivalent to 14.34% fewer cycles.
Dynamic DDR read bus traffic falls from 150,994,944 B to 98,795,520 B. AV
retains A; it does not assume that its full B fits in S alongside A. The
two-slot row uses up to the existing six 64 B landing slots across three P
instances, needs a real stage-to-S implementation, and is a separate
schedule/resource sensitivity. No new SRAM; dynamic S peak is 12,672 B
including the 256 B reservation. Pressure is a measured sample, not a
worst-case stall bound.

The best row is below 9.215647 token/s. The 8.136179 placeholder is an
unqualified control, not a speed target or an implementation of attention.
E/N numeric providers, full LC/MC and S source staging, M2 control overlap,
whole system physical acceptance, and energy are separate qualification
gates. The previous 15-partial exact failure remains in run 23. Use
`analyze_native_dot.py` on run 24/25 to audit source, receipt, workload,
bound, and result identities offline.

Run 26 / 102476 replaces the candidate S write serialization with the
102473 actual SRAM stage profile. It counts physical address bit 11,
three existing 64 B landing slots per channel, a single held aperture per
P, and releases the DDR beat only after all real S writes and raw ACK.
Both channel peaks are three. The best result is **7.187736 token/s**;
source-pressure-only is **6.865856**, source plus dot pressure is
**6.625541**. The unchanged old-stage control reproduces 7.098255.
With the same sixteen lanes and **two slots on both sides**, cold
6.651003 → A-resident 6.978147 → A/QK B resident 7.187736 gives **8.07%**
higher throughput (**7.47%** fewer cycles). Eight lanes are 6.124945
at the same residency; one slot with sixteen lanes is 6.326169.

The model still does not constitute actual mixed traffic timing:
the S stage profile is from original four-bank SRAM with a held MC
interface peer. Actual three-P typed dynamic64 transport is exercised in
102487 separately; its per-stage event/pressure samples must feed a
later round. E/N numeric providers and other system gates stay open.

Run 27 / 102482 tests **an unimplemented hardware option**: checkpoint
the unrounded S80 accumulator to the same private S, then process AV
in K128 order across both query groups and two adjacent N8 tiles. One
64 B DDR beat now serves both N8 halves; the candidate B reader needs an
explicit four-word row stride. The model charges each 22-word snapshot
and restore (20 S80 data words plus two headers); peak private-S
occupancy is 15,488 B including the reservation. Each of 6,912 saves
and restores uses the existing port, adds no SRAM, and does not add an
extra RNE. The two-pair wave reaches **7.792632 token/s** and 44,531,712 B
dynamic DDR reads, versus 7.187736 and 98,795,520 B in its exact control.
One-pair wave is 7.750448; conservative serial checkpoint transfers
give 7.746779; combined pressure is 7.273558. These improvements are
co-design sensitivity; they require new RTL and are not credited as
pure mapping gains. No variant meets the throughput target.

Run 28 / 102496 separately evaluates M2 short issue using the isolated
real issuer/guard2 profile from 102480 (INPUT EOP +11, CONTINUE/FINAL EOP
+16/+18, consecutive EXEC II15). M2 at the same serial AV schedule is
7.516904 token/s, versus 7.187736 with single M dispatch; combined with
the **still conditional** AV checkpoint wave, M2 is 8.181031 versus
7.792632. Charging the real registered first DDR offer raises cycle
count from 36,670,196 to 36,697,961 (8.174841 token/s). The stage-pressure
and combined-pressure alternatives reach 7.929642 and 7.610817 token/s.
These rows have the same 75,497,472 S32 MACs and static weight bus bytes
and no extra SRAM. They do not include proof of sustained wide-P issue:
the old independent DMA producer can prefill four W banks, whereas
the actual 102470/102474 coordinator serializes W fetches. The separate
[same-weight, same-return audit](WIDE_P_DDR_REPLAY.md) explains why even
the non-M2 FFN span cannot be treated as product calibrated.
