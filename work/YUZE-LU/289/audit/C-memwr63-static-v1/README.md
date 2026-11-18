# C mem_wr_address[63] bounded static sizing

Job 120207 completed. This is a fixed-wire-RC planning result, not a legalized or extracted backend candidate.

Source is qualified normalized-nine-net ODB SHA 666d30659827b7764eb3e89e8f0e4846e366142b9f3ca0bfffae34f32a4ac371 and SPEF SHA 303a113045f40318159e235f7566cb7c31e76837f1dab465a8dd01aa9e2524ab. The existing 59-cell plan is applied first, then 37 additional same-family stateless cell changes are selected under global non-regression checks. Exact changes and metrics are in plan.tsv and planning-receipt.json.

Target setup slack improves from -95.547 ps to +142.720 ps. Relative to the explicit after-59 baseline, global setup WNS stays -103.446141 ps, hold WHS stays -72.067246 ps, setup count decreases 97 to 90, hold count remains 141, capacitance count remains 2, slew/fanout remain zero. TNS improves from -4.131950855 ns to -3.760901451 ns.

The 59-cell baseline itself worsens hold relative to its source: 117 violations / -48.911043 ps becomes 141 / -72.067246 ps. That prior change is disclosed separately and is not hidden by the additional-plan non-regression condition.

All instance coordinates, orientations, pin/net connectivity, protected flip-flops, clock cones, macros and selected 153 output drivers are unchanged. Same-family function/direction/three-state equality applies to the additional 37 changes; the existing 59 changes have a separate pin-function proof and include BUF/CLKBUF family substitutions.

Five masters beyond the previously qualified 34-master fixture (AND3_X4, BUF_X1, INV_X4, NAND3_X4, NOR3_X2) pass the complete unchanged original deck on a translated isolated original-library fixture. This proves that fixture only, not C parent geometry.

The independently-recomputed-inputs-after.sha256 file reopens and hashes every input after completion. The legacy inputs-after.sha256 was copied after successful sha256sum -c; provenance-supplement.json explicitly distinguishes the new independent enumeration.

Next use requires an independently named physical ECO candidate, actual legalization/routing, fresh extracted timing, exact geometry and source checks, functional proof, and the complete original physical rule deck. Do not reuse fixed-wire positive slack as final timing evidence.
