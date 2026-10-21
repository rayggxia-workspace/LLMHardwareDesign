# Fast Tcl scope regression with mocked OpenDB/native-PG calls. This is not EDA
# evidence. Actual ORFS hooks and compute-node PG/route checks remain required.
set test_source [file dirname [info script]]
set test_output [lindex $argv 0]
if {$test_output eq "" || [file exists $test_output]} {
  error "Supply a new output directory"
}
file mkdir $test_output
set mock_objects {}
set mock_removed {}
set mock_native_calls 0
set mock_writes 0
set mock_native_false 0

proc mock_put {name methods} {
  global mock_objects
  dict set mock_objects $name $methods
  if {[info commands $name] eq ""} {interp alias {} $name {} mock_call $name}
}
proc mock_call {name method args} {
  global mock_objects mock_removed
  if {$name eq "block" && $method eq "findInst"} {return inst}
  if {$name eq "block" && $method eq "findNet"} {return net_[lindex $args 0]}
  if {$name eq "master" && $method eq "findMTerm"} {return pin_[lindex $args 0]}
  if {$method eq "getWires"} {
    set result {}
    foreach box [dict get $mock_objects $name $method] {
      if {$box ni $mock_removed} {lappend result $box}
    }
    return $result
  }
  return [dict get $mock_objects $name $method]
}
proc mock_box {name layer rect} {
  lassign $rect a b c d
  mock_put $name [dict create getTechLayer $layer xMin $a yMin $b xMax $c yMax $d]
}
proc mock_reset {bad} {
  global mock_removed mock_native_calls mock_writes mock_native_false
  set mock_removed {}; set mock_native_calls 0; set mock_writes 0; set mock_native_false 0
  mock_put block {}
  mock_put inst {getOrient R0 getLocation {160000 160000} getMaster master getBBox bbox getITerms {it_VDD it_VSS}}
  mock_box bbox metal7 {160000 160000 2457040 2457040}
  mock_put master {getName vec_engine getOrigin {0 0} getObstructions {obs7 obs8 obs9}}
  foreach level {7 8 9 10} {mock_put metal$level [dict create getName metal$level getRoutingLevel $level]}
  mock_box obs7 metal7 {0 0 100000 2800}
  mock_box obs8 metal8 {5000 400 6000 800}
  mock_box obs9 metal9 {5000 50000 6000 51000}
  foreach supply {VDD VSS} y {0 10000} kind {POWER GROUND} {
    mock_box pg_$supply metal7 [list 0 $y 100000 [expr {$y+2800}]]
    mock_put mp_$supply [dict create getGeometry pg_$supply]
    mock_put pin_$supply [dict create getMPins mp_$supply getName $supply getSigType $kind]
    mock_put it_$supply [dict create getMTerm pin_$supply getNet net_$supply]
    mock_put net_$supply [dict create getName $supply getSWires wire_$supply]
    set boxes {}
    foreach x [expr {$bad && $supply eq "VDD" ? {165000 190000} : {190000}}] {
      foreach edge {7_8 8_9 9_10} {
        set box via_${supply}_${x}_${edge}
        mock_put $box [dict create isVia 1 getTechVia tech_$edge getViaXY [list $x [expr {160000+$y+1400}]]]
        lappend boxes $box
      }
    }
    mock_put wire_$supply [dict create getWires $boxes]
  }
  foreach edge {7_8 8_9 9_10} {
    lassign [split $edge _] lo hi
    mock_box shape_${edge}_lo metal$lo {-200 -200 200 200}
    mock_box shape_${edge}_hi metal$hi {-200 -200 200 200}
    mock_put tech_$edge [dict create getName tech_$edge getBoxes [list shape_${edge}_lo shape_${edge}_hi]]
  }
}
namespace eval ord {
  proc get_db_block {} {return block}
  proc dbu_to_microns {value} {return [expr {$value/2000.0}]}
}
namespace eval odb {
  proc dbSBox_destroy {box} {lappend ::mock_removed $box}
}
proc read_db {path} {mock_reset [expr {$path eq "bad"}]}
proc write_db {path} {incr ::mock_writes; error "Unexpected DB write in check-only audit"}
proc check_power_grid {args} {
  incr ::mock_native_calls
  return [expr {!$::mock_native_false}]
}
# The real ORFS hook is sourced inside a procedure, not the global frame.
proc source_env_var_if_exists {name} {source $::env($name)}
proc prepare_case {name} {
  global test_source test_output
  set dir [file join $test_output $name]
  file mkdir $dir
  foreach script {filter_pg_access.tcl check_pdn_connectivity.tcl post_pdn_check.tcl audit_pdn.tcl} {
    file copy [file join $test_source $script] $dir
  }
  set ::env(LLHD_ATTEMPT) $dir
  set ::env(LLHD_MACRO_PDN) legal-m10
  return $dir
}
proc require {value message} {if {!$value} {error $message}}
proc contents {path} {set f [open $path]; set text [read $f]; close $f; return $text}

set dir [prepare_case mutate]
mock_reset 1
unset -nocomplain ::env(LLHD_PG_FILTER_AUDIT)
set ::env(TEST_HOOK) [file join $dir post_pdn_check.tcl]
source_env_var_if_exists TEST_HOOK
require [expr {[llength $mock_removed] == 3 && $mock_native_calls == 2}] "mode1 did not delete a whole stack and run both strict PG calls"
require [expr {[string first {"remaining_guard_intersections": 0} [contents $dir/pg-access-selection.json]] >= 0}] "mode1 residual geometry failed"

set dir [prepare_case readonly]
set ::env(LLHD_PG_FILTER_AUDIT) 2
set ::env(LLHD_AUDIT_DB) good
set ::env(TEST_HOOK) [file join $dir audit_pdn.tcl]
source_env_var_if_exists TEST_HOOK
require [expr {[llength $mock_removed] == 0 && $mock_writes == 0 && $mock_native_calls == 2}] "mode2 mutated DB or skipped strict PG calls"

set dir [prepare_case readonly_unsafe]
set ::env(LLHD_AUDIT_DB) bad
set ::env(TEST_HOOK) [file join $dir audit_pdn.tcl]
set code [catch {source_env_var_if_exists TEST_HOOK} value]
require [expr {$code == 1 && [llength $mock_removed] == 0 && $mock_writes == 0 && $mock_native_calls == 0}] "unsafe mode2 did not fail before native checks without mutation"

set dir [prepare_case native_false]
mock_reset 0
set mock_native_false 1
unset ::env(LLHD_PG_FILTER_AUDIT)
set ::env(TEST_HOOK) [file join $dir post_pdn_check.tcl]
set code [catch {source_env_var_if_exists TEST_HOOK} value]
require [expr {$code == 1 && $mock_native_calls == 2}] "normal false native return incorrectly accepted"
puts "MOCK PROC-SOURCE SCOPE PASS: mutation, check-only, unsafe check-only, strict native false"
