# A/B interface X8 implementation — Issue 289

Task: https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/289

Owner: YUZE-LU. Work branch: `task/289-ab-x8`; base main `00b288f00e6d64e29ce9ba2ff2a5edb01bc58291`.
Remote root: `/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117`.

## Scope and source binding

Upgrade the actual output drivers used by archived A/B non-P connections to X8 or stronger, preserving function, clocks/SDC, block outlines, and endpoint geometry. Union: C153 + U153 + G33 + S1 = 340 outputs. Inputs remain receivers. See [audit](audit/README.md) for exact manifests and evidence.

C/U use the exact overlay `4_cts.odb` sources, which were **not** backend accepted. This task must complete their backend as well as upgrade drivers. The old pre-global access-pins hook moves BTerms and is replaced by a geometry-preserving ECO hook. B's G macro inventory uses a separate segment-C source whose timing passed but full DRC reported 106 items; it must not be represented as an accepted parent. Whether one final C implementation covers both sources requires exact G pin-shape comparison.

G/S leaf upgrades require regenerated physical/timing views and downstream parent revalidation. B's synthetic G/S pressure-test wiring is not a qualified product-level connection. Original parent connectivity is preserved during backend qualification.

## Execution record (2026-11-17)

| Job | Purpose | Observed result |
| --- | --- | --- |
|119527|G/S source driver inventory|completed; G33 and S1 are BUF_X4|
|119528|segment-C inventory|completed; comparison source only, not actual C/U routing source|
|119529|G minimal first pilot|failed unsupported `resize_cell`; preserved|
|119530|G minimal v2|replacement/legalization succeeded; stale detailed routes caused connectivity failure; cancelled, preserved|
|119531|exact overlay C/U inventory|completed; C153 BUF_X1, U135 BUF_X1 +18 BUF_X4|
|119533|eight candidates, one node, 8 CPU each|running on node14; C/U seed0 + G/S × minimal/hold03/hold08 v3|

`batch1.sbatch` and `batch1.json` freeze the batch; `dispatch.py` gives each task an exclusive Slurm step, unique output directory, and exit-code receipt. Available node memory was 371354628 kB at start. Slurm advertises only 1 MB configured memory, so a real `/proc/meminfo` available-memory guard is used; it is not a scheduler memory reservation. Total CPUs are checked against the allocation. Failed attempts are not overwritten.

G/S v3 clears obsolete ordinary signal dbWires after resizing and regenerates routes while retaining PG special wires and BPin geometry. Hold margins 0.03/0.08 ns are implementation repair targets; original acceptance constraints remain unchanged. Final BTerm-to-driver checks prevent a subsequent optimizer from silently inserting a weaker output stage.

## Acceptance

Candidate completion is not acceptance. Required evidence: exact source hashes, actual X8 coverage, preserved geometry/function, final ODB/DEF/netlist/GDS/SPEF, regenerated hard-macro views, original-frequency setup/hold/electrical checks, connectivity/PG/antenna and full unmodified DRC, and parent-block checks. Top-level A/B RC/STA is a subsequent scope and is not established by this backend task.

Current state: in progress; no candidate accepted yet. PR not yet created. Management registration remains pending (existing management PR5); Projects synchronization unverified/pending because project board configuration is absent. Review owner pending designation.

## Subsequent execution

- 119538: six S checks (3 physical, 3 LEC). All three LEC proofs passed. Physical wrappers failed before streamout because private ORFS log directories were missing; fixed separately as qualification-v2, preserving failed attempts.
- S three candidates also preserve all 265 state instances, clock/reset controls and explicit initialization attributes. This supplements the state-boundary Boolean equivalence evidence.
- 119542: seven tasks on node18, 8 CPU each: C/U original-size-start and X8-start candidates with explicit new IO constraints, plus S three physical qualification-v2 checks. Node startup available memory: 516063264 kB.
- Original U physical pilot hit RSZ-3006 because instance-level dont-touch prevented upstream repair. v3 freezes the output net instead and verifies final drive. Obsolete clock-only C step 119533.5 was cancelled after its exact srun command was verified; G steps remain running. Both failures/cancellation are retained as evidence.
- v3 C/U IO contract: 4 ns clock, 0.1 ns uncertainty; nonclock input min/max delays 0.2/0.8 ns and BUF_X2 with 50 ps source slew; output min/max delays 0.2/0.8 ns; selected 153 outputs use 50 fF, other outputs 2 fF. This is a **new engineering test environment**, not extracted top-level loading. No blanket reset false paths. Additional 500/1000 fF sensitivity checks are separate.
- Original-size-start candidates use the same optimizer restrictions as X8 candidates; the optimizer may strengthen their outputs. They must be compared by final measured cell distribution, not labeled a fixed-X1 control.
- B's selected G macro physical pins match overlay-C exactly (34/34). The hierarchy changes from `local_group.services.engine[1].genblk1.activate.leaf` to `services.engine[1].genblk1.activate.leaf`; binding is explicit in the audit.
