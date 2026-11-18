# C input antenna trial (547 nets)

Frozen remote package: `/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-antenna-eco-v1`.

The plan binds 547 uniquely mapped INPUT nets from the completed C-v22-access-metal1 actual GDS antenna report. This source remains a diagnostic candidate, not an accepted C release. The hook validates each expected INPUT port-to-net connection and all 153 BUF_X8 output drivers before adding one qualified ANTENNA_X1 per target net. Receiving-pin anchors are chosen from the candidate loaded at execution, never from diagnostic coordinates.

Allocated dry edit 119966 completed successfully on an independent copy. Fresh OpenDB readback checked 547 diode A/PG bindings, unchanged original instances/master/placement/terminal connections, and exact interface/die/macro geometry. All anchors used actual input-pin geometry, with zero fallback. This does not qualify legalization, routed antenna, electrical performance, power connectivity geometry, or full DRC.

To integrate, load the chosen C candidate in OpenROAD, work in a new empty output directory, and source the frozen absolute `hook.tcl`. Preserve its generated audit files. Then perform global connections, legalization, changed-net routing, RC extraction, and complete final gates. Existing diodes on a target net cause preflight failure rather than duplicate insertion. The final actual antenna report determines whether this trial is sufficient.

Hook SHA256: `2457c1f1fcd79fffad56adf9bf514d23e1246623e942b5b02ada3378cc1003c3`.

Complete remote package manifest SHA256: `c29ee71c17d2a5b02946a7e3b347e8b440826a7b09b592270994ffd7ad8c6dca`.
