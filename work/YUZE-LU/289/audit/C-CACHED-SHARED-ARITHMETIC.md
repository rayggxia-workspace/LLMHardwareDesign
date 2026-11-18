# Cached loader arithmetic sharing experiment

The original cached candidate remains unchanged. The two standalone variants modify only the pure `addr` function; all original state, allocation, reset, acknowledgement and external cycle behavior remains identical outside that function after line-ending normalization.

A: `aa + (f + 4*w + lane)*ast` becomes `aa + (f + 4*w)*ast + lane*ast`. Every multiplication and addition is explicitly unsigned 64 bits. Both sides are equal in the ring Z/(2^64), for every possible operand, including overflow. The shared first multiplier can serve all four lanes; lane multiplication reduces to constant shift/add when the allocation loop is unrolled.

AB additionally uses `index0 = flat(w,0)`. Because flat is 11-bit multiplication by four, index0 has low two bits zero even when w-a_words underflows. Consequently index0 <= 2044 and index0+lane never overflows 11 bits. For every cols encoding, the original row is base_row + row_step, and the original column is lane_col:

| cols | base_row | row_step | lane_col |
|---|---|---|---|
| 1 | index0 | lane | 0 |
| 2 | index0 >> 1 | lane >> 1 | lane bit0 |
| 3 | floor(index0/3) | (index0%3 + lane >= 3) | (index0%3 + lane) mod 3 |
| 0,4,5,6,7 | index0 >> 2 | 0 | lane |

For cols3, lane_sum is 0..5 and fits its declared 3 bits; base_row+row_step fits 11 bits for every case. All 16384 index0/cols/lane combinations were enumerated. `cached-shared-layout-proof.sv` also extracts the actual AB function prefix and original helpers to prove the 14-bit row/column identity with unconstrained word_index, a_words, lane and cols; no added assumption is required. The remaining B transformation is exact unsigned64 distributivity of `(base_row+row_step)*bst`. All extensions are explicit 64-bit zero extensions.

This is a source-level two-state arithmetic proof. It does not claim four-state X propagation equality. Each candidate must independently meet mapped area and the unchanged 4 ns physical diagnostic before consideration for a parent implementation. The existing reset-initialized cache-validity proof remains applicable because every addr result is unchanged.

Job119816 compares baseline, A and AB using the same FAST synthesis script and identical physical diagnostics at 30%/50% utilization (six 8-CPU tasks on one 48-CPU debug allocation). This is a relative module experiment, not C-parent signoff.

Independent endpoint_audit review inspected the actual original addr expression, shared-A and AB-v2. It confirmed original A unsigned64 context and new explicit unsigned64 products, the 11-bit index0 bound and 3-bit cols3 intermediate, and found no signedness/truncation gap. This supports the two-state source algebra only, not mapped/parent proof or four-state X equivalence.
