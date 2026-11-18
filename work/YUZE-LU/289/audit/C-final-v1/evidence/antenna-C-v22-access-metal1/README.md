# C-v22 actual antenna localization

Diagnostic source: `cu/runs/C-v22-access-metal1`. GDS SHA256 `2cdeffb831ef0948ac87fc521b9322e300dcd70e10b9eb30492f89fc03168a9d`. This source has5109 native DRC markers and is **not an accepted C backend**.

Producer119956 generated the actual focused antenna report. Job119958 bound it to unchanged GDS/deck before/after manifests and the completed report SHA. Read-only mapper119959 then completed successfully with frozen inputs.

- 1118 actual parent report polygons map to547 distinct parent nets.
- Nonparent, ambiguous and unmapped counts are all0.
- All547 nets connect INPUT boundary ports, verified against actual DEF direction. None touches the153 selected output ports.
- Parent ODB endpoints show no ANTENNA_X1 on these547 nets. Macro-internal diodes are outside this parent endpoint inventory.
- 272347 nets underwent DEF↔ODB terminal-set comparison;2135815 route segments were scanned. Explicit extensions, real via metal enclosures and every via layer transition were decoded.

Reports by metal layer: M2=103,M3=440,M4=44,M5=157,M6=80,M7=26,M8=47,M9=4,M10=217.

Remote complete mapping: `audit/C-final-v1/antenna-C-v22-access-metal1-119959/antenna-net-map.json`, SHA256 `eaa15ed76ece783fece88750090c7142039305b1a96238cb3c5165a8afefeab9`. Local small evidence includes summary, detailed network inventory, names, input manifests and producer binding.

No insertion anchor was selected, no diode ECO was generated or applied, and547 is not asserted to be the required diode count. Any changed final physical candidate requires a new actual report and mapping; these diagnostics do not transfer automatically.
