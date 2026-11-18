# Exact-material RCX endpoint normalization

This diagnostic workflow succeeded on actual C-v20-native-clock4. It is a reusable method, not permission to apply the same two net edits to a later candidate.

1. Run source-bound extraction and compare every signal-net layer union using actual DB tech widths/vias, explicit DEF extensions and strict route-token parsing.
2. Select only nets with observed before/after material differences. For each explicit endpoint zero, attempt removal; keep an edit only if the entire original per-layer metal/via union remains exactly unchanged. Other net bodies and all non-NETS text stay byte-identical.
3. Rebuild only those target wires using OpenDB dbWireEncoder, preserving every other original route instruction. Do not use read_def -incremental for this: a full DEF duplicates BPin objects, while a mini DEF does not import existing-net routing even after target wires are removed. Failed trials120015/120017/120018 were retained;120017 was stopped after actual readback proved it had not applied the intended change.
4. Validate the actual exported target route instruction tokens, exported Verilog, all original interface geometry, and complete source-to-import per-net material before extraction. The hook is namespace-isolated to avoid caller scratch-variable collisions.
5. Extract afresh, then run uncached VDD/VSS checks and complete before/after material comparison. Preserve macro pins and obstructions. A later final candidate must rerun all its timing, model and release source bindings with this extraction.

Successful job120020: 272347 nets, zero source-to-import differences and zero extraction-before/after differences; macro pins/OBS unchanged; VDD/VSS both connected. Source edit removed two union-redundant explicit zeros at engine1.b15 and store.pending_data73 bends. Each original raw extraction had removed0.16um2 due to joining endpoint styles. No real metal change is used as a workaround.

Remote successful output: `audit/C-rcx-zero-normalization-v1/reextract-encoder/`. Receipt SHA256 `ae32a4cb1a4c57fdd8cc4c10cad0edd1df6843ba9a5be003130dd78091c27932`. This is extraction consistency only; C is still not accepted, and this old diagnostic SPEF must not be substituted into a later routed candidate.
