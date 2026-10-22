# Fixed-state/port experiment contract (proposal, 2026-10-22)

The first result should be a falsifiable latency/queueing mechanism under an
explicit abstract microarchitecture. It is not a PPA result, a calibrated cycle
prediction for ACT/MXU, or proof that a chosen connection graph can be fabricated.
Issue25/PR26 benchmark selection is outside this note's scope.

## Most discriminating question

With the same matrix, vector and reduction engines, bank inventory, bank ports,
engine-local registers, HBM service and static-link inventory, can one static
state-placement/connection deployment improve BOTH a prefill and its subsequent
decode, after the fixed baseline receives the same software scheduling search?
Where is the gain zero or negative? Use a Pareto pair (prefill cycles, decode
cycles) plus feasibility/slack. Do not hide a regression with an arbitrary
weighted objective or select a different physical graph for each phase.

Freeze an abstract hardware manifest H. A candidate deployment D consists only
of a legal static edge subset/binding and a phase-invariant placement rule for
named states. Freeze D once, then run the entire prefill/decode sequence.
Phase-specific instructions/tile schedules are legal only if the identical
controller supports them for every D. Instructions are not late-custom wires.

## Two separate comparisons

1. Keep the entire fabric fixed; change state placement only. This establishes
   whether ownership changes port contention, rather than merely byte totals.
2. On the same frozen active inventory, compare static legal connection graphs
   with the same link count, total link bandwidth, endpoint/degree constraints
   and endpoint adapters. Optimize legal placement and schedules symmetrically.

If a bank is manufactured as a single-master direct interface, connecting more
passive wires does not create a multi-master arbiter, request mux, address
generator, router or DMA. Those must be pre-existing frozen active assets. Count
them and their request/response resources in H. An abstract reachability matrix
is not evidence of this physical capability. A baseline with a complete fabric
may already support every beneficial placement: the corresponding late-custom
gain should be zero, not excluded from the study.

## States and valid ownership alternatives

All compute ownership stays fixed: M executes QK/PV and GEMMs; V executes exp,
SiLU, elementwise scale/add/divide; R executes row max/sum (or share its V issue
resource if the hardware has no independent R engine). Putting O in M's bank
does not give M free vector rescaling.

Attention uses the same FA2-style unnormalized recurrence in every placement:

    m_j = max(m_(j-1), rowmax(S_j))
    alpha_j = exp(m_(j-1)-m_j)
    P_j = exp(S_j-m_j)
    l_j = alpha_j*l_(j-1) + rowsum(P_j)
    T_j = P_j V_j
    O_j = alpha_j*O_(j-1) + T_j
    output = O_last/l_last

