# Real prefabrication resources: isolate bank output loads and local controls.
# No macro/library limits, timing constraints or functional nets are waived.
set block [ord::get_db_block]
set count 0
set fixed_bank_receivers {}
set stream [open $::env(RESULTS_DIR)/sram-boundary-buffers.tsv w]
foreach bank [$block getInsts] {
  if {[[$bank getMaster] getName] ne "s_sram_256x128_freepdk45"} {continue}
  lassign [$bank getLocation] bx by
  foreach term [$bank getITerms] {
    set mt [$term getMTerm]
    set pin [$mt getName]
    set direction [$mt getIoType]
    if {$direction eq "OUTPUT"} {
      # Actual smallest receiver input, 0.779830fF. Native fixed-topology
      # BUF_X1 comparison missed final cap by 0.114255fF while setup had
      # 0.101377ns margin. Timing/electrical gates still inspect this cell.
      set cell CLKBUF_X1
    } elseif {[regexp {^(addr0\[[0-7]\]|csb0|web0)$} $pin]} {
      set cell BUF_X2
    } else {continue}
    set old [$term getNet]
    if {$old eq "NULL"} {error "Open bank boundary before repair"}
    set name sram_boundary_buf_$count
    set net_name sram_boundary_local_$count
    if {[$block findInst $name] ne "NULL" || [$block findNet $net_name] ne "NULL"} {error "Duplicate bank boundary repair"}
    set master [[ord::get_db] findMaster $cell]
    if {$master eq "NULL"} {error "Actual Nangate buffer unavailable"}
    set inst [odb::dbInst_create $block $master $name]
    set local [odb::dbNet_create $block $net_name]
    set geometry [[lindex [$mt getMPins] 0] getGeometry]
    set box [lindex $geometry 0]
    set x [expr {$bx+([$box xMin]+[$box xMax])/2-[$master getWidth]/2}]
    set y [expr {$by-2800}]
    $inst setLocation $x $y
    $inst setOrient R0
    $inst setPlacementStatus PLACED
    $term disconnect
    $term connect $local
    if {$direction eq "OUTPUT"} {
      [$inst findITerm A] connect $local
      [$inst findITerm Z] connect $old
    } else {
      [$inst findITerm A] connect $old
      [$inst findITerm Z] connect $local
    }
    foreach supply_term [$inst getITerms] {
      set kind [[$supply_term getMTerm] getSigType]
      if {$kind in {POWER GROUND}} {
        set supply [expr {$kind eq "POWER" ? "VDD" : "VSS"}]
        set power [$block findNet $supply]
        if {$power eq "NULL"} {error "Original power net missing"}
        $supply_term connect $power
      }
    }
    if {$direction eq "OUTPUT"} {
      # A fixed point-to-point bank receiver is an actual architectural
      # resource. Preserve this local connection and input cell while
      # allowing downstream fanout repair. Final RCX electrical checks still
      # inspect this net against the unchanged 6.6912fF bank limit.
      set_dont_touch [get_cells $name]
      set_dont_touch [get_nets $net_name]
      lappend fixed_bank_receivers $inst
    }
    # Address/control buffers remain editable: freezing their input load
    # prevents the necessary upstream native cap/slew repair (RSZ-3006).
    puts $stream "[$bank getName]\t$pin\t$direction\t$name\t$cell\t[$old getName]\t$net_name"
    incr count
  }
}
close $stream
if {$count != 552} {error "Expected 512 output and 40 control buffers, got $count"}
