# Actual C-v28 closure checkpoint

This is an intermediate checkpoint, not backend acceptance. The accepted U and F releases remain frozen; G33/S1 are qualified within the F chain. C153 remains under repair at its unchanged 250 MHz contract.

## Selected actual route

`cu/runs/C-v28-actual-i8-h50` is the selected physical source. Fresh extracted timing has setup100/WNS−0.116965555ns, hold117/WHS−0.048911043ns, capacitance27, slew0 and fanout0. Its native router report has4 items; a fresh independent native check has236. The original-rule upper-metal check also finds macro-context material interactions absent from the router's report. Neither native report is a complete physical acceptance result.

The other five actual routes from120096 are retained as controls. No frequency, IO, uncertainty, false-path or multicycle relaxation is authorized or used.

## Completed evidence

- Actual i8/h50 legalized data/state/control equivalence120098 passes against the actual C-v16 synthesis, including21095 retained states and no unmatched boundaries. Actual i16/h150 proof120105 also passes; it does not qualify a different final netlist.
- The S4 same-net notch patch is qualified by actual hierarchical GDS component/material and800nm width/spacing/notch checks, unchanged unrelated geometry/logic and fresh native/PG comparison120115. It adds0.12µm² M10 material and removes only the targeted native marker. Its frozen binding is `C-v28-S4-integration-binding.json`; it has not yet been merged into a final accepted C.
- The34 changed/added standard-cell masters pass an isolated unchanged full-deck fixture120102 (`C-v28-cell-preflight/receipt.json`). This does not qualify final placed/routed C.
- The15-change static greedy study120120 is bounded and complete. It improves WNS by8.864ps using unchanged actual wire RC. Its result is planning evidence, not rerouted timing.
- The disjoint59-change sizing plan120126 is fully remeasured against actual i8/h50 RC: setup97, hold141, capacitance2, slew0. Targeted hold repair and physical routing are still required. The two residual capacitance violations belong to R macro outputs220/466.

## Active work and rejected trials

CU owns the141 hold repairs, two R-output isolations and indexed-path local buffer placement/changed-net routing. Endpoint audit owns R boundary M10 repairs, S4 composition and dynamic RCX material qualification. Loader review owns the newly localized M9/VIA9 physical interactions. Root owns the complete original full deck, evidence aggregation and delivery.

The R3 trunk-shift trial120128/120130 is rejected: shifting away from foreign copper creates a new0.105µm own-net notch. Both PG rails passing does not override that geometric failure. A new direct connection to the actual R pin is being prepared, including a fourth R interaction found only by the original-rule check.

Signal-delay study120122 is rejected for its incorrect signed-TNS comparison. Corrected120124 and the fully remeasured combined plan120126 are recorded separately. Clock-budget studies120125/120129 are read-only: external incoming hold limits on read_address63/61 are77.75/94.51ps; clocks have not been edited. Self-feedback hold alone is not used to infer a useful-skew bound.

The original unchanged full-deck baseline120063 on frozen v27 completed in2h18m39 with42 violations: all41 frozen focused markers match exactly, and the only additional marker is METAL1.5 in OAI221_X4. See `full-C-v27-joint-e20-h30/focused-comparison.json`. It is a failing diagnostic baseline; its source differs from v28 and it cannot qualify a final v28 GDS. Final acceptance requires matching frozen ODB/DEF/V/GDS/SDC/SPEF, fresh physical/electrical/timing/PG gates, complete original deck and actual-final functional/model checks.
