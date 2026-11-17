# Apply a stricter implementation spacing rule only to actually diagnosed nets.
# Original full-deck acceptance thresholds and physical BPin geometry are unchanged.
proc i289_apply_upper_ndr {} {
 set b [ord::get_db_block]
 set tech [ord::get_db_tech]
 set margin 1.2
 if {[info exists ::env(U_UPPER_MARGIN)]} {set margin $::env(U_UPPER_MARGIN)}
 if {$margin ni {1.0 1.2 1.4}} {error "Unreviewed upper-spacing implementation variant $margin"}
 set by_name [dict create]
 foreach n [$b getNets] {
  set normalized [string map [list "\\" ""] [$n getName]]
  dict lappend by_name $normalized $n
 }
 set specs [list \
  [list m9 [list {datapath.legacy_rsp_data[90]} {incoming_data[29]} {dma_wr_data[491]} {incoming_data[111]} {dma_rd_rsp_tag[16]} {dma_rd_tag[59]}]] \
  [list m9m10 [list {net22350} {datapath.legacy_rsp_data[78]}]]]
 set log [open upper-ndr-changes.tsv w]
 foreach spec $specs {
  lassign $spec family names
  set rule_name "i289_upper_${family}_[expr {int($margin*1000)}]"
  set spacing [list metal9 $margin]
  if {$family eq "m9m10"} {lappend spacing metal10 $margin}
  create_ndr -name $rule_name -width {*1} -spacing $spacing
  set found {}
  foreach r [$b getNonDefaultRules] {if {[$r getName] eq $rule_name} {lappend found $r}}
  if {[llength $found]!=1} {error "Missing exact new NDR $rule_name"}
  set rule [lindex $found 0]
  $rule setHardSpacing 1
  if {![$rule getHardSpacing]} {error "NDR spacing is not hard"}
  foreach name $names {
   if {![dict exists $by_name $name] || [llength [dict get $by_name $name]]!=1} {error "Missing/ambiguous diagnosed signal net $name"}
   set net [lindex [dict get $by_name $name] 0]
   if {[$net getSigType] in {POWER GROUND CLOCK}} {error "Unexpected diagnosed net type $name"}
   set old [$net getNonDefaultRule]
   if {$old ne "NULL"} {error "Refuse to replace an existing rule on $name"}
   $net setNonDefaultRule $rule
   if {[$net getNonDefaultRule] ne $rule} {error "NDR assignment failed $name"}
   set wire [$net getWire]
   if {$wire ne "NULL"} {odb::dbWire_destroy $wire}
   puts $log "[$net getName]\t$rule_name\t$spacing\thard\tripped"
  }
 }
 close $log
 puts "EXACT_8_UPPER_NETS_HAVE_STRICTER_SPACING_AND_ARE_RIPPED"
}
i289_apply_upper_ndr
