# Issue 289 independent endpoint audit

The A original route contains 306 non-P branches. B contains the same 306 C/U branches plus 34 G/S branches. Union: 340 drivers, with 153 C0 outputs, 153 U0 outputs, 33 C0.G outputs, and one F0.S output. Input ports are sinks; changing their input cells to X8 is not an electrical output-drive upgrade.

`endpoints.json` records exact direction and scheme membership. `directions-check.json` checks all 612 selected C/U endpoints against the actual CTS export BTerm directions: zero mismatches. The two CTS files are explicitly not detailed-route accepted, as recorded in `stopped-current-checkpoints.json`; completion must start from those exact checkpoints and retain their interface contract.

## Physical binding

- C/U branch geometry: `/public/home/yuzelu/project-circuit/yzl-cu-overlay-physical-20261116/{C,U}/flow/results/nangate45/{c,u}-overlay-current/base/4_cts.odb`. Hashes are in the stopped-checkpoint receipt. The archive source export is `/public/home/yuzelu/PingyangHuang/hpy-pr276-stress976.nTAy3LMX/export-{C,U}`.
- B C0.G pin inventory instead uses `/public/home/yuzelu/project-circuit/yzl-c-segment-250mhz-20261116/flow/results/nangate45/c-native-frame/base/6_final.odb`. Thus B mixes a C/U overlay contract and separate segment-C macro pin inventory; these must not silently be represented as one already accepted parent C implementation.
- B F0.S uses `/public/home/yuzelu/project-circuit/main-blockv2-f300-side-01/flow/results/nangate45/f-native-frame/base/6_final.odb`; hierarchy `local_group.services.store.leaf`.
- G leaf: `/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-201-compact-ge/2ba89c0bd/release/g/6_final.gds`; C and F configs explicitly bind this source.
- S leaf: `/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-200-compact-local-s/run08-base0/results/0/flow/results/nangate45/local_s_base/base/6_final.gds`; characterization `/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-200-compact-local-s/audit08/base0/local_s_base.lib`.

## Geometry and functional scope

C/U selected pins are BTerms. Original CTS has perimeter BPin shapes. Archive top endpoints include added `lift-nine-C0`, `lift-nine-U0` lower escape geometry and landing closure overlays. Original PRE_GLOBAL_ROUTE `access-pins.tcl` relocates BTerms to an internal M10 array; running it would invalidate the original endpoint geometry. Keep CTS BPin geometry and recheck new block routing against the preserved lower escape overlay.

B `prepare.py` describes synthetic macro-pin pressure connectivity and replacement of existing local input drivers in the test netlist only. F S req_valid has original parent driver hold15100/Z. Preserve parent connectivity for block acceptance. The synthetic G-to-S connection is not proof of the parent product's functional compatibility or permission to retain two drivers on a net.

## Independent acceptance gates

1. Immutable provenance: source ODB, RTL, SDC, Liberty, LEF/GDS hashes; separate exact CTS C/U parents from B macro-placement source. Baseline and upgraded candidates must share the same logical contract.
2. Coverage: every listed output appears exactly once with an actual driven net; no missing ports, ties, accidental multiple drivers, or changed polarity/function. Trace actual terminal instance/master before and after; a final BUF_X8 or verified equivalent X8 gate must truly drive that output. Do not infer drive from filename.
3. Geometry: unchanged BTerm shapes, block dimensions and macro transforms, or an explicit new placement/route binding. Recheck lower escapes against new routed block geometry, not only the top 536/536 connectivity report.
4. Functional equivalence/regression: original contract and cycle latency preserved, same inputs/outputs; no removals of real parent drivers merely to emulate synthetic macro wiring.
5. Backend completeness: final routed ODB/DEF/netlist/GDS plus extracted SPEF and updated LEF/Liberty for changed hard macros. No CTS checkpoint or log completion alone counts as acceptance.
6. Timing/electrical: original clock/IO constraints, actual extracted parasitics, setup/hold nonnegative, electrical max-cap/max-slew/fanout acceptable; report unconstrained endpoints and unresolved paths. X8 receive input-cap changes must propagate to parent timing. Keep baseline and candidate values together.
7. Physical signoff: detailed route connectivity, DRC and antenna checks, macro-interface consistency, tool status and remaining violations explicitly recorded. Leaf pass does not automatically establish parent pass.
8. Top RC assessment is a separate next acceptance level: updated driver Liberty plus new leaf/block parasitics and exact A/B top route RC. Current requested macro/block backend success alone must not be labeled A/B top 200/300 MHz timing closure.

