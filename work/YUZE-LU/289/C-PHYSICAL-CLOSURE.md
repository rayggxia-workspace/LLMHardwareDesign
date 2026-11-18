# C closure experiments (in progress)

These are diagnostics and candidates, not backend acceptance. The original 4 ns clock, new declared 50 fF IO contract, exact signal BPin geometry, macro transforms, die and upgraded G views remain the contract.

## Actual source

The v13 `distributed-parallel/3_place` checkpoint passed `signal_die_macro_exact`. Its placed, ideal-clock worst path is `loader.a_words[0]` to `loader.pd[1][31]`, arrival 7.438087 ns and slack -3.567515 ns. `c-cluster-before.rpt` retains the full paths. The arithmetic and control logic as well as long buffered connections contribute; the small isolated module result is not the parent result.

## Small placement clusters

`c-cluster*.tcl` selects cells from actual timing paths whose endpoints include loader state. It follows STA-to-OpenDB instance identity, including flattened combinational cells; it does not pretend a hierarchy name glob finds the whole cone. Disjoint groups of 8/16 cells and unclustered controls use net weights 3/10, six workers of eight CPUs on one node. Full geometry equality is required after the experiment. Only placement-estimated timing is produced.

- 119678: four clustered workers stopped at exact STA/OpenDB escaped-name mismatch. Two controls continued. No cluster result accepted.
- 119680: direct `sta_to_db_inst` resolved identity, but this tool's incremental placer explicitly skipped optimization when all instances were already placed. These redundant workers were canceled; logs retained. This is not evidence that clustering was attempted successfully.
- 119682: actual Nesterov placement via `-skip_initial_place`, six independent workers. This uses the documented small placement-cluster capability: https://openroad.readthedocs.io/en/latest/main/src/gpl/README.html . All six completed geometry-preserving diagnostics. Unclustered setup WNS -3.512380 ns, size8 -4.761012 ns, size16 -4.899891 ns; weights3/10 gave identical results within each size. Clustering worsened timing and is not promoted. The skipped-incremental controls followed by repair gave -3.132679 ns. No result is backend-accepted.

## Match arithmetic mapping between module and parent

The standalone module diagnostic used generic Yosys synthesis and ABC. The actual ORFS Nangate45 parent defaults `ADDER_MAP_FILE` to `cells_adders.v`; `extract_fa` and this techmap bind arithmetic to HA_X1/FA_X1 before ABC. The parent critical path contains many of these fixed cells. This is a verified flow difference, not yet a demonstrated explanation of all timing loss.

- 119684 failed before synthesis at the manifest's task-directory allowlist. Its separate directory and failure are retained.
- 119685 runs two fresh parent syntheses, `distributed` and `distributed-parallel`, using `cu/run-c-fresh-v14-template.sh`, with empty `ADDER_MAP_FILE`, the verified fixed-pin/PDN hooks, and unchanged timing contract. Outputs: `cu/runs/C-v14-genericadder-{distributed,distributed-parallel}`. Root owns these jobs; CU does not submit duplicates. Formal and backend checks still apply to actual final candidates.

No timing exception, clock reduction, extra pipeline stage or state change is introduced by either experiment.

## Observed no-adder result and sequentially equivalent cache candidate

Both 119685 no-adder parents reached saved post-CTS checkpoints with negative setup and hold TNS (combined setup TNS -1099.03 ns, distributed -1147.56 ns). Removing FA/HA pre-mapping did not close the real parent. After confirming the allocation contained only its two main steps and no borrowed work, root canceled further physical continuation; all checkpoints and logs remain. This is a negative result, not acceptance.

The task still requires unchanged externally observable cycle behavior. The previously selected combination-only approach was an implementation choice, not a user prohibition on auxiliary internal state. The new cached-loader candidate uses the already existing allocation edge to capture lane addresses, without adding an externally visible cycle. It introduces 512 RTL auxiliary state bits (synthesis may prune unread low bits). Independent reset-base/one-step induction proves the valid-slot address-key invariant, and exact source binding verifies every guarded use and preservation of original state updates. See `audit/C-CACHED-LOADER-REVIEW.md` and `C-cached-loader-proof-binding.json`. This does not replace actual synthesized-design and backend checks. CU owns independent cached-parent job119722; it remains in progress.
