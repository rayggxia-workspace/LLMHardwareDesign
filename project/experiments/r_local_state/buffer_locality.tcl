# Keep inserted data buffers with their real fenced producer/consumer.
# Exclusive regions otherwise expel unowned hold/wire buffers into the central
# corridor, turning adjacent logic into a long out-and-back electrical path.
if {![info exists ::r166_locality_installed]} {
 set ::r166_locality_installed 1
 set ::r166_locality_here [file dirname [file normalize [info script]]]
 set ::r166_locality_round 0
 set ::r166_electrical_round 0
 proc r166_host_input {inst location} {
  set block [ord::get_db_block];set dbu [$block getDbUnitsPerMicron]
  lassign $location x y
  foreach region [$block getRegions] {
   foreach box [$region getBoundaries] {
    if {$x*$dbu>=[$box xMin] && $x*$dbu<[$box xMax] && $y*$dbu>=[$box yMin] && $y*$dbu<[$box yMax]} {
     set group [$block findGroup "[$region getName]_cells"]
     if {$group eq "NULL"} {error "Input host group missing"}
     $region addInst $inst;$group addInst $inst
    }
   }
  }
  $inst setLocation [expr {round($x*$dbu)}] [expr {round($y*$dbu)}]
  $inst setPlacementStatus PLACED
 }
 proc r166_data_buffer {inst} {
  set master [[$inst getMaster] getName]
  if {![regexp {^(BUF|CLKBUF)_X[0-9]+$} $master]} {return 0}
  if {[regexp {^r166_(io_|input_|extra_)} [$inst getName]]} {return 0}
  foreach pin [$inst getITerms] {
   set net [$pin getNet]
   if {$net ne "NULL" && [$net getSigType] in {CLOCK POWER GROUND}} {return 0}
  }
  set out [$inst findITerm Z]
  if {$out eq "NULL" || [$out getNet] eq "NULL"} {return 0}
  foreach load [[$out getNet] getITerms] {
   if {[[$load getMTerm] getName] in {CK CLK}} {return 0}
  }
  return 1
 }
 proc r166_real_owner {inst} {
  if {[regexp {^r166_(io_|input_|extra_)} [$inst getName]]} {return NULL}
  set group [$inst getGroup]
  if {$group eq "NULL" || ![regexp {^r166_b[01]_g[0-9]+(_l[0-7])?_cells$} [$group getName]]} {return NULL}
  return $group
 }
 proc r166_physical_host {inst} {
  #193 found101 unfenced NOR2 decode drivers feeding opposite-bank buffers.
  #A global repeater must keep its native physical location; pulling every
  #upstream buffer back from a local consumer recreates a millimetre root net.
  #Assign an actual host when its native chosen centre is inside an exclusive
  #region, allowing DPL to retain distributed repeaters inside that region.
  set box [$inst getBBox]
  set x [expr {([$box xMin]+[$box xMax])/2}]
  set y [expr {([$box yMin]+[$box yMax])/2}]
  set block [ord::get_db_block]
  foreach region [$block getRegions] {
   foreach bounds [$region getBoundaries] {
    if {$x>=[$bounds xMin] && $x<[$bounds xMax] && $y>=[$bounds yMin] && $y<[$bounds yMax]} {
     set group [$block findGroup "[$region getName]_cells"]
     if {$group eq "NULL"} {error "Physical repeater host group missing"}
     return $group
    }
   }
  }
  return NULL
 }
 proc r166_localize_buffers {} {
  set block [ord::get_db_block]
  set out [open $::r166_locality_here/BUFFER_LOCALITY.tsv a]
  incr ::r166_locality_round
  set count 0
  for {set pass 0} {$pass<64} {incr pass} {
   set added 0
   foreach inst [$block getInsts] {
    if {[$inst getGroup] ne "NULL" || [$inst getPlacementStatus] in {LOCKED FIRM} || ![r166_data_buffer $inst]} {continue}
    set input [$inst findITerm A];set output [$inst findITerm Z]
    if {$input eq "NULL" || [$input getNet] eq "NULL"} {continue}
    set owner NULL;set anchor NULL;set rule none
    # A weak original logic/FF output must first drive a nearby buffer.
    # Exclude interface hosts: their global distribution remains unfenced.
    foreach pin [[$input getNet] getITerms] {
     if {[[$pin getMTerm] getIoType] ne "OUTPUT"} {continue}
     set driver [$pin getInst];set group [r166_real_owner $driver]
     if {$group ne "NULL" && ![r166_data_buffer $driver]} {set owner $group;set anchor $driver;set rule producer}
    }
    if {$owner eq "NULL"} {
     set host [r166_physical_host $inst]
     if {$host ne "NULL"} {set owner $host;set anchor $inst;set rule physical_host}
    }
    # Only a true leaf or an already local chain inherits a consumer owner.
    #Do not pull a global root/distribution chain into a remote consumer bank.
    if {$owner eq "NULL" && [llength [[$output getNet] getBTerms]]==0} {
     set candidate NULL;set consumer NULL;set valid 1;set loads 0;set leaves 1;set source_owner NULL
     foreach pin [[$input getNet] getITerms] {
      if {[[$pin getMTerm] getIoType] eq "OUTPUT"} {set source_owner [r166_real_owner [$pin getInst]]}
     }
     foreach pin [[$output getNet] getITerms] {
      if {[[$pin getMTerm] getIoType] ne "INPUT"} {continue}
      incr loads;set load [$pin getInst];set group [r166_real_owner $load]
      if {$group eq "NULL" || ($candidate ne "NULL" && $candidate ne $group)} {set valid 0;break}
      if {[r166_data_buffer $load]} {set leaves 0}
      set candidate $group;set consumer $load
     }
     if {$valid && $loads>0 && ($leaves || $source_owner eq $candidate)} {set owner $candidate;set anchor $consumer;set rule consumer_leaf_or_local}
    }
    if {$owner eq "NULL"} {continue}
    set region [$block findRegion [string range [$owner getName] 0 end-6]]
    if {$region eq "NULL"} {error "Missing actual buffer hosting region"}
    set old [$inst getLocation]
    $region addInst $inst;$owner addInst $inst
    lassign [$anchor getLocation] x y
    $inst setLocation $x $y;$inst setPlacementStatus PLACED
    puts $out "$::r166_locality_round\t$pass\t[$inst getName]\t[[$inst getMaster] getName]\t[$owner getName]\t$rule\t[$anchor getName]\t$old\t$x $y"
    incr added;incr count
   }
   if {$added==0} {break}
  }
  if {$added!=0} {error "Buffer ownership did not converge within 64 passes"}
  close $out
  puts "R166_BUFFER_LOCALITY_ROUND=$::r166_locality_round; newly_owned=$count; clocks_and_interfaces_excluded=1"
  return $count
 }
 rename detailed_placement r166_detailed_placement_native
 proc detailed_placement {args} {
  r166_localize_buffers
  r166_detailed_placement_native {*}$args
 }
 #174 exposed RSZ-3006: electrical repair cannot insert a local driver before
 #a load on a protected hold-delay cell. Open protection only for this repair
 #call; retain every original delay instance, audit any resizing, and restore
 #protection before subsequent timing optimization. Final hold is still exact.
 rename repair_design r166_repair_design_native
 proc repair_design {args} {
  set block [ord::get_db_block];set protected [get_cells -quiet r166_hold_endpoint_*]
  set before [dict create]
  foreach cell $protected {
   set name [get_full_name $cell];set inst [$block findInst $name]
   if {$inst eq "NULL"} {error "Missing protected hold cell $name"}
   dict set before $name [[$inst getMaster] getName]
  }
  if {[llength $protected]} {unset_dont_touch $protected}
  set code [catch {r166_repair_design_native {*}$args} result options]
  set surviving [get_cells -quiet r166_hold_endpoint_*]
  if {[llength $surviving]} {set_dont_touch $surviving}
  incr ::r166_electrical_round
  set out [open $::r166_locality_here/BUFFER_REPAIR_GUARD.tsv a]
  dict for {name master} $before {
   set inst [$block findInst $name]
   if {$inst eq "NULL"} {close $out;error "Electrical repair removed hold-delay instance $name"}
   set after [[$inst getMaster] getName]
   if {![regexp {^(BUF|CLKBUF)_X[0-9]+$} $after]} {close $out;error "Hold delay became non-buffer $name"}
   puts $out "$::r166_electrical_round\t$name\t$master\t$after\tprotection_restored\t$code"
  }
  close $out
  puts "R166_ELECTRICAL_REPAIR_GUARD=$::r166_electrical_round; preserved_delay_instances=[dict size $before]; native_exit=$code"
  return -options $options $result
 }
}
