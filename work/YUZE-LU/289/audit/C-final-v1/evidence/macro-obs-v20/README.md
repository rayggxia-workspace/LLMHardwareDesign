# C-v20 hardmacro VIA6–VIA9 OBS inventory

Read-only allocated jobs119912,119914,119915. Exact source is `cu/runs/C-v20-native-clock4/global-candidate.odb` (SHA256 `eb5e0e17ce50e8d68ccb5ea36d18e9f3ed9b0298e394de32d8e2c1998826b10c`). Source database/config hashes remained unchanged.

| Actual installed master | VIA6 | VIA7 | VIA8 | VIA9 |
|---|---|---|---|---|
| local_s_base | fully covered | fully covered | fully covered | fully covered |
| block_v2_e_compact | fully covered | fully covered | fully covered | fully covered |
| block_v2_g | fully covered | fully covered | fully covered | fully covered |
| r_stream_local | fully covered | fully covered | fully covered | fully covered |
| e_s32_pipeline_128 (dot) | 1098 cuts uncovered | 298 uncovered | 288 uncovered | 286 uncovered |

The bank master `s_sram_256x128_freepdk45` exists and is BLOCK, but has zero actual top-level instances. It was not accidentally filtered by master class. Recursive source material of all five instantiated macros is included in the inventory.

For dot, installed VIA6–VIA9 OBS counts are all zero. Uncovered source areas are21.5208,47.68,46.08,183.04µm². All1970 actual cut polygons are rectangles. Exported TSV columns are master/layer/xmin/ymin/xmax/ymax, in2000DBU/µm master-local coordinates, without dilation. Dot origin is(0,0), size460×400µm; current instance origin is(2000,672)µm,R0.

`dot-actual-cut-obs.tsv` SHA256 `608f06d6a8b3956d590733be0a51b935435adce160f17754647c6207ffb2e872`.
Actual dot source GDS SHA256 `fae5ae9ec8b4268d2d0996699d7c5892ed6ed21f9528168340ab939dda54992e`.

The comparison subtracts actual installed dbMaster cut OBS from actual recursive leaf GDS material, with exact zero-origin coordinate mapping and source LEF checks. These are abstract coverage omissions, **not evidence that a routed parent violates DRC**. No routing, physical edits or geometry inflation were performed. The TSV was passed to cu_upgrade for a separately versioned future guarded candidate; existing running inputs remain frozen. Root owns actual final full-deck checks.
