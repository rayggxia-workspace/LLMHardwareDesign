# Issue27: state ownership and port service model

This experiment isolates **state placement and contention**, not a measured chip
speedup. All capacities, rates, setup latencies and scalar-function costs in
`experiment.json` are declared hypotheses. A cycle is an abstract service unit;
there is no frequency, energy, area, routed wirelength or timing calibration.

## Frozen contract

The active inventory is one matrix unit M, one vector/reduction/exp unit V,
one DMA D, two independent banks, fixed bank arbiters and three half-duplex
engine/DMA endpoints. Six possible bidirectional links (M0/M1/V0/V1/D0/D1)
have fixed widths and service rate. Fabric access is **never free**, even when
an operand and engine have the same Block label. A disabled link has no bypass.
All endpoints and arbiters remain manufactured in every connection variant.
The five-link comparisons count enabled links only, not real metal area/cost.

Each bank port supports a burst at `bank_port_bytes_per_cycle`. `1RW` allows one
read OR write; `1R1W` allows one of each; `2RW` allows two reads/writes in total.
These are different hardware sensitivity cases, not equal-area alternatives.
Each burst locks its whole object, preventing same-address simultaneous access.
Slots are distinct 64-byte-aligned fixed byte ranges, with no capacity pooling.
The capacity test reserves all slots throughout the deployment. This is a
conservative static allocation, **not** an optimal live-range memory allocator.

Transfers atomically reserve source/destination service resources for
`setup + ceil(bytes/min(bank-port,link[,external] rate))` cycles. The setup holds
all those resources. The model assumes one fixed 64-byte staging register per half-duplex endpoint
(192 bytes total, checked against the assumed one-beat-per-cycle link width);
this is not a proof of sufficient RTL FIFO depth. Full operands live in bank
slots and the explicitly bounded engine scratch. No packet queues, arbitrary
wormhole routing or asynchronous clocks are modeled. Atomic reservation removes
hold-and-wait within this model; it does not prove a streaming FIFO RTL deadlock-free.

M scratch simultaneously holds Q+K+S or P+V+T, whichever is larger. V scratch
holds all inputs and outputs of softmax or output update, whichever is larger.
The sizes use the maximum query tile across both phases, not phase-specific
hardware. Internal scratch operand access is included in the assumed operation
service rate; actual scratch ports/exp throughput need hardware calibration.
Read/compute/write phases of one transaction never overlap, and each engine
finishes all output writes before its next transaction. M and V and DMA may
overlap. This is a restricted abstract schedule class, not all possible
prefetching, double-buffering or pipelining schedules.

## State and algorithm

Q/K/V tile slots are in B0; S/P/T slots in B1. O, m and l each have two possible
bank owners; alpha shares m's owner. The eight placements use the same hardware
and transfers. O/m/l/alpha stay at their selected addresses across both phases;
no phase-specific rewiring or placement migration is credited.

For each key tile: `S = Q K^T / sqrt(d) + causal_mask`,
`m_new = max(m,rowmax(S))`, `a=exp(m-m_new)`, `P=exp(S-m_new)`,
`l_new=a*l+rowsum(P)`, `T=P V`, `O_new=a*O+T`.
Initialization O=0/m=-infinity/l=0 and final O/l use compute and real bank
accesses. Softmax is a declared V transaction, not a separate free reduction
unit. M performs QK/PV. The assumed V cost is 6*q*k+5*q scalar-equivalent work
for softmax, 2*q*d for update, q*d for normalization. These are service-model
assumptions, not instruction counts or measured transcendental throughput.

All operands and state are FP32 here. This does not freeze project INT8
attention/nonlinearity precision. PR26's W8A8/INT32 matrix recommendation does
not imply INT8 KV, probability, rescale or normalization; those contracts remain
separate. FP32 byte counts must not be divided wholesale by four.

