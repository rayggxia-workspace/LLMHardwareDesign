# C-v20 single-net M10 notch patch

Remote evidence: `/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-m10-notch-v1`.

The source C-v20 native final route has a same-net M10 notch at `dma_s_rsp_data[52]`. The S macro pin ends at x1393.095um and the vertical route starts at x1393.295um. The horizontal connection covers the lower portion, leaving a0.2um by0.6um notch between y580.470 and581.070um.

The candidate adds one M10 segment, center x1393.095um, y580.070→580.670um, standard0.8um width. Its geometric union fills only the0.12um² notch. Job119983 reconstructed only this net using the supported OpenDB dbWireEncoder API. All original target route segments and vias remain; all other nets and all non-NETS DEF sections are byte-identical after normalized OpenDB export. Exported Verilog before/after is byte-identical. Details and hashes are in `C-m10-notch-structural-receipt.json`.

Use frozen `patched.odb` SHA256 `e0d64d00f28f2b3349001ab9e2acb5feaa741cc0bb7aee7a61c166c244a0b91f` as the source for a subsequent ECO. The frozen hook reconstructs the original C-v20 target wire and must not be blindly applied after that net has been rerouted. Source files were not overwritten.

Incremental DEF attempts119979/119980 were unsuccessful: existing net wiring was ignored, even after the old wire was removed. These were probes, not passing candidates. The final encoder run119983 replaced those temporary diagnostic outputs. Streamout119984 initially failed because KLAYOUT_CMD was undefined;119986 used the same actual def2stream command with direct klayout executable and succeeded.

Actual regenerated GDS local geometry/rule and fresh PG results are tracked separately. This patch does not address the remaining upper-layer/antenna/electrical violations or establish full block signoff. Final merged ECO requires fresh routing checks, GDS rules, parasitic extraction and timing, and functional validation.

## Completed independent checks

- Actual regenerated GDS119986/119987: exactly0.12um² M10 added, zero removed; every other layer in the local ROI unchanged. Original800nm space and notch checks report one target marker before and zero after. `C-m10-notch-gds-receipt.json`.
- Fresh patched-ODB PG119991: all VDD and VSS shapes connected. `C-m10-notch-pg-receipt.json`.
- Identical standalone `drt::check_drc` full-design invocation119996(original)/119993(patched):235→234 markers. Only the specified dma_s_rsp_data52 M10 marker disappears; no new markers, all other markers unchanged. `C-m10-notch-native-difference-receipt.json`. This standalone checker reports more pre-existing markers than the detailed-router iteration report;234 remain, so full native clearance is explicitly false.

All frozen patch artifacts remain under the evidence directory above. Source ODB SHA25654f4e52432b1313b48ab9270de558039699e3e3852c6794dffcedf6d7f9b8d8d is unchanged. Final full GDS/backend acceptance belongs to the subsequent integrated candidate.
