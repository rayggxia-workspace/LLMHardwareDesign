C43 pipeline read-only review
=============================

Reviewed the current v1 scripts only; no live files or plans were modified. The v1 launcher still selects the nine-cell `C-actual-seven-size-v1` plan, not the running v3 result. This review is preparation, not backend acceptance.

The actual-source ODB assertion is correct: `6cc21b934b59858cbbee2bfe9028529746dc663e5fd61ceb1bf8f0e8b6a5cdef`. Both currently referenced C38 and C40 SDC files are byte-identical (`a16b8b380ef12239d4fa2495b3a8832351c321e19467609e67866cacef966270`). The route launcher should nevertheless use the prepared source's frozen SDC or explicitly assert that equality, instead of silently selecting C38 by path.

Required corrections before a new plan runs
------------------------------------------

1. The prepare TCL unconditionally locks all five long-wire buffers and requires their locations to remain exact, even if they are in the actual resize plan. A widened `i289_pd_mid` or another such buffer can therefore remain illegally overlapping. Exclude only actually resized names from that special lock and its unchanged-position assertion. Set eligible resized standard cells to PLACED before detailed placement, retaining original status metadata for later restoration. Preserve all non-resized long-wire cells, all other non-resized standard cells, macros, die, and BPin geometry. Do not globally unlock the five buffers.

2. A nonempty static receipt is not a plan admission check. The new frozen launcher should validate the selected receipt's exact `plan.tsv` hash, source/model hashes, completed status, and every old/new instance pair; compare all combinational changes against real Liberty truth and the shared fixture catalog. Reject FF, clock-tree, hard-macro and protected output-driver edits, duplicated plan rows, and prohibited masters. The current `replace_cell` loop checks old master, do-not-touch and OAI221_X4, but alone does not establish those remaining properties. The final actual LEC remains mandatory.

3. The launcher records input hashes but does not recheck them after prepare/route. Add a frozen dependency manifest and before/after hash verification, including `geometry.tcl`, output-freeze TCL, optional extra-rip hooks, the final route TCL, fresh-STA TCL and GDS configuration. Freeze the exact completed v3 plan; do not point a running job at a live diagnostics directory. The original v1 inputs and evidence must remain unchanged.

Mechanisms that are sound, and their limits
-----------------------------------------

- The saved net signature includes actual endpoint instance, master, location, orientation and pin. Changing a master or legalizing its position therefore rips every connected non-PG wire. This correctly covers input and output pin-shape changes; it is stronger than ripping only the output. S74 and the two previously established late-access recovery nets are separately ripped. There is no demonstrated need to rip all macro nets again.
- The placement loop freezes non-resized standard cells and checks that any moved original instance is in the plan. `geometry_snapshot` compares die, every BPin, hard-macro identity/transform and M10 macro-pin geometry after edit, placement and route. These are fail-closed checks. Explicitly keeping macros fixed before placement is useful, but the existing postcondition already rejects macro motion.
- `check_placement`, `global_connect` and pre-route VDD/VSS checks are present. Connectivity alone does not prove PG material/endpoint provenance or final DEF-to-GDS/RCX correspondence; retain the independent final PG/material checks. This review does not authorize the known historical PG changes.
- Routing keeps the original signal metal2–metal10 and clock metal4–metal10 policy and the same actual DRC rules. A heuristic capacity adjustment is not a physical rule relaxation. Retained unchanged wires can still be edited by the detailed router; compare actual final material rather than assuming only explicitly ripped nets changed.
- The route wrapper intentionally emits diagnostics after a nonzero route/fresh-STA exit. Its `accepted=false_pending_all_final_gates` is appropriate. Existence of `6_final.def`, a candidate manifest, or `native_report_bytes` must never be promoted to acceptance. Final acceptance still requires actual native/full DRC, antenna, PG, material-consistent RCX, fresh all setup/hold/electrical checks, X8/interface geometry and exact functional proof binding.
- The static sizing receipt is based on the M9 clock-grafted actual RC model. Replaying those cell changes on the raw C40 source is an implementation experiment, not evidence that the raw clock geometry has the same slack. Re-extract and verify the final clock geometry used for delivery, without altering clock constraints or borrowing the old static hold result.

Useful one-node 6×8 experiment design
-----------------------------------

Do not spend six routes varying only `or_seed` after C40/C41 demonstrated identical actual ODB/DEF/V/SDC. Use six independent, bounded preparations of the same exact admitted plan: three maximum displacement bounds for resized standard cells (for example 4, 12 and 50 in the tool's existing displacement units) crossed with two conservative global-routing capacity settings (existing 0.0 and a modest 0.1 adjustment). Keep actual layer widths, spacing rules, macros, pins, die, SDC, clocks and all non-resized placements fixed. The existing 50/0.0 point is the control.

Before launching costly DRT, hash a canonical tuple of actual standard-cell master/location/orientation and canonical guide contents. Collapse identical results; a changed filename, seed or ODB metadata alone does not establish distinct physical candidates. Route only distinct candidates, each in one exclusive 8-CPU step within a single 48-CPU allocation. A failed bounded legalization remains a failed experiment; do not silently unlock more cells. Allocate unused slots to final extraction, geometry/proof checks, or a specifically diagnosed next variant rather than duplicating identical routes.

Reviewed source SHA256
---------------------

| File under `cu/` | SHA256 |
| --- | --- |
| run-c-seven-prepare-v1.sh | 848209b5eeff05e2f858119430bddc86da97123150ed0f5d8d337946d1f9e093 |
| run-c-seven-route-v1.sh | 1c3aca7f9c70e1bb91866d6d782a536bdfb043e8c083fdc70c5adb8281cdee69 |
| c-seven-route-v1.sbatch | ef14c881ff2889a39aa8494a309b00633f1d77813921bb0898759dad33615ad5 |
| c-final-sizes-edit-v1.tcl | ac68008417e8470da4af809ae2e72e68058b30605916f31bcf47450298b68496 |
| c-final-sizes-prepare-v1.tcl | 23acb458309fade2598972bb4c3b52534a04c24aa65b8470cfb98096d655cd34 |
| c-final-route-k1-v1.tcl | 0adbcd975b84f16e1786515bf4f764d684c761449ad2c2b2b4a32830fb01b504 |
| geometry.tcl | 9de1deaef117bfbe084364133afcc81c54e32c99f87d4244a8442cae1a65623f |
