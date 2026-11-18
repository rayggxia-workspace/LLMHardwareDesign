# Candidate-bound C native marker classification

Prepared only; no candidate is accepted by this package. Derived from root's `c-v27-native-material.py` and `c-v27-native-own-net.py`; those scripts and their receipts remain unchanged.

Run on a frozen actual candidate, after an independently generated fresh native report exists:

`sbatch audit/C-final-native-v1/run.sbatch /absolute/candidate-native-spec.json`

The JSON specification has `candidate_id`, a new absolute `output` directory, `inputs`, and `evidence`. Each input/evidence entry is `{ "path": "/absolute/path", "sha256": "actual-file-sha256" }`.

Required input keys: `gds`, `def`, `native`, `layers`, `vias`, `parser`. Use the actual final candidate's GDS and explicit routed DEF; layers/vias must be exported from that candidate's database/technology. `parser` is the frozen `C-v27-rcx-normalization-v2/parser-source.py` (only its strict `parse` function is compiled). Unknown route encodings remain unresolved rather than being approximated.

Required evidence keys: `native_origin`, `metadata_origin`. These receipts must establish that the fresh native report and metadata exports came from the same exact candidate ODB/DEF used by the final independent gates. This checker hashes these receipts; final aggregation must verify their contents, not merely their existence.

Every parsed native marker is retained, with no expected count or baseline-count ceiling. For each reviewed layer the checker measures actual hierarchical GDS material and local spacing/notch edge pairs, then independently decodes the named source net's explicit DEF geometry. Only `Metal Spacing` on metal2/metal3 can receive the existing reviewed classification, and only when both actual GDS and that single source net completely cover the marker and both local checks are empty. All other markers require explicit resolution; unknown layers remain unresolved. No material from another net can satisfy the source-net condition.

The local rule table is the unchanged reviewed native diagnostic table (M2/M3 70 nm, M9/M10 800 nm, VIA9 880 nm). It is not a replacement for the full original deck. The checker does not resolve short circuits, connectivity, antenna, arbitrary cut rules, or upper-metal exceptions.

## Final aggregation contract

Alongside `C-final-v1` independent timing/electrical/async, 153 X8, geometry, PG and model import gates:

1. Require this receipt's candidate ID and exact GDS/DEF hashes to match the authoritative final candidate. Verify all before/after hashes, checker/parser hashes, and origin receipt contents against exact candidate ODB and report/export hashes.
2. Require no unresolved native indices, or an independently reviewed, marker-specific actual-material disposition bound to the same exact source. Never reuse the v27 221-marker count or accept a lower total count.
3. Independently require the complete original unchanged foundry deck to report zero on the same authoritative GDS. This package always emits `accepted: false`; `native_markers_resolved` concerns only this diagnostic gate.
4. Keep function/control proofs bound to the final ODB-exported netlist and qualified extraction/model proofs bound to the final physical candidate. This local classification changes none of those requirements.

Validation at preparation: Python syntax compilation only. No new EDA was submitted against a failed candidate. First actual final-candidate invocation remains required.
