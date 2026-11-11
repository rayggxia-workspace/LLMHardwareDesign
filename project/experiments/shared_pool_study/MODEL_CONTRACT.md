# Shared A pool conditional SystemC model

This research generator wraps the frozen R4 generator. It does not modify
production RTL, previous experiments, tensor arithmetic, tile dimensions,
context count or original private SRAM allocation. All comparisons use the
same old R4 workload and native-profile evidence. New throughput values must
come from server SystemC runs; none are prefilled here.

## API and compatibility

`generate(repo, out, r1_calibration, r2_calibration, r4_calibration)` creates an
empty output directory using the SHA-bound R4 generator, then applies
count-checked changes to three generated files. The generation receipt lists
the complete old generated hashes, protected unchanged hashes, new generator
source hashes and new generated hashes.

All previous CLI lengths remain accepted and default to pool disabled. The
full R4 CLI gains four final positional values:

```
model TRACE PROFILE VARIANT CONTEXTS SWITCH REUSE P_KIB DUAL QUARTERS POLICY R1 R2 R4 POOL_KIB FIFO_BEATS LATENCY PORT_CYCLES
```

Allowed pool values are 0, 32, 48 and 96 KiB. FIFO depth is 1, 2, 4 or 8
64-byte entries per P. Read latency is an integer 0–16 cycles after bank
service. Port service is 1, 2 or 4 core cycles per 64-byte access. The main
comparison holds FIFO=4, latency=2 and port=1 fixed at every capacity.

Pool zero must reproduce the entire frozen R4 RESULT after deleting only
`shared_pool_study`. Original arithmetic, flow counters and timing fields
are part of that regression, not only token/s.

## Lifetime and storage

Eligible operations are streamed native-S32 matrix operations with static
layout 0, one batch, 1–8 rows and 32-bit A. The operation must use two P.
Input producers and input flushes run unchanged before pool initialization.
There is no direct U→pool handoff and no free format conversion.

Each row has a 64-byte-aligned pool stride. When all rows fit, the entire K
range is resident, including a final partial row beat. Otherwise every row
gets an equal prefix rounded down to the existing cfg.k grain. Capacity
includes padding. In the main evaluation cfg.k is 256. Filling repeats once
per eligible matrix invocation. No cross-operation caching or replacement
policy is assumed.

Initialization issues at most two 1024-byte DDR descriptors, alternates
the two existing DDR channels, and obeys all original channel credits,
alignment, row misses and bandwidth service. Each returned valid DDR beat
reserves shared SRAM write service instead of local P SRAM write service.
A misaligned DDR beat may cause a partial shared-line write and the next
beat may write another nonoverlapping part of that line; both pay service.
The pool becomes readable only after every requested byte and shared write
ACK completes. A bounded byte-valid audit map rejects duplicated fill
bytes, missing payload, writes into padding and premature activation.

Both P share the same immutable A generation and independently read it.
There is no broadcast discount. The generation cannot change until both
workers and their FIFO entries have drained. Original local A resident and
prefix reuse remain in place for the uncovered range. Their bookkeeping
of actually loaded/reused bytes excludes bytes already supplied by the
shared pool; their original capacity reservations remain conservative.

## Physical service and FIFO model

The shared fabric carries one 64-byte line per PORT_CYCLES. Four 128-bit
1RW lane banks operate in lockstep for each line; every line uses all four
lanes. Reads and writes compete for the same fabric and lane bank service.
This is a fixed-width bank organization, not four independent 64-byte ports.
All capacities have the same fabric and bank widths. Per-bank service and
global queueing are recorded. Initialization finishes before P computation,
so fill and compute do not overlap in this first model.

Each P has a separate finite FIFO. An entry's credit is held from request
issue through read response latency until the feeder consumes its final
valid byte. A FIFO entry therefore includes data in flight. A producer
cannot issue with all credits occupied. Each P issues at most one request
per cycle, while global 1RW conflicts can further delay service. The
feeder consumes at most 32 valid bytes per core cycle; short fragments use
one cycle. Partial-row and prefix boundary masks retain exact byte ranges.

The implementation uses an event-time credit queue rather than spawning a
SystemC process for each beat. It yields the actual P SystemC process at
request-interval and credit-release boundaries; two P therefore compete
through the real shared calendar. Every queued release is the computed
consumer completion time, and occupancy is checked against the configured
depth. The algorithm does not issue an unbounded list of future reads.
There is no next-tile A prefetch in this version.

After existing A/B DDR ACKs, the remaining local A plus B receives the
original combined local S-read service, calculated by rounding the combined
remaining byte count. Shared A avoids both the old DDR→local-S write and
the old local-S→A-adapter read. It still pays pool read service, response
latency, finite FIFO waits and the A feeder's original 32 B/cycle demand.
The original M/adapter work counters remain unchanged. Local B service,
M/adapter work and shared A feeder completion overlap using the latest of
their completion times, then the original M tail is paid. Shared A feeder
time is not added serially to the full original adapter time.

For a tile crossing the shared-prefix boundary, the local A suffix waits
for the combined remaining local A/B read completion before feeder
consumption. This conservative mixed-tile join is explicit; full shared
and full local tiles retain their respective parallel timing contracts.
Nonaligned source-row fills use byte masks: only the valid intersection
of each DDR beat and its descriptor is written at the translated pool
address. Each partial line write pays a full shared-port service. This is
a model requirement for a masked fill bridge, not evidence that current
RTL already has that bridge.

The FIFO is a timing/address model. It does not store real tensor payload.
Optional pure callbacks report each issue and each at-most-32-byte consumed
segment. A probe-only `consumer_ready_at` callback can delay consumption,
which delays credit release and subsequent producer issues. Numerical
oracle tests can bind actual input values to these reported addresses;
that supports address/ordering/lifetime evidence and is not a full LLM RTL
numerical proof. Callback observers report planned event times and must not
call SystemC wait themselves.

## Ledger and limitations

The new RESULT key includes capacity, FIFO and port settings; fill calls,
payload and descriptors; line read/write counts; global and per-bank
service; each P's FIFO peak, credit waits, port waits, consumed bytes and
local A read bypass; original A DDR bytes removed and local SRAM service
removed; and live-generation/worker state. All live state must be zero at
the final result. Original non-A logical and bus traffic is invariant.

Pool bytes consume area in addition to the unchanged two 16-KiB P stores
and 16-KiB U store. FIFO payload adds 2 × FIFO_BEATS × 64 bytes. Arbitration,
valid masks, crossbar/wires and controller area are not physically measured.
Timing uses the old 300-MHz evaluation frequency and does not establish
physical closure at that frequency. Capacity, bank service and response
latency are independently adjustable, so a capacity gain must not silently
include extra bandwidth.

Server validation is required: complete pool-zero regression, four old
workloads × two port layers × four capacities, flow/service conservation,
dual-P FIFO and epoch probes, numerical address oracle, invalid CLI checks,
and selected FIFO/latency/port sensitivities. Local generation alone is not
performance or numerical validation.
