# U physical closure — still in progress

## Latest combined repair

**119747 / U-v14 is rejected.** The first NDR hook specified spacing only on M9/M10. Actual database readback shows native widths but zero spacing on unspecified routing layers; the router did not inherit default spacing. PG checking caught VDD-to-legacy_rsp_data90 shorts despite native DRT0; two1.0um cases also failed RCX with a segmentation fault. No v14 candidate is accepted and no failed PG check is waived. Root's `u-upper-ndr-hook-v2.tcl` explicitly lists native width and spacing on every routing layer, increases only the selected upper spacing, and asserts exact database readback for every layer. Restart from the previous PG-checked guard-ant-v1 database, retaining diode/timing corrections; do not reuse v14 routing.

Job119747 runs six independent candidates on one node (six exclusive eight-CPU steps), combining upper-layer spacing margins1.0/1.2/1.4um with two targeted electrical/hold repairs. All start from the same `candidate-guard-ant-v1` geometry. Their database edits have completed:15 residual input-net antenna diodes,8 precisely diagnosed nets assigned stricter hard-spacing routing rules and explicitly ripped,7 macro-branch buffers, two driver upsizes and the task_packet89 receiving-register hold branch. Final routing and verification remain pending. The routing margins are implementation constraints; acceptance uses the unchanged original deck and IO contract.

The predecessor's original-definition antenna diagnostic fell from1293 to15 report items. Its upper-layer diagnostic has five unique physical locations (nine hierarchical report items). Neither result is an acceptance. The new candidate retains the1897 actual macro cut obstructions and the previously checked PG stack corrections; no leaf GDS or fixed signal port is changed.

The electrically closed seed is `cu/runs/U-v13-electrical-f50-x4` under the task's remote root. Fresh independent ODB/SDC/SPEF loading gives setup +0.044321 ns and hold +0.001723 ns (rounded), with all five timing/electrical violation counts zero. Independent original-CTS-to-seed data/macro/state and clock/reset proofs pass; 153 actual X8 outputs, original signal BPin/die/macro geometry and both PG rails pass. Evidence: `audit/evidence/U-f50x4`. This is **not yet full backend acceptance**.

## Why native DRC/ANT zero was insufficient

The old v7 complete, unmodified foundry deck reported 1459 items: 1312 antenna and 147 spacing reports. Hierarchical reports duplicate some leaf-local and parent coordinates. They must not be described as 1459 independent physical defects.

Independent GDS comparisons show the embedded S/E are geometrically identical to their original GDS, and source-alone spacing checks are zero. Reported macro-local markers arise from neighboring **parent** signal vias or PG material. Thus the leaf GDS is retained, not declared defective or replaced merely because its name appears in a hierarchical report.

The original deck incorrectly labels the via7 spacing check `VIA6.2`; its actual layer is GDS24, threshold440nm. Via9 is GDS28, threshold880nm. The original full deck remains unchanged.

`u-map-markers-v2.py` mapped all84 parent-coordinate non-antenna markers to actual DEF wires/vias/BPins and PG special-wire rectangles. Ten S M9 contexts identify ten redundant parent PG via stacks. This is exact shape overlap ownership evidence, not a waiver. The latest f50 geometry already fixes most old boundary defects: the diagnostic reports parent M9×10, via7×2, via9×53, with no M10 spacing items. One via9 pair remains outside macro footprints; the other reports involve macro context. Diagnostic subsets do not replace the full deck.

## Parent cut and PG correction

Root job119729 writes `u-physical/candidate-guard-v1`, starting from f50/x4:

- Real S/E GDS via7/8/9 material is extracted into1897 cut rectangles. The exact material becomes additional master OBS; no leaf metal, pins, Liberty or GDS is edited.
- Ten precisely identified complete M7–M10 PG stacks (30 parent via objects) are removed. VDD and VSS connectivity pass immediately afterward; final connectivity must also pass.
- All546 parent nets attached to S/E are ripped and rerouted. Signal and power BPin geometry, die and macro transforms must remain exactly equal. Parasitics and all five timing/electrical checks are rerun in a fresh process.
- Upper spacing uses `upper-spacing-diagnostic-v2.lydrc` only for fast diagnosis. It contains four original spacing checks and cannot serve as full acceptance.

The first diagnostic wrapper failed before checking because it called `report` before `source`; v2 corrects this. The first wire-iterator probe found that this OpenROAD Tcl build does not expose `dbWireShapeItr`; the actual mapping instead parses exported DEF and dumps exact technology-via/PG geometry. All failed attempts remain separate.

## Antenna correction in parallel

Independent current-f50 antenna-only diagnosis uses the original actual gate/diode geometry and300:1 rule. Its1293 polygons map unambiguously to1149 actual signal nets. Library ANTENNA_X1 has a physically verified A contact to the diode geometry; its LEF `ANTENNADIFFAREA=0` explains why OpenROAD ANT0 alone is inadequate evidence of foundry-rule protection.

Endpoint-audit job119734 writes `audit/U-antenna/candidate-guard-ant-v1`. It starts from root's exact `guarded-before-route.odb`, already containing the cut guards and verified PG removals, adds one real ANTENNA_X1 to each mapped net at a current actual anchor, legalizes and reroutes all nets affected by movement or new connections, then performs RCX/fresh checks/GDS/antenna diagnosis. It does not overwrite the guard-only comparison.

Both candidates remain unaccepted. Required closure is full original-deck DRC zero plus fresh timing/electrical, PG/antenna, exact153-driver/geometry checks and complete functional evidence on the final candidate. Routing/diodes can alter the tight hold margin, so timing must not be inherited from f50.
