# C-v27 extraction normalization verification

Job120076 completed successfully. The raw v27 extraction had changed two M10 regions: R cmd_data232 by0.216um2 and S pending_data69 by0.16um2. This version uses two strictly material-preserving encoding operations: coalesce two collinear rectangular paths where their exact union is unchanged, and remove an endpoint-zero only when full-net per-layer material stays unchanged.

The source-to-normalized text proof preserves all other net bodies and all non-NETS sections. A namespace-isolated OpenDB WireEncoder rebuilds only the selected wires. The exported instruction check resolves only absolute versus wildcard coordinate spelling; actual operation order, layers, via names and explicit extensions must match. The full source-to-import and before/after RCX per-net polygon-union comparisons then both pass.

275054 NETS declarations were checked, including VDD and VSS. Actual signal/clock count is275052. The legacy `signal_nets` receipt field counts declarations; see the bound count-scope clarification instead of reproducing that label. Uncached post-extraction VDD/VSS both pass, all macro pins/obstructions and boundary geometry are preserved.

Remote authoritative receipt: `audit/C-v27-rcx-normalization-v2/reextract-encoder/receipt.json`, SHA256 `1a407947671780b8877f561246bf227da257e750b8b68caa483c10db5a79a91e`.

This proves extraction consistency for frozen v27 only. It is not C timing/DRC acceptance. Future candidates must derive their own exact changed nets and rerun all import/material/PG checks, then use their resulting SPEF for timing and model generation. Do not copy this candidate's two net names or SPEF into a newer physical version.
