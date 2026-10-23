# Issue29 method review: executable bank fabric first

Read-only basis: Issue27/PR28 worktree clean at
`a3f8335287f6745bd96b9657a6279f12a142ac49`; current state_ports builder,
scheduler/limitations and final experiment report. Read AGENTS and collaboration
Skill. PR26 commit `2cd9ca15` was not in this local object database; the parent
provided its authenticated readback: W8A8 matrix operands, INT32 accumulation,
INT64 integer reference/range checks, and separate requantization/scale rules;
KV, softmax, probabilities, nonlinearities and recurrent-state formats remain
unfrozen. No other GitHub identity or ref-project was accessed.

## Decision

Prioritize a real RTL bank controller/fabric with finite queues, byte writes and
backpressure. Keep the transferred 32-bit words opaque FP32 bits. Do not divert
this stage into INT8 attention or label synthetic M/V completion delays as RTL
attention arithmetic. This phase can falsify the abstract assumption that a
single beat of staging and atomic all-resource admission predicts port behavior.
It cannot calibrate M/V throughput, an SRAM macro or PPA.

## Accepted minimal interface

- Two behavioral 1024x512-bit banks, 3 endpoints M/V/D, one clock and synchronous
  reset. Memory is NOT reset; the testbench explicitly initializes bytes used.
- Beat request: valid/ready, bank, write, beat-index addr[9:0], 512-bit data,
  64-bit byte strobes, tag[31:0]. One grant per endpoint per cycle. No request
  FIFO: a stalled source holds its meaningful request stable and valid.
- Registered per-endpoint response FIFO depths 1/2/4. Reads and write acks share
  FIFO order. One response per accepted beat; no response can be consumed at
  the same edge that accepts its request. A full FIFO may pop its old head and
  append a new response at the same edge. No extra uncredited read pipeline.
- Each bank offers mode0=one R/W, mode1=one R plus one W, or mode2=two R/W per
  edge. Any same-bank/same-row pair is prohibited, INCLUDING read/read. This
  deliberately conservative rule avoids relying on unspecified macro collisions.
- LINK_MASK bit(ep*2+bank) gates a direct connection. A masked request is never
  accepted; blocked invalid traffic must not be counted as a liveness success.
- A valid head read-response blocks that endpoint's write grant, including when
  the read response will pop this edge. Read control and read-return data may
  operate concurrently. A write-ack's data is zero/don't-care.
- Accepted reads snapshot pre-edge contents. Accepted strobed writes change only
  selected bytes at the edge; zero strobe is a no-op with one acknowledgement.
- Reset flushes response/control state and cancels outstanding responses, while
  preserving bank contents. Tests must record cancellation separately from loss.

Response-data storage alone is 3*depth*512 bits, plus 3*depth*(32+1) tag/type
bits and pointers/counts. Count this actual finite inventory; it is not the
Issue27 three-64B-staging assumption. Port modes and depths are separate hardware
sensitivity points, not iso-area alternatives. Within each point, ownership arms
must share the exact same RTL, queues, controllers and physical-port contract.

## Review of the first RTL and harness

The independent review found no blocking safety bug in the supplied RTL's FIFO
pop/push, depth1 pointer wrapping, pre-edge read snapshot, same-row filter or
read-head/write half-duplex rule. Advancing RR from the first winner is appropriate
to avoid starvation under mixed R/R/W traffic; verify fairness independently with
persistent eligible R0/R1/W2 on distinct rows and always-ready sinks.

This is a custom ready/valid interface. It is not claimed AXI-compliant: the
same-edge full-pop credit permits a combinational rsp_ready->req_ready path.
The behavioral array/read register does not establish a technology SRAM's port
latency, collision behavior, byte-enable capability, synthesized area or Fmax.

Harness generation checks are useful but data token(g,offset) is periodic in g
with period256. Current small graphs have fewer task generations; do not extend
that payload equality into an unrestricted version proof. The independent trace
checker instead tracks full integer write generation and source byte offset.

External bandwidth is a harness assumption. D writes are spaced >=2 cycles and
D read data is consumed on even cycles. Because the harness runs one complete
transfer per endpoint, retires every response before the next transfer, and has
positive setup, direction switches currently also satisfy the common two-cycle
data-beat gap. This barrier is part of the contract. If setup can become zero or
transactions overlap, separate R/W throttles no longer establish a shared 32B/c
limit. Independently audit both directions together. Fabric stress is not an
external-bandwidth performance experiment and should not use that extra rule.