The persistent full-model KV cache is in external backing storage. Only the
current K/V tiles reside in these banks; their DMA is charged. Q is loaded and
the normalized output is stored. We do not model KV generation/append, weights,
QKV/O projections, FFN, other heads/layers, scheduler interleaving across heads,
or host costs. No GQA cross-query-head KV reuse is credited in any arm. Causal
masked positions are computed; there is no sparse skip saving. Consequently
even the sum of these query-tile cycles is not full attention or model latency.

Observed shapes (q=32,k=32 and q=1,k=48,d=128) are bound to Issue23's archive.
The k=256 cases are explicitly unmeasured extrapolations, not holdouts.
`capture.py` separately captures real head inputs for arithmetic validation;
the service graph is a new tiled schedule, not a replay of eager execution.

## Comparisons and validation

1. Relabel split/joined with identical tasks/resources: exact zero effect.
2. Compare all eight placements within each fixed inventory. Four identical
   greedy policies are tried on every arm; report feasible upper bounds, not
   global optima. Tiny exact oracle includes deliberate idle; all four greedy
   policies can lose on the same counterexample.
3. Drop V0 or D1: static subgraph cannot improve the optimum. In this direct-link
   model the graph either remains identical or becomes infeasible. A five-link
   deployment is meaningful only if one mapping serves both phases; deleting a
   used edge is not a legal software optimization.
4. Keep capacity failures and scratch/edge failures. Bank totals are not summed
   to justify an allocation that overflows one bank.
5. Verify every schedule with independent interval/resource sweep and whole
   object RAW/WAR/WAW version checks. Code tests include invalid contracts,
   mutated addresses/dependencies/resources and independent tiny exact oracles.

The static selection sums one prefill query tile and one decode query tile with
equal weight, explicitly just a small diagnostic objective. The per-phase
mapping lower envelope is an oracle comparator, not a deployable static mapping.
Scheduling priority may change at runtime; manufactured resources and links do
not. True workload-weighted optimization and regret require whole-model traces.

## Run

From the repository root, with a clean source commit:

```powershell
python -B scripts/check_project.py
python -B -m unittest discover -s project/experiments/state_ports -p 'test_*.py' -v
python -B project/experiments/state_ports/run.py --output D:/Projects/Codex/state-port-study-20261022/run-01
```

Use a fresh output directory for each run. `--development` records dirty-source
exploration and never upgrades it into a formal result. Scientific JSON and
mtime-zero gzip are deterministic; manifests carry real runtime provenance.

## Prior work and novelty boundary

[Stream, ISQED2024](https://arxiv.org/abs/2406.09804v1) already studies transformer
fusion and scheduling across compute/memory architectures. Neither the DAG nor
capacity-aware fusion alone is a proposed new contribution here.
[FlashAttention](https://arxiv.org/abs/2205.14135v2) and the
[Triton implementation](https://triton-lang.org/main/getting-started/tutorials/06-fused-attention.html)
motivate the online m/l/O recurrence; their GPU performance is not transferred.
[Timeloop architecture](https://timeloop.csail.mit.edu/v4/input-formats/design/architecture)
separates compute/storage organization and mapping constraints. The new research
question remains what manufacture-time assets and late static connections can
achieve after fair scheduling and **actual** physical calibration. This phase
provides falsifiable machinery and placement counterexamples, not that final proof.

Actual capture uses the locked Issue23 environment (torch2.10.0+cpu, transformers4.57.6, NumPy2.5.4):

```powershell
& D:/Projects/Codex/qwen3-inference-20261022/environment/.venv/Scripts/python.exe -B project/experiments/state_ports/capture.py --weights D:/Projects/Codex/qwen3-inference-20261022/environment/weights --output D:/Projects/Codex/state-port-study-20261022/capture-01
```

Run the full unittest command above with that environment interpreter; generic Python needs NumPy and Torch for test_capture.py. Test temporary files use the task D-drive directory. Captures record all eight model hashes, installed implementation hashes, source commit/blob bindings, exact teacher-forced token IDs and archived raw head tensors. Carry-error controls with one key tile are explicitly non-applicable.
