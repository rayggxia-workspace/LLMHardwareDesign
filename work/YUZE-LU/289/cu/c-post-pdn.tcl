proc find_master {name} {
    set selected {}
    foreach inst [[ord::get_db_block] getInsts] {
        if {[[$inst getMaster] getName] eq $name} {lappend selected $inst}
    }
    if {[llength $selected] != 1} {error "Expected one $name in this fixture"}
    return [lindex $selected 0]
}
source {/public/home/yuzelu/project-circuit/issue250-cfj-e32-20261111-03/source/project/experiments/cfj_leaf_base/filter_pg_landings.tcl}
set macros [list [[find_master {local_s_base}] getName] [[find_master {block_v2_e_compact}] getName] [[find_master {block_v2_g}] getName] [[find_master {r_stream_local}] getName] [[find_master {e_s32_pipeline_128}] getName]]
pj_filter_pg $macros $::env(REPORTS_DIR)/pg-removed.tsv
