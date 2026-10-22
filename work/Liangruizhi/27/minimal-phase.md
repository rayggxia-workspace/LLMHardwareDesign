# Minimal phase ready for implementation

Use the same fully connected, explicitly costed fabric for all arms in this phase.
This is an ownership/port experiment, not yet a late-custom interconnect benefit.
There are 8 static deployments: (bank(O),bank(m),bank(l)) in {B0,B1}^3, alpha
follows m. Select a deployment once for both prefill/decode. Q/K/V slots are B0;
S/P/T slots are B1. Bank capacities, port types/service rates, M/V (and any
independent R) units, internal scratch/RF, fabric and HBM inventory stay frozen.

For one query-row tile with r rows, KV tile c rows and head dimension d=128,
all states are FP32. Buffers Q,K,V,O,T have respectively r*d,c*d,c*d,r*d,r*d
elements; S/P have r*c; m/l/alpha have r. Tail tile dimensions use actual valid
elements or a declared common padded schedule, consistently in all arms.

| Transaction | Read versions | Compute (fixed engine) | Write versions |
|---|---|---|---|
| init | no data input | fixed constant generator if pre-existing | O_0=0,m_0=-inf,l_0=0 |
| DMA_i | K_i,V_i in persistent external backing | DMA/controller | Kslot_i,Vslot_i |
| QK_i | Q,Kslot_i | M: r*c*d MACs | S_i |
| softmax_i | S_i,m_(i-1),l_(i-1) | R/V: rowmax, m_i, alpha_i, exp P_i, rowsum, l_i | P_i,m_i,l_i,alpha_i |
| PV_i | P_i,Vslot_i | M: r*c*d MACs | T_i |
| update_i | O_(i-1),alpha_i,T_i | V: O_i=alpha_i*O_(i-1)+T_i | O_i |
| final | O_last,l_last | V: O/l | final output |

The table's reads and writes are real transactions, including m/l and init/final
state service. A constant initializer is not an unspecified free write port.
The controller supports FP32 handling of initial -inf; no data-dependent cycle
shortcut is inferred from values. Masked tiles must use one common policy (dense
masked compute, or proved wholly masked-tile skipping) across all deployments.
GQA KV reads are not repeated or broadcast for free: explicitly choose a query
head/group schedule and charge the actual selected reuse/buffering.

Every transaction is read-operands -> compute -> write-results. Inputs/outputs
reside in finite frozen engine-local scratch during the transaction, so bank ports
can be released after reads while compute proceeds. For the simplest single
buffer transaction class, enforce M order QK_i -> PV_i -> QK_(i+1) and V order
softmax_i -> update_i -> softmax_(i+1), from the previous transaction's LAST WRITE
completion to the next transaction's FIRST READ. If only compute nodes are ordered,
the schedule permits prefetch/drain overlap and requires extra scratch accounting.

DMA may overlap M/V when every endpoint port/link and destination slot is free.
For an initial conservative atomic KV-tile DMA, next DMA waits for both previous
K and V reads. If K and V are separate DMA transfers, release them independently.
The modeled external persistent KV store and weight traffic need the same shared
HBM service; omitting weights limits the result to this declared microkernel.

## Dependencies that cannot be inferred from the compute engine alone

- RAW: QK waits for K DMA; softmax waits for S; PV waits for P and V DMA;
  update waits for T, alpha and old O; final waits for final O and l writes.
- WAR on reusable slots: next K DMA write waits for QK_i's K read completion;
  next V DMA write waits for PV_i's V read completion; S_(i+1) write waits for
  softmax_i's S read completion; P_(i+1) write waits for PV_i's P read completion;
  T_(i+1) write waits for update_i's T read completion; alpha_(i+1) write waits
  for update_i's alpha read completion.
- WAW/state recurrence: m/l updates form an ordered row-state chain; O updates
  form an ordered row-state chain. Initial/final writes also use those slots.
- A DMA write completes only when the bank has received the entire burst, not
  when the DMA request was submitted. Readers must retain the source through
  completion of their corresponding read burst, not just its issue cycle.

These are semantic hazards. Some are automatically implied by the deliberately
strong whole-transaction order, but keep named hazard edges in the task generator
or validator so later pipelining cannot silently remove them.

## Capacity and meaning of a result

Reserve all shared slots over their declared allocation intervals. O/m/l/alpha
span the complete query-tile loop; Q spans all of its QK readers. Persisted KV
backing spans phases; SRAM K/V tile slots are temporary. S/P/T slots cannot be
released at compute completion while their consumers or drains are outstanding.
Fixed transaction scratch is the maximum simultaneously live INPUT+OUTPUT across
all transactions and all phases of this same deployment inventory: e.g. QK has
Q+K+S, PV has P+V+T, update has oldO+alpha+T+newO. A bank in-place update does
not eliminate the staged old/new RF values. Count every fixed RF byte separately
from the two shared banks. If R is part of V, do not also claim an independent
free reduction engine or overlap its work with V.

Use hypothetical FP32 M/V/R rates with units, compute startup and explicit service
rates; sweep ratios. No INT8 peak-rate assumption or real-PPA label. The strongest
first findings are: fixed byte/compute counts but distinct port queues/makespans;
or a reduced-copy placement with no gain/worse contention. A greedy schedule
can be inferior to another legal schedule on the SAME hardware, so a schedule
improvement does not imply a wiring benefit.

## Independent executable small checks

`port_oracle.py` provides a greedy event engine, independent integer-cycle BFS
oracle (<=8 tasks, permits intentional idling), and independent interval audit.
It includes complete live-buffer checks and retained KV-like state. It does not
claim a whole attention model's exact optimum. `test_port_oracle.py` has six
tests and passes under stdlib-only Python:

    D:/APP/Python/python.exe -B -m unittest -v test_port_oracle

Hand results: equal 8 cycles of port demand, collocated=14 vs separated=10;
greedy-counterexample=16 vs exact12; DMA source+destination+link=6; 8B simultaneous
temporary capacity feasible vs 7B infeasible. These are normalized artificial
examples, not measured hardware cycles or model speedups.

Primary-source bibliography and the broader contract are in experiment-contract.md.
