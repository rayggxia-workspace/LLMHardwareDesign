# C antenna localization: read-only preparation

No C antenna localization or diode modification has been run by this preparation package. Do not estimate counts from U or native OpenROAD ANT reports.

Once root's diagnostic job has completed against the actual C GDS, invoke:

`sbatch audit/C-final-v1/antenna-map.sbatch <exact-C-run> <actual-antenna.lyrdb> <report-binding.json>`

Required binding JSON fields (created by the completed diagnostic producer, not fabricated by the mapper):

```json
{
  "completed": true,
  "gds_path": "/absolute/exact-C-run/flow/results/nangate45/c-overlay-current/base/6_final.gds",
  "gds_sha256": "ACTUAL_SHA256",
  "report_path": "/absolute/actual-antenna.lyrdb",
  "report_sha256": "ACTUAL_SHA256",
  "deck_path": "/absolute/actual-diagnostic-rule-deck.lydrc",
  "deck_sha256": "ACTUAL_SHA256"
}
```

The allocated8-CPU job freezes the physical input/report/script hashes, reads actual ODB layer/via/BPin/cell endpoint data, and validates DEF-to-ODB terminal connectivity. It maps actual antenna polygons through exact intersections with DEF wire rectangles and real via metal enclosures. The decoder tracks each layer transition at every via, explicit point extensions, consecutive vias and default native widths. Unknown NDR or route syntax is rejected for inspection; it is not silently decoded as an ordinary-width route.

Output `antenna-net-map.json` distinguishes unique parent-net hits, ambiguous hits, unmapped markers and nonparent hierarchical markers. Nonparent reports remain unresolved until their actual hierarchy is inspected. It lists actual existing diode cells and standard endpoint candidates only as factual metadata, selects no insertion anchor and emits no ECO script. Mapping completeness is separate from physical/timing acceptance.

If the report is empty, the mapper does not invent work. If source/report files change during the run, the hash gate fails. Root continues to own full unchanged foundry deck qualification; C final provenance/model gates remain in this directory's main README.