## Follow-up baseline acceptance audit

Segment-C's actual `c-final-signoff/c250-signoff.json` reports setup +0.438744 ns, hold +0.020786 ns, five violation categories zero, but **full_drc_items=106 and passed=false**. Its earlier C-SEGMENT-250MHZ-RECEIPT reports full DRC pending. This must not be described as complete backend acceptance. Its exact audit launcher is `qualify.sh`: run `audit-pads.tcl`, `control-sta.tcl`, then KLayout `/OpenROAD-flow-scripts/flow/platforms/nangate45/drc/FreePDK45.lydrc` against final GDS, and parse `c250-full.lyrdb`.

F300 `verify-300.sh` runs two independent STA/electrical scripts. `check-300.py` verifies exact equality to F250 ECO ODB/DEF/GDS/V/SPEF hashes and its 129-rule full deck DRC (zero items); only clock SDC changes. F250 source is `/public/home/yuzelu/project-circuit/main-blockv2-f250-side-eco01`. It contains `audit.sh`, `check-signoff.py`, `native-full.lyrdb`, `final-signoff.json` and `formal-retry.sh`. The latter uses tie-normalize.py and Kepler `normalized-lec.yml`, verifies zero unmatched inputs/outputs and explicit UNSAT/IDENTICAL. Upgraded artifacts cannot reuse this old hash-equivalence shortcut.

G's final LEC receipt is `issue-201-compact-ge/2ba89c0bd/final/g/formal/receipt.json`, passed=true. Its parse/emit scripts and Kepler config are in the same directory. Release G `delivery.json` reports leaf_accepted=true. `release/g/klayout-results.json` covers only all-port fixture rectangles and upper-layer checks; full native DRC is separately `release/g/full-deck.lyrdb`. Exact release checker `.../2ba89c0bd/source/project/experiments/block_v2/compact_release.py` verifies strict_native_lec, empty native-whole-drc.rpt and source DRC hashes before packaging.

S's exact native routed audit is `issue-200-compact-local-s/audit08/base0/audit.json`: passed=true, setup +0.158919111 ns, hold +0.033924419 ns, all listed timing/physical checks true. Audit Tcl scripts are in the same folder. Formal proof is separately `final-gates/formal-base/formal.json` (passed=true), with `gate.yml` and negative controls. It cuts at four SRAM banks and checks 1185 common inputs, 1216 common outputs, zero unmatched boundaries.

Overlay-C and segment-C placement scripts both place G at (3088000,1336000) DBU, i.e. (1544,668) um; overlay explicitly sets R0. This is script-level evidence of matching placement, not yet an ODB-shape comparison. Requested existing C probe to emit actual G origin/orientation and all 34 selected ITerm boxes, then compare to B `C-pins.tsv`. Whether one upgraded overlay-C can cover B G geometry requires that direct comparison plus leaf identity and full parent acceptance.

## Pilot independent readback

C-seed0 actual ODB geometry comparison is complete. All 34 B G endpoint rectangles and directions match overlay C exactly. Hierarchy differs: B inventory `local_group.services.engine\[1\].genblk1.activate.leaf`; overlay `services.engine\[1\].genblk1.activate.leaf`. `G-geometry-comparison.json` preserves both identities and all differences, with `physical_geometry_equal=true`. Explicit rebinding is required.

C pilot ECO receipt independently checked: 153/153 exact selected outputs, 153 unique driver instances, every swap BUF_X1 to BUF_X8. Entire geometry-before and geometry-after-eco snapshots are byte-identical (BPin geometry, die, macro origins/orientations, M10 macro ITerms). See `C-pilot-audit.json`. This verifies ECO coverage and geometry preservation only; final routed driver readback and extracted electrical acceptance remain pending.
