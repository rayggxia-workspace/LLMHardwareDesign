# Physical buffering only: break measured 66k/62k-load mux-select nets into
# spatial groups before native resizer constructs Steiner trees. Clock is CTS.
# No logic/timing exceptions, no protected buffers: final resizer and gates apply.
set feed_block [ord::get_db_block]
set feed_master [[ord::get_db] findMaster BUF_X8]
if {$feed_master eq "NULL"} {error "Missing native fanout buffer"}
set feed_dbu [$feed_block getDbUnitsPerMicron]
set feed_pitch [expr {128*$feed_dbu}]
set feed_candidates {}
foreach net [$feed_block getNets] {
  if {[$net getSigType] in {POWER GROUND CLOCK}} {continue}
  if {[llength [$net getITerms]]>2048} {lappend feed_candidates $net}
}
set feed_count 0
set feed_report [open $::env(RESULTS_DIR)/feed-partition-fanout.tsv w]
foreach net $feed_candidates {
  if {[llength [$net getBTerms]]} {error "Unexpected high-fanout external root"}
  set drivers {};set loads {};set bins {}
  foreach term [$net getITerms] {
    set direction [[$term getMTerm] getIoType]
    if {$direction eq "OUTPUT"} {lappend drivers $term;continue}
    if {$direction ne "INPUT"} {error "Ambiguous fanout direction"}
    lappend loads $term
    lassign [[$term getInst] getLocation] x y
    set key [list [expr {$x/$feed_pitch}] [expr {$y/$feed_pitch}]]
    dict lappend bins $key [list $term $x $y]
  }
  if {[llength $drivers]!=1} {error "Fanout net must have exactly one driver"}
  set covered 0;set groups 0
  dict for {key members} $bins {
    for {set start 0} {$start<[llength $members]} {incr start 256} {
      set group [lrange $members $start [expr {$start+255}]]
      set name feed_fanout_$feed_count
      if {[$feed_block findInst $name] ne "NULL" || [$feed_block findNet ${name}_net] ne "NULL"} {error "Duplicate fanout object"}
      set newnet [odb::dbNet_create $feed_block ${name}_net]
      set sx 0;set sy 0
      foreach row $group {
        lassign $row term x y
        if {[$term getNet] ne $net} {error "Fanout load changed before partition"}
        $term disconnect;$term connect $newnet
        incr sx $x;incr sy $y;incr covered
      }
      set size [llength $group]
      set x [expr {int(round($sx/double($size)))}]
      set y [expr {int(round($sy/double($size)))}]
      set inst [odb::dbInst_create $feed_block $feed_master $name]
      $inst setLocation $x $y;$inst setOrient R0;$inst setPlacementStatus PLACED
      [$inst findITerm A] connect $net
      [$inst findITerm Z] connect $newnet
      foreach term [$inst getITerms] {
        set kind [[$term getMTerm] getSigType]
        if {$kind in {POWER GROUND}} {
          set supply [expr {$kind eq "POWER" ? "VDD" : "VSS"}]
          set pg [$feed_block findNet $supply]
          if {$pg eq "NULL"} {error "Missing native supply"}
          $term connect $pg
        }
      }
      if {[llength [$newnet getITerms]]!=$size+1} {error "Partition coverage mismatch"}
      puts $feed_report "$name\t[$net getName]\t[$newnet getName]\t$size\t$x\t$y"
      incr feed_count;incr groups
    }
  }
  if {$covered!=[llength $loads] || [llength [$net getITerms]]!=$groups+1 || $groups>1024} {error "Incomplete or excessive fanout partition"}
  foreach driver $drivers {if {[$driver getNet] ne $net} {error "Original driver changed"}}
  puts "FEED_FANOUT [$net getName]: $covered loads -> $groups groups"
}
close $feed_report
if {$feed_count==0} {error "Expected measured high fanout was absent"}
global_connect
detailed_placement_helper
check_placement -verbose
puts "FEED_FANOUT inserted $feed_count native buffers; downstream native repair remains enabled"
