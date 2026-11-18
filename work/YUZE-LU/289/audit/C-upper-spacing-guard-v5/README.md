# C actual-main upper-spacing investigation

Source: C-v20-native-clock4 actual GDS SHA256 `7a469744bc6a08962009c1e37039dd89385a8fc188412cfa4e1b2b542342dbe2`.

The focused report contains 168 hierarchical items, corresponding to 90 exact category/bounding-box locations. Of these, 68 dot via sites have both parent and leaf reporting. The dot's missing actual cut obstruction inventory is a separate 1970-rectangle repair. The other 22 locations map to parent signal conductors; none mapped to a PG stack. This is a diagnostic classification, not a rule waiver.

R/S actual upper-metal coverage was checked against the installed master OBS and MPin rectangles. Missing coverage was zero; the earlier hypothesis of missing R/S metal OBS was rejected. Six parent standard-cell-to-standard-cell nets run too near R actual M9. The retained v5 hook adds conservative local 0.4um routing keepout at those sites, G M9 and the unrelated S net54927 site. It adds 33 master OBS rectangles and changes no physical metal. Exact MPin rectangles remain open.

S rsp14 and rsp52 sites are excluded entirely to avoid creating a ring around legal pin access or the independent same-net patches. Their geometric repair belongs to `C-m10-notch-*`. The 15-net file records all observed candidates; when preserving these patches, exclude rsp14 and rsp52 from the actual ripup list. E metal/via sites and the exterior cfg request/ready pair have no nearby leaf material to expand; reroute those parent nets and inspect the resulting actual GDS.

Probe 120007 validated first append 33, repeated append 0, unchanged die/BPins/macro geometry, and byte-identical exported Verilog. This proves structural behavior only. The new routing must still pass pin-access, PG, STA/electrical, focused upper/antenna, and the complete original deck. If S's remaining keepout prevents legitimate macro access, adjust its physical routing explicitly rather than weakening final checks.

Use the complete v5 directory: hook code is generic and shares a hash with v4, while binding.tcl and frozen-manifest.json select the correct 33 rectangles. Do not use v4's 43-rectangle plan.

Integration note: this frozen Tcl hook uses global scratch variables (including b for a pin coordinate). The caller must refresh OpenDB block/db/tech handles after sourcing it, or execute it inside a dedicated Tcl namespace. Joint trial120012 exposed this integration collision before routing; CU integration-v2 explicitly re-fetches ord::get_db_block. Do not interpret that script failure as a physical result.
