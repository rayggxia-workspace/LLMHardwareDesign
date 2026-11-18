# A/B interface X8 implementation — Issue 289

Latest C continuation: [actual C-v28 checkpoint](audit/C-v28-ACTUAL-STATUS.md) and [continuation record](CONTINUE.md). C remains unaccepted. The completed original full-deck v27 baseline has42 violations; [exact comparison](audit/full-C-v27-joint-e20-h30/focused-comparison.json) matches all41 earlier focused markers and identifies the remaining isolated OAI221_X4 marker. A final C needs its own complete original-deck pass and extracted timing closure.

## Accepted backend packages

F with the accepted **S minimal-localv4** X8 leaf has completed backend acceptance. Evidence: [accepted-parent.json](audit/evidence/F/accepted-parent.json). Nangate45 TT, nominal300MHz, original0.1ns uncertainty; actual serialized period3.3333ns. Setup+0.221605405ns, hold+0.002453537ns. Timing/electrical violation counts, full foundry GDS DRC and antenna are zero; PG, formal equivalence, state/control preservation and signal/power BPin/macro geometry checks pass. Native-route checker markers are40 exact historical matches plus4 individually proven same-net physical macro contacts; two old markers disappear. Do not label this checker report empty. Hold margin is only2.454ps and this does not establish other PVT corners or A/B top RC timing.

Frozen F package: `/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/gs/candidate-S-minimal-localv4/parent-F-eco-h20-v4/release/`. Accepted receipt SHA256 `60cbc5d7574e07d8fdfbd7646cfbbe25785c3821ead2da9a4967d40b34c0aa5e`.

U has completed block backend checks in `candidate-U-v19-preserved`. All 153 selected output drivers are `BUF_X8`. At Nangate45 TT, 250 MHz, 0.1 ns uncertainty and 50 fF on the selected outputs, setup slack is +0.078050904 ns and hold slack is +0.003471112 ns. The five timing/electrical violation counts and the complete unchanged FreePDK45 DRC are zero. Both PG rails, formal data/state/control, signal pin/die/macro geometry, and the Liberty and physical LEF views passed. The checked release preserves the qualified GDS and uses a SPEF extracted from an independently proven equal-material DEF. [Acceptance receipt](audit/evidence/U/accepted-parent.json).

Frozen U manifest and acceptance: `/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/release-candidate-U-v19-preserved/`. Accepted receipt SHA256 `cb34cbc8badd0d2d9e8d0d259ce22f512bc9aea15ed4aae365f1e1c322703771`. C backend verification is in progress.

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

Current state: in progress; leaf results below are accepted only at leaf scope. [Draft PR290](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/290) tracks implementation. Management registration remains pending (existing management PR5); Projects synchronization unverified/pending because project board configuration is absent. Review owner pending designation.

## Subsequent execution

- 119538: six S checks (3 physical, 3 LEC). All three LEC proofs passed. Physical wrappers failed before streamout because private ORFS log directories were missing; fixed separately as qualification-v2, preserving failed attempts.
- S three candidates also preserve all 265 state instances, clock/reset controls and explicit initialization attributes. This supplements the state-boundary Boolean equivalence evidence.
- 119542: seven tasks on node18, 8 CPU each: C/U original-size-start and X8-start candidates with explicit new IO constraints, plus S three physical qualification-v2 checks. Node startup available memory: 516063264 kB.
- Original U physical pilot hit RSZ-3006 because instance-level dont-touch prevented upstream repair. v3 freezes the output net instead and verifies final drive. Obsolete clock-only C step 119533.5 was cancelled after its exact srun command was verified; G steps remain running. Both failures/cancellation are retained as evidence.
- v3 C/U IO contract: 4 ns clock, 0.1 ns uncertainty; nonclock input min/max delays 0.2/0.8 ns and BUF_X2 with 50 ps source slew; output min/max delays 0.2/0.8 ns; selected 153 outputs use 50 fF, other outputs 2 fF. This is a **new engineering test environment**, not extracted top-level loading. No blanket reset false paths. Additional 500/1000 fF sensitivity checks are separate.
- Original-size-start candidates use the same optimizer restrictions as X8 candidates; the optimizer may strengthen their outputs. They must be compared by final measured cell distribution, not labeled a fixed-X1 control.
- B's selected G macro physical pins match overlay-C exactly (34/34). The hierarchy changes from `local_group.services.engine[1].genblk1.activate.leaf` to `services.engine[1].genblk1.activate.leaf`; binding is explicit in the audit.

## Leaf milestone and parent work

G hold03 and the three S candidates have hash-bound accepted-leaf receipts under `gs/evidence/`. G hold03 at 300 MHz has setup/hold +0.525632679/+0.028771570 ns; preferred S hold08 has +0.174261272/+0.058656693 ns. Both complete GDS deck and independent native DRC are clear; exact timing/electrical counts, PG, antenna, state-boundary LEC, state/control-cone preservation and target X8 assertions pass. G hold08 was rejected despite a clear GDS deck because independent native DRC found two violations. Parent integration and real top-line timing remain separate.

New leaf abstracts have the same die and pins but different OBS. Explicit new-master reconstruction is required. Detailed abstracts are exported separately from the more conservative bloated originals. C rebuild checks 223554 instances, all BPin/macro geometry and full net connectivity; DEF's 7455 LOCKED→FIRM tap status conversions are explicitly restored, then equality is asserted. v6 failed an incorrect GDS path; v7 exposed the DEF status conversion; v8 passes the full reconstruction gate. Failures are retained.

Job119595 initially launched C-v6 and U-v5 (three seeds each); failed C steps were replaced by C-v8 steps inside the same allocation after pilot success. U-v5 permits ordinary weak internal buffers and ensures selected final outputs are X8; it supersedes the unnecessarily broad BUF_X1/X2/X4 optimizer exclusion. C uses the accepted G hold03 detailed LEF, new Liberty and actual GDS.

F with new S initially has 2/1/1 hold violations for minimal/hold03/hold08; those parent attempts are not accepted. F ECO v2 h20/h50/h80 rebuild from the new S detailed LEF, restore original fixed statuses, and assert 170438 instances plus 74809 nets before repair. The h20 strategy initially needs only two hold buffers. All final physical/function/timing checks remain required.

Obsolete X8 steps (119542.1/.2 and 119586.2/.4) were ended after inspecting their exact srun commands. Original-size-start C/U comparisons remain. New C/U candidates and F repair steps continue; no parent/block acceptance is claimed.
