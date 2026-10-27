# Native Liberty metadata inventory; no timing model modification.
if {[catch {
  read_liberty $::env(BV1QA_MODEL)
  set cells [get_lib_cells $::env(BV1QA_CELL)]
  if {[llength $cells] != 1} {error "Expected one exactly scoped model cell"}
  set cell [lindex $cells 0]
  set stream [open model-ports.tsv w]
  foreach port [get_lib_pins $::env(BV1QA_CELL)/*] {
    if {[$port is_bus]} {continue}
    puts $stream "[get_full_name $port]\t[get_property $port direction]\t[$port is_pwr_gnd]"
  }
  close $stream
  set groups [open model-arc-groups.tsv w]
  set arcs [open model-arcs.tsv w]
  set index 0
  foreach group [$cell timing_arc_sets] {
    set from [$group from]
    set to [$group to]
    if {$to eq "NULL"} {error "Unsupported null model arc destination"}
    set to_name [get_full_name $to]
    if {$from eq "NULL"} {
      # Native clock-tree groups can have no related/source port. Calling
      # get_full_name on this group dereferences from() in this STA version.
      # Preserve the group explicitly, without inventing a resolved role.
      set from_name __NO_FROM_PIN__
      set group_name "$from_name -> $to_name native-null-from-role-unresolved"
    } else {
      set from_name [get_full_name $from]
      set group_name [get_full_name $group]
    }
    set members [$group timing_arcs]
    puts $groups "$index\t$from_name\t$to_name\t$group_name\t[sta::timing_role_is_check [$group role]]\t[binary encode hex [encoding convertto utf-8 [$group when]]]\t[llength $members]"
    set subindex 0
    foreach arc $members {
      set edge none
      if {[$arc from_edge] ne "NULL"} {set edge [$arc from_edge_name]}
      puts $arcs "$index\t$subindex\t$edge\t[$arc to_edge_name]"
      incr subindex
    }
    incr index
  }
  close $groups
  close $arcs
} problem options]} {
  puts stderr "BV1QA_MODEL_INVENTORY_FAILURE: $problem"
  puts stderr [dict get $options -errorinfo]
  exit 1
}
exit 0