The source for the recurrence is [FlashAttention-2, Algorithm 1](https://tridao.me/publications/flash2/flash2.pdf).
It supports this algebra and identifies non-matmul work/communication as relevant;
its GPU speedups do not predict our hardware. FP32 state arithmetic in this study
must match the existing numerical oracle/real Qwen shape contract. New reduced
precision requires its own correctness contract and compute/memory parameters.

Prespecify a small placement inventory rather than permitting arbitrary free
copies:

- V/R-side O,m,l; M-side KV. T_j crosses to V and P_j returns to M, with all bank
  reads/writes, link resources and finite staging included.
- M-side O/KV, V/R-side m,l. V still reads/rescales/writes O via an existing legal
  bank interface. This may remove an interbank copy yet worsen KV/O port conflict.
- KV head/page coloring across the same two banks, with O bound to a fixed bank
  rule. The coloring cannot change between prefill and decode for free. GQA shares
  one KV group over its Q heads only when the modeled buffering/broadcast supports
  it; otherwise each actual fetch is charged.

KV is persistent across all layers and phases; O/m/l is ephemeral over one query
tile's KV loop; FFN G/U/Z tiles and output partial sums have different, shorter
lifetimes. A serial attention->FFN layer must NOT add non-overlapping O and FFN
workspaces as simultaneous peak memory. A pipelined schedule must prove overlap
with event lifetimes and include additional simultaneously live buffers.

Use all-model KV backing storage. If SRAM holds only one layer's KV, explicitly
model HBM persistence, per-layer DMA and dirty append writeback. Do not replace a
28-layer persistent cache with the current layer's SRAM footprint. A model may
instead declare it is a current-layer microkernel experiment and avoid claiming
whole-model inference latency. Weight streams must be included in the same HBM
and bank queues, or results must state that the omitted common traffic can alter
overlap and ranking (a common scalar latency added afterward is insufficient).

## Executable event semantics

Use integer cycles and half-open [start,end) reservations. Each task has a unique
ID, operation class, input/output versions, predecessor IDs, duration, required
resources, and allocation/release events. Every event schedule is saved for
independent replay. A resource is an explicitly named unit-capacity port/link or
compute issue slot; multiport banks have distinct ports, not an unlimited aggregate
bandwidth. Use 1RW and 1R1W as separate hardware sensitivity points, holding that
inventory identical across deployment arms inside each point.

A transfer is split into fixed-size nonpreemptive bursts. A burst duration is
startup + ceil(bytes/bandwidth); if a datapath has different sustained link and
memory rates, use separate staged events or an explicitly documented streaming
service rule. A DMA copy consumes source read service, destination write service,
the selected path and DMA service. HBM traffic also consumes the common HBM
queue/controller/channel. 1RW reads and writes contend for the same token. Two
1R1W banks do not imply free transfers: source R, destination W and path must all
be available. Acquire resources atomically; partial resource acquisition otherwise
introduces accidental simulator deadlocks.

Do NOT reserve SRAM ports for an entire long GEMM unless that is a documented
microarchitecture. For an initial explicit load/compute/store model, tile inputs
are fetched into finite, frozen engine-local storage; M/V/R then execute; outputs
are drained. Count those local operand/accumulator buffers and ping-pong copies
in H. If streaming through compute is modeled later, generate per-cycle/beat
operand requests and allow compute to stall on service; ceil(FLOPs/peak) alone
cannot infer utilization of a real systolic array, especially decode GEMV.

O_j must depend on O_(j-1), alpha_j and T_j; l_j depends on l_(j-1). Do not
parallelize updates to the same row state. Different query tiles/heads can overlap
only if their simultaneous live state fits. P_j and S_j may be overwritten only
after their last consumers. Store versions and reader counts to verify this.

Allocate a producer's entire output region before the producing task starts;
release after all consumers complete. Keep destination/staging reservations
during in-flight transfers. A capacity-infeasible deployment is rejected or uses
an explicit common spill policy with spill events, never an implicit free HBM
escape. Verify every bank's active allocated-byte sum at every event boundary.

Use one deterministic scheduler (e.g. critical-path priority, ID tie-break) across
arms, then the same finite menu of schedule priorities/tile orders per arm. Report
both fixed-policy latency and best latency under the identical declared search
budget. A search outcome is not a global optimum. Schedule interactions mean
removing a resource constraint can perversely worsen a greedy schedule: tiny
exact oracles and common-search controls are needed before causal claims.

## Initial campaign, deliberately small

Use Issue23's measured Qwen dimensions/semantic checks as shape provenance, not
CPU time as a hardware calibration. Reuse existing prefill32+decode16 and
prefill96+decode8 dimensions; do not rerun weights solely to create event tasks.
Use one explicit attention schedule (e.g. Br=8 prefill / Br=1 decode, Bc=16) and
one FFN hidden tile at first. The trace supplies shapes/state, not an actual
hardware memory trace. The selected hardware access schedule is synthesized and
must be labeled as such.

For a tractable first campaign choose 2/3 legal static graphs x 3 placements x
2 workloads x 3 hardware ratios (bank/HBM service vs compute) x 2 port models.
Prune impossible placements; keep infeasibility evidence rather than silently
omitting them. Lock compute, shape, schedule, tile sizes, total memory and link
budgets inside every paired comparison. A later independent tile sweep must be
applied to every graph, including the fixed baseline. Do not derive physical
benefit from a smaller software burst unless burst length is symmetrically tuned.

Prespecify the most informative outcomes:

1. Same arithmetic and same transferred bytes, different port queueing/makespan.
2. Fewer transferred bytes, no cycles saved because compute or HBM remains critical.
3. O collocation reduces a copy but worsens decode KV/O port contention.
4. One deployment wins prefill and loses decode; report the Pareto tradeoff.
5. Fixed full-connectivity baseline plus software placement reaches the best
   candidate; measured late-custom benefit is zero under this contract.
6. A candidate gain disappears with a common better schedule, faster bank port,
   lower compute throughput, or full traffic included. Preserve the counterexample.

## Metrics and independent checks

Report per phase and combined sequence: makespan, TTFT-like microkernel boundary
(not end-to-end token latency), per-engine busy/idle, critical chain, resource
service and queue wait, bank live-byte peaks, spill traffic, and link/HBM bytes.
Classify a ready task's blocking resource set; do not sum overlapping wait reasons
as independent additive causal delays. Supply resource-load and dependency-path
lower bounds. Any claimed optimum is limited to exact tiny cases or a proved
lower-bound match. Save a Gantt/event table for the two most informative cases.

An independent time-indexed exhaustive solver should cover <=8 tasks and unit
ports; it must allow deliberate idling. It checks the event scheduler on hand
instances, not an entire real model. Test signed resource direction (1RW vs
separate R/W), burst boundaries, simultaneous completion/start, DMA two-ended
reservation, append-after-read/version hazards, live-buffer capacity, and
dependency cycles. Validate emitted schedules separately for duration,
predecessors, overlap and complete task coverage. Test exact lower-bound cases
and at least one case where greedy is suboptimal, to avoid testing two copies of
the same scheduling assumption.

## Parameters: evidence, calibration and unknowns

- Proven from Issue23/21: dimensions, GQA groups, head_dim=128, tensor precision
  of that run, causal positions, algebraic equivalence within stated tolerances.
- Derived: operation counts, tile/state bytes, task dependencies for the selected
  schedule, version lifetimes, resource service demand under the stated model.
- Hardware hypotheses: M/V/R issue/latency/throughput, local registers, bank port
  protocol, bank/NoC startup and service rates, FIFO depths, HBM queue/burst model,
  clock, routing feasibility. Use labeled sensitivity ranges, not numbers claimed
  to come from CPU inference or a macro LEF.
- Calibratable next: isolated GEMM/GEMV/vector/reduce cycle traces in RTL; SRAM
  controller/bank-port traces; DMA burst service; documented HBM controller model.
  Real LEF pin geometry neither supplies these timing/service rates nor proves
  those interfaces implement the modeled operations.

## Reuse assessment from primary sources

- [Timeloop v4 architecture](https://timeloop.csail.mit.edu/v4/input-formats/design/architecture)
  supports explicit shared/read/write bandwidth and network fill/drain attributes;
  [constraints](https://timeloop.csail.mit.edu/previous_versions/timeloop-accelergy-v3/timeloop/input-formats/design/constraints)
  can restrict mappings. Useful for compute/memory mapping and traffic sanity
  checks; it is not automatically an oracle for arbitrary cross-engine event
  dependencies and bank-controller queues.
- [ZigZag official hardware documentation](https://kuleuven-micas.github.io/zigzag/hardware.html)
  has explicit r/w/rw ports and operand-port allocation. The cited documentation
  explicitly notes that memory access latency is not actively used there.
  Reuse port/operand abstractions and mapping estimates; do not label its output
  as independently cycle-accurate for the proposed shared-port model.
- [Stream transformer paper, ISQED 2024](https://arxiv.org/html/2406.09804v1)
  already studies fine-grained transformer fusion, multiple accelerators and
  schedule-dependent active memory. Its scheduling/memory machinery is the closest
  starting point. Merely adding fusion/placement/scheduling is not new; the
  frozen-manufacturing inventory and phase-invariant wiring question is distinct
  only if actually enforced and compared against its software mapping freedoms.
- [SCALE-Sim v2 documentation](https://scale-sim-project.readthedocs.io/en/latest/)
  provides GEMM-oriented cycle and SRAM/DRAM traces. [SCALE-Sim v3 paper](https://arxiv.org/html/2504.15377v1)
  adds multi-core, layout/bank-conflict and finite-queue DRAM modeling. Its matrix
  service traces are promising calibration/cross-check inputs. A wrapper is still
  required for our V/R, online-state dependencies and static-edge constraints;
  the paper's validation does not validate that wrapper or our hypothetical HW.
- [SimPy official shared resources](https://simpy.readthedocs.io/en/stable/topical_guides/resources.html)
  supplies event queues and finite Resource/PriorityResource primitives, not
  accelerator semantics or simultaneous multi-resource atomic admission. A small
  stdlib event engine may be easier to independently audit initially. Do not
  accidentally use preemption for nonpreemptive hardware bursts.
- [Accelergy original paper](https://accelergy.mit.edu/paper.pdf)
  converts characterized per-action costs and counts into energy estimates. It
  is a later option after actions and SRAM/controller characterization exist,
  not a source of latency or an energy claim without valid ERTs.

No external simulator was installed or executed for this note. Sources were
browsed as primary documentation/papers on 2026-10-22, not downloaded to the repo.
