# Issue247: isolated native M contexts

This directory belongs to Melodydt's Issue247/PR243 research. It contains a
generator and server-only numerical runner. It does not edit the production
repository or submit a job. The source snapshot is the actual `block_v2_m`
S8/S16 implementation, not the S32/96-bit SystemC candidate.

The candidate reuses the original eight result rows, each eight S64 values, as
up to eight output-column-group contexts. Existing A/B operand arrays, 16 S40
partial slots, eight S64 preview words, 64 S64 merged words, multiplier count,
two scale lanes, and the final RNE/saturation stages are unchanged. No SRAM
capacity is added. The original eight-row mode and live context mode cannot
overlap. This is a choice between interpretations of existing result slots,
not simultaneous eight-row by eight-context storage.

The new metadata is 8×(2-bit state + 2-bit format + 16-bit nextK + 16-bit tag)
= 288 bits. Current-command selection adds 37 bits: mode, final, source-row,
endK and tag. Total added explicit state is 325 bits (40.625 bytes), plus muxes
and checking logic. Physical area, timing and power remain unmeasured.

`block_v2_m_context #(parameter integer CONTEXTS=8)` accepts 1, 2 or 8. The
parameter limits new context IDs; original eight-row legacy storage remains.
All original ports, payload widths and ready/valid semantics remain. The
context path uses the same serialized arithmetic and atomic row commit.

| Command | Encoding |
|---|---|
| 13 | `index[5]=bank`, `[4:3]=0`, `[2:0]=destination context`; `data[0]=Awide`, `[1]=Bwide`, `[2]=first`, `[3]=final`, `[7:4]=lastK (1..8)`, `[11:8]=N (1..8)`, `[14:12]=tiles (1..4)`, `[17:15]=source A row`, `[33:18]=Koffset`, `[49:34]=group tag`, `[63:50]=0` |
| 14 | `index[5:3]=0`, `[2:0]=context`; `data[0]=abort`, `[16:1]=expected tag`, `[63:17]=0` |

FIRST requires a free context and Koffset zero. Append requires ACTIVE state,
matching tag/format/N and exactly nextK. The sum of offset and actual K length
must not exceed 65535. A successful original S64 atomic commit advances state
and nextK. Overflow preserves both old values and lifecycle, so the segment
can be retried at the same offset. FINAL makes the context readable using
original commands 3/5. A normal release requires COMPLETE; an explicit abort
allows ACTIVE or COMPLETE. Both require the tag and invalidate the result.
Global clear/reset invalidates all contexts; operand-bank invalidation leaves
the contexts as in the original contract. Command 12 remains the original
limited S40 diagnostic partial read; it is not a final RNE result API.

The original per-segment signed coefficient and left alignment may vary by K
segment. Every addition retains the original S64 common binary scale; the
caller remains responsible for that common scale. There is no intermediate
rounding. Original command 5 applies the final RNE exactly as before.

Actual A reuse is K-segment outermost: load one source A row, load a context's
B, execute it, then load the next B while preserving A. M checks valid/format
and locks the executing operand bank. It adds no cross-command bank reference
counter: software must not overwrite a reused A row until its consumers have
completed. The main P integration needs an actual B-only feeder operation;
root supplies that separately. A direct native-M result does not prove SRAM
or DDR speedup, and physical clock effects are not modeled.

`generate.py --repo ROOT --out NEW_DIRECTORY` emits unchanged original RTL/test,
the context RTL, the renamed legacy compatibility test, the new context test,
and SHA receipts. Root may rename the generator `generate_m_context.py` when
integrating it alongside `context_tests.cpp.inc` in `p_native_opt`.

`run_context.py --repo ROOT --out NEW_RESULTS --cpus 4 --verilator PATH` performs
server builds only when explicitly invoked there. It compares the exact full
legacy result JSON on original vs context RTL, runs new tests with 1/2/8
contexts and three randomized initializations, and audits the traffic counts.
The new C++ program uses direct signed `__int128` dot products and final RNE
as its oracle. It covers K1/7/8/9/31/32/33/65/255/256/257, all four S8/S16
format combinations, N tails, K65535, alignment and addition overflow, bad
descriptors/tags/lifecycle, response backpressure, bank locks and executing
reset. Each of 44 numerical cases measures three schedules: original
N-group outer loop, reordered contexts with A reloaded, and reordered contexts
with A reused. The last two have identical B and command work; their actual A
handshakes differ by the context count. Measurements include all configuration,
execution, output and release commands; reset and assertion-only negative
commands are excluded from the three measured schedules.

Local generation/static checks are not RTL execution. Server RTL, integration,
synthesis and physical results are pending until root supplies real receipts.
