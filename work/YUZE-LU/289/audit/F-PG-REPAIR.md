# F new-S power-grid collision audit

F-v4 passes reported extracted timing/electrical/antenna gates but fails PSM at 12 parent VDD-to-S M9 intersections. These are real signal locations, not a reason to suppress PSM.

Read-only DEF tracing, using S origin (72,72) um and R0, maps the 12 marker rectangles to new S signal segments: rsp_data[84] (1), rsp_data[62] (1), net7857 (3), rsp_data[26] (7). net7857 explicitly connects max_cap7857/Z to storage banks 1 and 3 din0[75], USE SIGNAL. The result is S-parent-pg-net-trace.json. The tracer uses route centerlines and M9 width 0.8 um; final ODB/GDS inspection and merged DRC remain the authoritative checks.

The original F300 config inherits PDN_TCL and POST_PDN_TCL from issue250-f-native-frame-20261112-01. pdn.tcl creates parent M1/M4/M7/M10 stripes and M7-to-M10 stacks over macro PG pins. post-pdn.tcl calls `pj_filter_pg` from `/public/home/yuzelu/project-circuit/issue250-cfj-e32-20261111-03/source/project/experiments/cfj_leaf_base/filter_pg_landings.tcl`. Its old pg-removed.tsv already records removed VDD stacks near S/G upper obstructions.

The filter indexes actual master signal pins on M7-M10 and OBS on M8-M10 with a 3000 DBU (1.5 um) guard. It checks R0/zero macro origin and 2000 DBU/um, identifies complete three-part parent stacks ({7 8}, {8 9}, {9 10}) at a common location, and removes the whole stack if any landing collides. It preserves leaf wires, abstract metal and parent stripes. It aborts on an incomplete stack or disconnected VDD/VSS. New F-v4 retained the old parent PG and did not rerun this filter against the changed S geometry.

Recommended repair: after rebuilding F against new nativeguard LEFs, invoke this existing filter with the exact actual macro instance list and a new own-run pg-removed.tsv before signal rerouting. Keep all assertions, then reroute, extract RC and repeat timing/electrical, antenna, complete power-grid checks and merged GDS DRC. Do not replay old removal coordinates or cut only one metal landing. If the preserved grid loses connectivity, regenerate PDN respecting the new abstractions or construct validated alternative PG access; do not weaken PSM or alter the accepted S signal routing merely to hide a short. A PG-only ECO to an already routed candidate also requires refreshed streamout/RCX/checks and must record all removed stacks and grid continuity.

## localv4 alternative preserves original upper wiring

Read-only comparison against the original accepted S DEF (SHA ed81f7dbbaebf001cd3d640569bd6e40b33e001de261946d6acb7b5f613267a1) gives:

- minimal: all 1196 signal route records referencing M9/M10 or via8/via9 are exactly identical by net and line. No new upper metal relative to the source that worked with original parent PG.
- hold08: removes one original $abc$2382$new_n1248 M10 segment and its via8/via9 accesses. req_ready changes only ROUTED/NEW prefix. No new upper geometry.
- hold03: req_ready M10 splits into equivalent segments and adds M9 x152.095–156.895 um at y505.67 um, moving via8 to the right endpoint. At parent S origin (72,72) this is x224.095–228.895/y577.67 um. A fast SPECIALNETS M9/via8/via9 center search within 5 um found no PG landing. This is a screening result, not full DRC.

These local variants avoid the broad v3 upper-metal changes responsible for the 12 M9 and 2 M10 shorts. Prefer minimal or hold08 according to their timing/physical acceptance. Full power-grid checks and merged GDS DRC remain required. No parent stripe/BPin surgery is needed based on this screening; the strict original pin contract remains intact.
