# Run only against the chosen, fully accepted ODB/SPEF; views are same-source artifacts.
set_thread_count 8
set res $::env(CU_VIEW_RESULTS)
set out $::env(CU_VIEW_OUT)
read_liberty /OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib
foreach lib $::env(CU_LIBS) {read_liberty $lib}
read_db $res/6_final.odb
read_sdc $res/6_final.sdc
read_spef $res/6_final.spef
set_propagated_clock [all_clocks]
sta::find_timing
foreach delay {min max} {if {[sta::endpoint_violation_count $delay]!=0} {error "Cannot export timing-qualified view with $delay violation"}}
foreach kind {capacitance slew fanout} {if {[sta::max_${kind}_violation_count]!=0} {error "Cannot export timing-qualified view with $kind violation"}}
set b [ord::get_db_block]
set top [$b getName]
write_timing_model -library_name ${top}_tt -cell_name $top $out/${top}.lib
write_abstract_lef -bloat_factor 0 $out/${top}-raw.lef
set f [open $out/source-interface.tsv w]
foreach bt [$b getBTerms] {puts $f "[$bt getName]\t[$bt getIoType]\t[$bt getSigType]"}
close $f
source /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/geometry.tcl
geometry_snapshot $out/source-geometry.tsv
puts VIEWS_EXPORTED_REQUIRE_INDEPENDENT_LEF_LIB_RELOAD_AND_FULL_GEOMETRY_CUT_GUARD