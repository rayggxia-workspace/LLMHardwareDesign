# Why the measured wide P is slower than the FFN SystemC schedule

Refs #250, #251. The same-weight comparison uses **72 actual RTL scopes**:
two K2048/N64-gate/N64-up scopes per run, six seeds and three initial
states, for 102470 (per-tile copy) and 102474 (lazy-copy candidate).
The RTL runs one actual P, with real S/A/M/guard traffic and a finite DDR
peer. It does not run three P clients on the production DDR fabric. Each
scope includes 256 ordinary K128 record admissions,
16 BEGIN and 16 CREATE commands, 256 true ALLOC/FILL/EXEC pairs,
4,352 accepted 64 B reads and exactly as many returns (278,528 B), 256
A S128 reads, 2,048 A32 beats, and 32 terminal S128 write ACKs. The
scope window starts at admission and excludes fixture boot and the
post-terminal host readback.

| Real trace | Scope cycles min / median / max | First → last DDR return median | Earliest final EXEC EOP, same returns, relative to first return, median |
|---|---:|---:|---:|
| 102470 | 19,699 / 20,221 / 20,492 | 19,927 | 19,954 |
| 102474 | 19,507 / 20,105 / 20,491 | 19,927 | 19,954 |

Every measured run has **one W record fetching at a time**. The RTL
prepares both records of a pair before the first EXEC. It only admits
the following pair after the active pair advances. In the representative
102474 seed1/init0 first scope, the measured 19,900 cycles break down as:

| Span | Cycles |
|---|---:|
| Scope start to first DDR return (includes startup and first fetch) | 235 |
| Between returns inside the same record (4,096 gaps, 2 cycles each) | 8,192 |
| Previous record last return to next ALLOC EOP (255 transitions) | 8,057 |
| Next ALLOC EOP to next first DDR request (255 transitions) | 1,064 |
| Next first request to its first return (255 transitions) | 2,295 |
| Final DDR return to final actual result completion | 57 |

The previous-last-return → next-ALLOC-EOP median is **8 cycles within
a prepared pair**, versus **50 cycles between prepared pairs**. These
are state-machine delays as observed with this specific peer and real
A/ACK backpressure; they are not all arithmetic latency. The peer can
accept up to 32 outstanding requests overall, but its single held
response and no same-edge refill cap returns at 32 B per core cycle
across both channels. At that ceiling, 4,352 continuous returns would
span 8,702 cycles first to last. Actual first-to-last span is 19,608 in
this sample: the observed gaps add 10,906 cycles above that cap. The
single-record admitted policy, not just the raw DDR peer service rate,
is therefore the main reason this fixture misses the model.

`analyze_wide_p.py` checks original accepted requests/returns, ordered
17-beat addresses per ALLOC, genuine out-of-order return timestamps,
one live record, paired issue, every record's completion identity and
terminal S ACKs. It then replays the **exact same return timestamps and
record order**, advancing FILL and EXEC using the fastest observed
latencies and omitting A, manual controls and output contention. The
representative replay reaches final EXEC EOP at cycle 19,871, **the same
cycle as actual RTL**; actual final completion is 30 cycles later. This
optimistic replay isolates the limit imposed by those captured returns.
It is not a new whole-P SystemC runtime or an assertion that a different
admission schedule would see the same arrival calendar.

The old full decode 18,625,835-cycle FFN span includes Down and 36 layers
with 58 waves/layer (57 full, one tail). Its average is only about 8,920
cycles per wave, even before separating out Down. Those numbers cannot
describe the observed fixture: even without any tail P scopes or
any Down work, repeating the fastest observed *captured* full-width
first-to-last return span for the 2,052 full waves would exceed 39.8M
cycles. This is an illustrative fixture bound, not a prediction for a
three-P production fabric. The SystemC implementation submits the next
DMA after a bounded W-bank/ticket reservation in a separate producer
while previous records execute (`native_cl_service.inc`). This permits
four existing banks to be filled early without the real wide
coordinator's single ALLOC/FILL wait. Its nominal two-channel bandwidth
also differs from this direct peer. These are two independent changes;
neither a blanket bandwidth correction nor isolated M2 II15 makes the
full replay a measured wide-P result.

