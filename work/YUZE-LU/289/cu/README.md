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
