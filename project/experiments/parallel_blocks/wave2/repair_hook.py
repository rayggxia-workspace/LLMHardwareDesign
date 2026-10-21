"""Build a guarded OpenROAD hook without interpreting Tcl percent expressions in Python."""


def build_hook(replacements):
    script = '''set llhd_block [ord::get_db_block]
set llhd_changes [open [file join $::env(WORK_HOME) .. applied-replacements.txt] w]
proc llhd_find_net {block name} {
  set net [$block findNet $name]
  if {$net ne "NULL"} {return $net}
  set matches {}
  foreach candidate [$block getNets] {
    set normalized [string map [list [format %c 92] {}] [$candidate getName]]
    if {$normalized eq $name} {lappend matches $candidate}
  }
  if {[llength $matches] != 1} {
    set shown 0
    foreach candidate [$block getNets] {
      if {[string match {*g_ask*} [$candidate getName]] && $shown < 12} {
        puts "CHECKPOINT_NET_NAME: [$candidate getName]"
        incr shown
      }
    }
    error "Output net has no unique escaped-name match: $name"
  }
  return [lindex $matches 0]
}
'''
    for replacement in replacements:
        assert len(replacement) in (3, 4)
        assert all(not any(c in value for c in '{}\n\r') for value in replacement)
        name, before, after = replacement[:3]
        if len(replacement) == 4:
            script += '''set llhd_net [llhd_find_net $llhd_block {@@NET@@}]
set llhd_drivers {}
foreach llhd_iterm [$llhd_net getITerms] {
  if {[$llhd_iterm getIoType] eq "OUTPUT"} {lappend llhd_drivers [$llhd_iterm getInst]}
}
if {[llength $llhd_drivers] != 1} {error {Repair net must have exactly one instance driver}}
set llhd_inst [lindex $llhd_drivers 0]
'''.replace('@@NET@@', replacement[3])
        else:
            script += '''set llhd_inst [$llhd_block findInst {@@NAME@@}]
if {$llhd_inst eq "NULL"} {error {Missing repair instance: @@NAME@@}}
'''.replace('@@NAME@@', name)
        script += '''set llhd_name [$llhd_inst getName]
set llhd_sta_inst [sta::find_instance $llhd_name]
if {$llhd_sta_inst eq "NULL"} {
  set llhd_name [string map [list [format %c 92] {}] $llhd_name]
  set llhd_sta_inst [sta::find_instance $llhd_name]
}
if {$llhd_sta_inst eq "NULL"} {error "Resolved ODB driver has no STA instance: $llhd_name"}
set llhd_before [[$llhd_inst getMaster] getName]
if {$llhd_before ne {@@BEFORE@@}} {error "Repair instance master mismatch: $llhd_before"}
if {![replace_cell $llhd_name {@@AFTER@@}]} {error {Equivalent port replacement rejected}}
set_dont_touch [list $llhd_sta_inst]
puts $llhd_changes "$llhd_name $llhd_before -> @@AFTER@@"
'''.replace('@@BEFORE@@', before).replace('@@AFTER@@', after)
    return script+'''close $llhd_changes
detailed_placement_helper
check_placement -verbose
'''