## Independent trace oracle

`trace_checker.py` consumes a config line {type,mode,depth,mask} followed by every
pre-edge cycle with 3 req/rsp entries. It imports no RTL arbiter or harness logic.
It infers grants solely from request valid&&ready, maintains byte memory/known
masks and exact integer byte origins, and maintains expected FIFO response order.

It checks next-cycle presence, no loss/duplication/order changes, credit limits,
head stability under stalls, request stability, ports, same-row exclusion,
half-duplex, disabled links, byte strobes, semantic generation/offset and reset
conservation. Read data is checked only for bytes with prior observed writes;
unknown byte counts are explicit. `--require-known-reads` forbids all unknown bytes
and is appropriate for fully initialized stress. For short graph-tail reads,
semantic wstrb masks identify requested bytes; the checker demands known correct
versions for those bytes even if the other padding bytes are uninitialized.

`--external-min-gap 2` independently checks the combined D write-accept/read-consume
service spacing for program runs. Omit it for raw fabric stress. The checker does
not reproduce RR ordering or prove all possible executions live. It reports
request stall maxima; a bounded-fairness test needs its own controlled eligibility
conditions, not an arbitrary timeout with an indefinitely stalled sink.

Nine independent tests pass, including mutation controls for corrupted data/tag,
zero-cycle response, overflow, half-duplex, mask/port/row conflicts, changing a
stalled request/response, wrong integer generation despite aliased data, external
service overrun, partial/zero strobes, and reset persistence.

## Scientific controls and completion path

1. Directed exact beats: depth1 pop+push, isolated bank throughput, all-read vs
   mixed R/W saturation, same-row serialization, two-bank independence, FIFO fill
   to each exact depth and later drain. Record handshake cycles, not wall time.
2. Directed starvation fixture: persistent R0/R1/W2, distinct rows, all responses
   ready. Require every continuously eligible endpoint served within the declared
   small opportunity bound. This is independent of pointer implementation.
3. Freeze data/dependencies, initial values, M/V delay parameters, per-endpoint
   source scheduling, depth/mode/mask and common sink-stall pattern. Compare 000
   and111 ownership on prefill32 and decode48. M/V remain synthetic and bounded
   scratch contracts remain assumptions until their own RTL exists.
4. Use all four scheduling policies symmetrically before interpreting a placement
   difference. Do not call an RR arbitration or one-policy disadvantage a global
   optimum. Preserve zero/negative gains and drift from the abstract event model.
5. Keep all 24 selected nominal cycle traces and directed/random stress traces,
   source commit, generated program/index SHAs, exact Verilator/compiler options
   and versions, acceptance/response counts, FIFO peaks, wait cycles and failure
   seeds. Audit all supplied traces externally. Every behavioral difference from
   Issue27 needs a service explanation; do not force cycle equality by deleting
   real queue/handshake costs.
6. After controller validation, integrate finite engine scratch/read-compute-write
   sequencers and a separately frozen arithmetic contract. Only then attach a
   real operator and compare full projection/FFN/KV traffic. Technology SRAM and
   physical port/frequency/area characterization remains an additional milestone.

## Primary references checked

- [Arm AMBA AXI transport handshake specification](https://documentation-service.arm.com/static/651c285c15583d1bff972f94?token=):
  source validity must not depend on downstream readiness; valid payload is held
  through a stalled transfer. This informs handshake safety only; the new custom
  fabric is not asserted to implement every AXI rule.
- [Verilator executable documentation](https://verilator.org/guide/latest/exe_verilator.html):
  enable assertions in actual builds and record the installed version/options.
  The available server version is to be probed as5.042, not silently described
  using latest documentation's version. C++ drives this synchronous design, so
  no delayed RTL process or extra --timing feature is needed for the core clock.
- [cocotb timing model](https://docs.cocotb.org/en/v2.0.0/timing_model.html):
  edge triggers and settled read phases differ. The current C++ harness avoids
  this ambiguity by explicitly evaluating and recording pre-edge handshakes.

No main-worktree or remote files were modified by this review.
