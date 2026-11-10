# Exact15-pass full-scope failure baseline — Refs #250 / #252

Slurm102345, source`cf886cab7`, full Qwen2.5-3B36-layer decode512 historical
timing trace SHA`6ed2129e...f26f1d`. This is a complete-scope **SystemC timing
diagnostic**, not real full-model numerical inference or a300MHz whole-chip
measurement. E/N integer providers, deployed program fetch, typed source
loader integration and combined physical/energy qualification remain open.

The old8.136179token/s row still uses the unqualified dynamic placeholder.
It is retained only to show the consequence of correcting that assumption.

| Dynamic schedule, same physical3P base | Full-scope cycles | token/s |
| --- | ---: | ---: |
| old dynamic placeholder |36872345|8.136179169|
| measured ideal, use3P |601548755|0.498712694|
| observed component stress, use3P |691767635|0.433671633|
| measured ideal, use2P |820524141|0.365619956|
| observed component stress, use2P |946046061|0.317109296|
| measured ideal, use1P |1609318586|0.186414302|
| observed component stress, use1P |1860362426|0.161258901|
| measured ideal3P repeat |601548755|0.498712694|

The ideal3P result misses the9.215647token/s target by more than18×.
Changing lane scheduling alone cannot remove the15-record decomposition.
Issue252 therefore develops an explicitly counted native S32 resource.

## What was actually charged

The unchanged trace has36QK and36AV calls. Each is batches2/rows8; QK is
K128/N512 and AV K512/N128. There are73728K128/N8 chunk services and exactly
**1105920 real partial records**,552960 for QK and552960 for AV. Output N8
groups use the original cyclic/pair `detail::columns` policy across the
declared number of active P instances; the repeat has bit-identical cycles.
No independent physical SRAM, port or result owner is added by using fewer P.

Actual M + ordinary local S128 + LOCAL_S_PACK64, Slurm102338, validates
both full-N8 QK n-major and AV k-major layouts at1256cycles from BEGIN's
first flit to raw response. Native M modules are exact read-only source
`f08aefb93df071535f461da24b6829c5949bf5bf`; every initial DMA offer pays
its extra cycle. The surrounding normal owner bind/merge adds6 measured
cycles. Each record embeds288S128 reads,17actual64B local returns,8A32
beats and real13LC/14response flits. The interval is an exclusive atomic
service reservation on that P's actual ordinary S port; concurrent users
cannot consume this interval. It does not grant extra S ports or free W reuse.

The stress fee1483 is the largest record observed in seed25001 of102338's
artificial75%-ready component fixture. It is a **sample sensitivity**, not a
finite worst-case bound for arbitrary backpressure. Global DDR channel
arbitration/credits/row/turnaround costs still execute in each full-scope run.

Upstream raw tensor staging is separately charged through one64B return
retained in an existing MC slot. Each32/64B useful beat performs2/4 real-S
request/RTT2/ACK-edge writes before releasing that slot. QK walks contiguous
column fragments; AV walks strided32B row fragments and pays the complete
64B DDR beat. This is a conservative serial source-loader schedule, with at
most one outstanding raw return per P, not an implemented optimized loader.
It has no extra512B/4KiB payload FIFO. All global traffic shares the same two
DDR channels and32beat credits **per channel** with the rest of the trace.

Totals checked by `analyze_dynamic.py`:

| Traffic | Bytes |
| --- | ---: |
| dynamic local S reads |5096079360|
| dynamic raw staging S writes |339738624|
| LOCAL_S_PACK64 returns, explicitly zero DDR credits |1203240960|
| whole-scope global DDR reads, actual bus |3799178240|
| whole-scope global DDR reads, useful logical data |3648183296|
| global static weight reads, unchanged bus |3298000896|
| whole-scope logical writes, unchanged |8191232|
| KV state writes, unchanged |73728|

Each P uses raw B4096B+A512B within its original16KiB S; the final32B
result and two real S128 ACKs are separate. Dynamic stage peak is4640B if
result storage is distinct. Source-window release can later reduce this
peak but is not claimed here. Registers/MAC/packers remain counted separately.

The model reserves full record intervals instead of issuing every one of
the318504960 local reads as separate SystemC processes; those intervals are
calibrated against the complete real-RTL service, preserving one S port and
its finite ownership. It cannot prove alternate interleavings without new
RTL events. Current energy counters are not calibrated for this provider,
so no absolute energy comparison or ASIC/FPGA parity is inferred.

Run102340 is retained as a failed modeling iteration: generic Memory had
already reserved S delivery and the new explicit staging loop charged it
again.102345 replaces both with one typed raw-return→S-ACK calendar, retains
the MC slot through ACK, and preserves every source/log/hash. This is a
fee correction, not an algorithm speedup. No numerical scope/precision,
physical frequency or target was lowered.
