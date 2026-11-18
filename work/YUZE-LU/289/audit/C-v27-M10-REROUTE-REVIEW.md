# C-v27 M10 local reroute qualification

Qualified candidate: `/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-v27-m10/reroute-v2/patched.odb`, SHA256 `ab13f9ead58d9ee062d2a08ac883ff76b0d608d092a242a9eab7e8f60b32d519`. This is a local geometry input for integration, not an accepted final C block.

The six hierarchical M10 markers represent two unique same-net notches: S `rsp_data[71]` and R `load_data[114]`. Ownership was traced through actual parent net/pin, R0 macro position and each leaf's named-net routed DEF. The parent-only repair raises the S M10 horizontal segment from256.5um to257.3um, maintaining0.83um clearance to the actual leaf extension; the R route uses its existing x185.695um track with the pin connection at y1047.4um, giving0.8um clearance. Macro shapes, abstract pins, rules, vias, other layers and previous14/52 routes are unchanged.

The additive `patch-v1` experiment is rejected: although it joins genuinely same-net actual copper, the current abstract marks internal macro metal as OBS, and the additive version creates four new native Short markers. No waiver, changed abstract or relaxed rule was used. The qualified `reroute-v2` avoids these obstructions.

Validation:

- Structural comparison: only the declared two nets' M10 segment replacements; all other nets and non-NETS DEF sections byte-identical; exported Boolean Verilog byte-identical.
- Actual regenerated GDS: complete connected-component equality to the independently reconstructed top routes + pin + actual leaf routes; no foreign overlap;800nm foreign separation and original width/space/notch checks pass; every other layer within both ROIs identical.
- Original upper-layer diagnostic deck: all six M10 markers disappear;14 M9 and4 V9 markers remain exactly unchanged, with no new markers.
- Same standalone native checker:232→229, removing only the three S/R target spacing markers, no additions. Full native clearance remains false.
- Fresh VDD and VSS connectivity passes.

The GDS validation completed in job120064 using KLayout's documented conservative recursive bounding-box selection, expanded one database unit and followed by the exact original integer-ROI clipping. This is geometrically equivalent to the earlier global-flatten-then-clip formulation. The slow redundant120053 was stopped only after120064 passed, with its log and stop reason retained; it is not counted as a pass.

`C-v27-M10-integration-binding.json` hashes all four receipts and all their inputs. The final integrated candidate still requires fresh routing/parasitics/timing/electrical checks, the full unchanged GDS deck and final selected-netlist functional binding. Applying the frozen whole-net hook after a separate reroute requires first checking that its source wire still matches; do not overwrite a newer route blindly.
