# U GDS diagnostic corrections

The accepted diagnostic is `U-v7-leaf-context-v2.json`, using the actual original rule thresholds and layers. `U-v7-context-parent-markers.tsv` contains the 63 distinct macro-context parent marker locations. The original 1,459 report entries include hierarchy duplication and are not 1,459 independent errors.

The first diagnostic script `u-leaf-context.py` used the ambiguous VIA6.2 category as via6 at 440 nm. This was incorrect: the original deck labels both via6 (layer22,160nm) and via7 (layer24,440nm) as VIA6.2. Its large erroneous diagnostic remains remote at `audit/U-v7-leaf-context.json` as failure evidence and must not be used as a count or acceptance result.

The corrected diagnostic checks source-alone spacing on both actual layers; all E/S source-alone checks are zero. Every one of the 63 distinct context markers intersects actual parent-only geometry after subtracting the macro geometry. Thus these are parent-context spacing problems, not malformed source macros. Full source-to-embedded macro polygon comparison across every GDS layer is exact (empty symmetric difference), proving there was no streamout shape mutation.

These focused diagnostics do not replace the final unchanged full rule deck. The v7 report guides localization only; any later routed candidate must be checked using its own final GDS.
