# U X8 block qualification

Accepted candidate: `audit/U-antenna/candidate-U-v19-preserved`.
Authoritative receipt: `audit/release-candidate-U-v19-preserved/accepted-parent.json`.
Receipt SHA256: `cb34cbc8badd0d2d9e8d0d259ce22f512bc9aea15ed4aae365f1e1c322703771`.

- TT 250 MHz, period4 ns, clock uncertainty0.1 ns. The documented engineering IO contract sets selected153 outputs to50 fF, other outputs2 fF, IO delays0.2–0.8 ns and BUF_X2/50 ps input drive.
- Selected153 output drivers are exactly BUF_X8.
- Setup +0.078050904 ns; hold +0.003471112 ns. Setup/hold/capacitance/slew/fanout violation counts all0; recovery/removal report clear.
- Complete unchanged original FreePDK45 FEOL/BEOL/grid/antenna deck:0 items (job119772). Report SHA256 `8d85a9a432ce81fed2c7794d7399bda588094e6b9bc31a1bca0440ac528ab2b8`.
- Both PG rails connected. Original signal pins, die and macro geometry exact. Declared PG boundary change:172 rectangles removed,105 added; internal redundant PG stack removal remains recorded in the implementation provenance.
- Independent data/macro-boundary formal and separate12080-state control proof pass, with zero unmatched boundaries. Exact netlist and actual library models are bound in the receipt.
- Exported Liberty and raw zero-bloat LEF independently reload with4463 signal pin names/directions exact and1 ns/1 fF/1 V units.
- Use `parent-abstract/u_n32_controlled_dma_64.lef` for parent routing. It preserves all raw pins and M7–M10 obstruction geometry, conservatively covers M1–M6, and covers actual hierarchical GDS upper cuts: via6=43610,via7=24463,via8=10084,via9=7997. Raw nominal LEF is separately retained; its exporter omits cut obstructions.

## Extraction and delivery identity

Delivery preserves the original saved ODB, DEF, netlist, GDS and SDC. Its qualified SPEF comes from job119842 using a physically equivalent extraction copy: same-width NDR instructions normalized and a collinear short segment on net38 merged to preserve its endpoint extension. Exact input GDS material equality and all117231 signal-net layer/via unions before/after extraction were proved. Both PG rails pass in the extraction process without a precheck cache. The final timing/model proofs were rerun on this qualified SPEF.

Raw reordered DEF streamout introduced artificial corner/extension geometry; that GDS is rejected. It is not used for delivery. Preserve the frozen extraction source and transformation receipts when reproducing this flow instead of rerunning the known problematic single-process NDR extraction path unmodified.

`manifest.json` binds authoritative physical artifacts, nominal models, parent routing LEF and acceptance evidence. Earlier `PENDING.txt` files are retained as historical staging evidence; the authoritative acceptance receipt supersedes them.

This is macro/block qualification under the stated standalone IO contract. It does not certify actual A/B interconnect RC or PVT robustness; hold margin is only3.47 ps at this corner.
