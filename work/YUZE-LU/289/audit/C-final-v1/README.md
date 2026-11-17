# C independent final verification — prepared, not accepted

All paths below are relative to remote issue root `/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117`. U's accepted package is frozen and is not modified by these scripts.

Inputs remain candidate-specific. Current actual routing candidate is `cu/runs/C-v20-native-clock4` on the cached C-v16 source chain. `C-v21-shared-A` is a separate actual-parent experiment; it must use its own synthesis/RTL proof chain. Do not apply v18 cached receipts to shared-A merely because interfaces or state counts match.

## Ready commands

Each script uses an independent8-CPU Slurm allocation and writes a new candidate-specific directory. Do not submit these against an unfinished or changing candidate.

1. `sbatch audit/C-final-v1/extract-consistency.sbatch <exact-run>`: single isolated extraction, no PG precheck cache, exact before/after physical geometry and macro OBS, actual via metadata, all-net layer material comparison, uncached post-extraction PG. Retains all failed evidence; unknown NDR/route encodings fail. A successful result must still be linked to the original delivery GDS and final qualified SPEF before release.
2. `sbatch audit/C-final-v1/independent.sbatch <exact-run>`: frozen source/config/actual RTL and library/view hashes; fresh setup/hold/cap/slew/fanout and recovery/removal; exact BUF_X8 on all153 selected outputs; both PG rails; original overlay4CTS die/signal BPin/macro position and all-layer macro pin geometry; independently reconstructed IO contract. PG BPin changes are listed and require root review. Fresh `final-from-odb.v` is the authoritative input for final functional proof; if it differs from the saved netlist, the difference must be resolved before release.
3. `sbatch audit/C-final-v1/export-model.sbatch <exact-run>`: refuses nonzero timing/electrical/async violations; exports Liberty plus raw zero-bloat LEF; fresh OpenROAD and Yosys reload; separate parent LEF with conservative lower-metal cover and actual hierarchical via6–9 cuts; independently validates all pin geometry, upper OBS and actual cut coverage.

Full unchanged foundry deck is owned by root. Final functional proof is owned by loader_review: `c-formal.py <exact-run> <new-proof-out> <actual1_synth_lec.v> <fresh-final-from-odb.v>` then `c-control-tags.py <new-proof-out>`. Explicit cached-lifecycle and optional shared-A arithmetic/source-to-actual-synthesis proof chains must precede the final same-candidate synthesis-to-postroute proof. Do not reuse U's12080-state assertion or assume the earlier C state count.

Final aggregation must explicitly bind the exact candidate ODB/DEF/V/GDS/SDC/SPEF, original full deck and report, functional chain and exact final netlist, before/after manifests and frozen checker scripts, raw and parent model receipts. Nonzero native markers need concrete baseline/material resolution; no silent waiver. All new PG boundary changes need an explicit reviewed disposition.

## Completed preparation check

Job119889 independently loaded actual `C-v20-native-clock4/route-source.sdc` and the expected contract on the same frozen candidate ODB. All11270 noncomment normalized commands matched. Source hashes were unchanged. Receipt: `contract-smoke-v20/receipt.json` (small local copy under `evidence/`). This verifies the constraint checker, not final timing or physical acceptance.

Original C base SDC only supplies4ns clock and0.1ns uncertainty. Engineering IO contract adds50ps clock/input transition, BUF_X2 input drive,0.2–0.8ns input/output delays,50fF selected outputs and2fF others. No false paths, multicycle paths or disabled timing are introduced.

Likely physical review priorities are actual postroute GDS antenna and upper-metal/via interactions around macros. S/E actual cut guards and the accepted new G abstract already exist in the current implementation; inspect actual R/dot/bank context before proposing changes. Do not insert speculative diodes or declare RCX geometry consistency merely because C has no active NDR.