The next useful experiment uses unchanged address streams and bytes, one
identical DDR peer, and the existing four W banks. Separate ALLOC/FILL
ownership from EXEC/result retirement. Start with the current serial
admission, then allow two and finally four pending W fetch owners. Keep
the actual short command aperture, owner/generation/early-release ACK,
cancel/drain, 16 RF contexts and two result slots. Compare accepted W
requests/returns, time with an empty peer, first-beat delay, peak W and
credit occupancy, and START → terminal cycles. Follow with the actual
three-P fabric and same shared channel budget. Do not replace the
serial model fees until the faster admission is implemented and tested.

Reproduction: `analyze_wide_p.py --job JOB --archive ARCHIVE --out NEW.json`.
The two machine reports bind exact per-run CSV/log hashes and source
manifest. Original results are under
`/public/home/yuzelu/project-circuit/issue250-control-prep-20261110-{101,102}/project/experiments/shared_x_control/results/`.
Archive `source.sha256` and `p-resident-{0,4}-SEED-INIT.{csv,log}` for
the matching run. If re-packing changes tar metadata, add `--reference`
with the checked-in job JSON; the analyzer then requires every raw file
hash and all computed values to match it.

## Actual same-peer two- and four-bank follow-up

102524 replays the serial pair baseline and adds a two-fetch mode.
102530 allows four fetches in the same K tile once the relevant RF
contexts exist. `analyze_w_prefetch.py` independently reads 36 scopes
per mode and binds each accepted record to its 17 addresses/channels,
context/K, physical W bank/generation, INPUT EOP, and real completion.
The paired workload digest is identical for every seed, initial state
and scope across all three modes. No W generation is overwritten
before INPUT EOP, no overlapping K tiles fetch, and the first K tile
only reaches two fetches even in mode 6.

| Mode | Peak owned W banks / concurrent DDR W fetches | Median scope cycles | Total over all 36 scopes |
|---|---:|---:|---:|
| Paired serial W | 2 / 1 | 20,105 | 720,948 |
| Two W fetches | 2 / 2 | 17,074 | 611,991 |
| Four W fetches | 4 / 4 | 12,878 | 462,687 |

Same-work reduction is 15.11% / 35.82% in total cycles. No SRAM or W
payload capacity was added. The four-fetch source adds two metadata
entries (506 bits total) and 33 earlier-pair bookkeeping bits. This is
a controller hardware improvement, separate from pure mapping gains.
For seed1/init0 first scope the direct peer has 10,906 / 8,099 / 3,940
cycles idle above the return ceiling. Of these, 8,611 / 6,956 / 2,932
have no accepted outstanding request; 2,295 / 1,143 / 1,008 have only
requests before eligibility. The optimistic same-captured-return
replay reaches final core EXEC only 0 / 4 / 5 cycles earlier than RTL.
The measured speedup is primarily a changed DDR request calendar,
with no change to the arithmetic or addresses.

This validates same-K prefetch on the direct peer. It does not yet
validate arbitrary cross-K static prefill, Down spill scheduling, or
three P workers sharing two production channels. Keep the new mode
and the same-peer comparator separate from whole-decode claims.
`analyze_w_prefetch.py --compare w-prefetch-4.json w-prefetch-5.json
w-prefetch-6.json --out result.json` repeats paired workload checks.
Raw paths for modes 4/5 are the `...-113/.../results` sibling of the
above paths, and `...-114/.../results` for mode 6; file names carry
the mode number. `--mode MODE --archive PACK --reference JSON --out
NEW.json` independently re-verifies re-packed originals.
