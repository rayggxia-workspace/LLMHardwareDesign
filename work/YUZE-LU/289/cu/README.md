# Issue 289: exact C/U overlay output upgrade

Source: `/public/home/yuzelu/project-circuit/yzl-cu-overlay-physical-20261116/{C,U}/flow/results/nangate45/{c,u}-overlay-current/base/4_cts.odb`.
These are the actual archived C/U endpoint implementations. Their source receipt explicitly says **native detailed routing not accepted**. This task therefore completes their backend as well as upgrading output drivers; it does not substitute a different previously accepted C/U implementation.

`audit/C0-outputs.txt` and `audit/U0-outputs.txt` each select 153 outputs shared by A/B. Actual inventory: C has 153 BUF_X1; U has 135 BUF_X1 and 18 BUF_X4. `pre-global.tcl` uses `replace_cell` to BUF_X8, freezes the final stages and nets during optimization, legalizes placement, and snapshots all BPin shapes plus macro placement/M10 geometry. The historical `access-pins.tcl` is disabled because it moves BTerms away from the archived CTS endpoint geometry.

Both source SDC files specify only a 4 ns clock with 0.1 ns clock uncertainty. They contain no external load or IO delay contract. Preserving those constraints verifies the original internal timing scope; it does not prove loaded top-level cross-block timing. The final `check_setup` and readback SDC remain required evidence.

Run within a Slurm allocation:

```sh
bash /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/launch-overlay.sh C 0 8
bash /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/launch-overlay.sh U 0 8
```

Seeds 0/1/2 change router randomization, not constraints or geometry. Runs refuse to overwrite existing candidates. Source configuration references are read-only inputs; all outputs use a task-owned WORK_HOME. `manifest.py RUN` records input hashes without replacing prior evidence.

Inside an allocated ORFS container, `signoff.sh RUN` performs extracted timing/electrical, output strength, exact geometry, placement, power-grid, antenna, OpenROAD DRC and unchanged full FreePDK45 KLayout DRC reporting. `lec.sh RUN` compares original CTS and final gate-level implementations with identical hard macro abstraction boundaries. LEC is a fail-closed candidate workflow pending its first completed design run. `report.json` intentionally leaves `accepted=false` until all evidence is reviewed, including antenna/routing/constraint reports and LEC.

The initial C pilot retains the original G macro as a baseline. Final delivery must integrate the upgraded G views and rerun C-level checks; the archive's B G geometry is compatible with the overlay C instance only through the explicit audited binding.

## v3: explicit independent IO qualification

The first U pilot reached `repair_design` and failed with RSZ-3006 because freezing the complete output buffer prevented legal upstream buffer insertion. v3 retains the selected output nets, leaves the cells editable, and forbids the optimizer from choosing BUF_X1/X2/X4. This allows upstream repair while final strength is checked explicitly. Running scripts are frozen; revisions use new filenames.

`launch-overlay-v3.sh C 0 8 baseline` and `... C 0 8 x8` (and U equivalents) apply the same **new** declared IO environment: 4 ns clock, 0.1 ns clock uncertainty, 0.05 ns clock and BUF_X2 source slew, input/output delays min 0.2 ns and max 0.8 ns, ordinary outputs 2 fF, and the 153 selected outputs 50 fF. The generic delay/source methodology comes from historical qualified U timing; applying it to the exact new overlay logic and the selected 50 fF load are new qualification assumptions. No reset false path is added. This is not the actual top-level extracted RC environment.

`baseline` means original drive sizes at the start of the same optimization flow, not a promise that all final buffers remain X1. `final-drivers.tsv` records actual final cells. `signoff-v3` separately reports 500/1000 fF load sensitivity without treating those loads as extracted top-level RC.

Parent scheduler started the four v3 runs in job 119542. All four parsed the new SDC, completed selected-port processing/legalization, and reached pin access. Complete physical and timing acceptance remains pending. Full raw read-only inventories stay remote; the repository retains the 153 selected-driver rows per block.

## Current physical candidates: U v5 and C v8

v5 restores normal internal buffer choices rather than globally forbidding small buffers. A post-global-route hook records actual output and hold-buffer cell types. If selected output cells have been downsized, it upgrades only those final cells and performs incremental placement/routing plus guide regeneration before ORFS writes the database consumed by detailed routing. Final extracted timing and strength checks remain required.

C v8 incorporates the upgraded G hold03 implementation using its new Liberty, detailed LEF, and GDS. Original CTS is exported to DEF and reconstructed in a fresh database using the new G master, because the old abstract did not conservatively cover the new G routing obstructions. Rebuilding compares every die/BPin/macro pin, every component master/location/orientation/status, and all signal/power net connections against the original. DEF converts LOCKED to FIRM on import; v8 restores LOCKED only after exact identity/placement checks, then reruns the same complete comparison. Seed0 passed: 223554 components, 3758 BTerms, 256569 signal nets and 2 supply nets; 7455 LOCKED statuses were restored. No geometry or connectivity exception was introduced.

The original v6 attempt stopped before EDA work because a GDS path omitted the `qualification-v2` directory; v7 intentionally failed on the DEF placement-status roundtrip difference. Those failed runs remain separate. New G file existence and hashes were checked before v7/v8 (`new-g-preflight.sha256`). Current C v8 seeds 0/1/2 and U v5 seeds 0/1/2 run in the parent's node allocation 119595, six tasks at eight CPUs each. All full acceptance gates remain pending.

## Abstract-access correction and early timing repair

C v8 subsequently failed pin access at `G/in_fn[2]`: the default LEF abstract blocked the real access window. The original qualified abstraction method explicitly used `write_abstract_lef -bloat_factor 0`, with conservative lower-layer coverage and real GDS via-cut guards. Applying that method to upgraded G produced `parent-abstract-v3/block_v2_g.lef` (SHA256 `1064235f79bb9995a9fe01782128c334a15f7153f694223ae6363725abd45c1d`). The fresh rebuilt C database passed full-context `pin_access` with all three via-in-pin/access options set to metal10, `macroNoAp=0`, in 1m57s. C v9 uses this corrected abstract.

The old C/U CTS configurations explicitly suppressed macro clock insertion delay and were built with clock-only constraints. A diagnostic captured actual U global-route paths: incoming data reached S at 0.388884 ns while its clock arrived at 0.671665 ns, giving -0.418091 ns hold after uncertainty and library hold. Ordinary control registers also failed input-to-register hold (e.g. `release_sequence_i[25]` data at 0.271063 ns versus register clock at 0.526127 ns). Thus the failures cannot all be attributed to macro clock insertion; the new IO contract exposes many short paths against the old clock tree.

`launch-u-ctsdelay.sh U 0 8 x8` and `launch-c-ctsdelay.sh C 0 8 x8` restart from the actual `3_place` checkpoint, apply the complete unchanged new IO contract before CTS, enable macro insertion-delay modeling, and repair timing during CTS. C also reconstructs the new G master first. They compare all BPin/die/macro geometry against the archived original `4_cts` and use original `4_cts` as the final LEC reference. The first U CTS stage completed in 38 seconds and entered routing; this is progress, not final extracted acceptance or evidence isolating one CTS option's effect.

The first hold diagnostic's `-max_iterations 5` did not bound the entire hold loop in this tool version. Its `hold-before` checkpoint and detailed paths are valid evidence; do not label it a completed five-iteration experiment. `launch-hold-bounded.sh` instead uses a small explicit buffer-count limit for a diagnostic-only return. `inventory-u-cts-hold.sh` reads the already written CTS database to record actual hold cell types. Neither diagnostic relaxes the full candidate's timing requirements.
