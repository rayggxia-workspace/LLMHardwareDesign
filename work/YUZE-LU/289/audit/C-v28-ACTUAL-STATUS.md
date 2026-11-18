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

## Subsequent actual results and unified run

The nine-net physical combination120158 passes the original upper checks24→0, fresh native236→227 with exactly9 targeted removals and no additions, PG and unrelated geometry/connectivity preservation. Independent normalization/reextraction120170 preserves all277589 net declarations, macro pins/OBS and uncached PG; actual complete GDS cell/layer material and child-reference identity120182 also passes. The qualified next seed is `C-v28-nine-net-normalization-v1/reextract-encoder/before.odb` SHA666d30659827b7764eb3e89e8f0e4846e366142b9f3ca0bfffae34f32a4ac371. Its qualified-binding explicitly leaves backend acceptance false.

Dynamic native classification finds222 M2/M3 same-net material artifacts and5 M9 virtual-guard interactions. The separate five-marker physical/OBS proof is conditional on a future full-deck zero result on the same final candidate. The marker counts are specific to this source. One actual antenna violation remains on mem_rd_rsp_data[182].

Targeted S74 access recovery120173 enables real local routing. Dual BUF8 middle repeaters improve indexed read_address63 from−116.965555 to−3.067768ps and61 from−115.405463 to−1.508571ps; global WNS becomes−114.741109ps on a different loader path. BUF16 gives no further endpoint improvement, so BUF8 is retained. Moving the net118426 buffer below R clears three original negative loader endpoints and introduces four small hold violations; moving the net118424 source buffer to the right corner worsens timing and is rejected. Actual material differences are measured across every net, including changes made by DRT outside the initially ripped list.

Unified actual batch120194 runs six independent8-CPU tasks on one node: R isolation BUF8/16 × net118424 control/middle repeater y200/y350µm. Common source is the qualified normalized-nine seed,59 equivalent sizes, exact locked dual-BUF8 and lower-R buffer coordinates,141 hold branches targeting100ps (1028 new delay/strong-buffer cells), two R isolations and one antenna diode. All six pass topology, legalization, fixed geometry/coordinate and PG prechecks and are routing. The four newly exposed hold endpoints have a frozen backup plan with1.57–2.19ns setup budgets, pending actual unified timing. Early strict legalized LEC120196 runs in parallel; final routed netlist binding remains mandatory. Each result stays bound to its own candidate, and the unified implementation needs fresh physical, RC, timing and functional verification.
