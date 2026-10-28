"""Bounded input-delay-cell experiment on immutable S/T CTS snapshots.

No constraints change, no qualification, and no production-flow modification.
All data inputs receive the same finite 24 BUF_X1 chain; clock and the actual
input antenna remain on the original root. Measure both setup and hold after
legal placement rather than inferring cell delays from a nominal estimate.
"""
import json
from pathlib import Path


def probe(root, out, cpus, run, kind):
    from io_slots import file_sha
    assert cpus == 16 and kind in ('s', 't')
    base = out.parents[2]
    source = base/('block-v1-20261028-237/tasks/revision300-cts-probe' if kind == 't'
                  else 'block-v1-20261028-240/tasks/revision300-cts-probe-s')
    receipt = json.loads((source/'receipt.json').read_text())
    assert receipt['passed'] is (kind == 's')
    top = 'bv1_transaction6k' if kind == 't' else 'bv1_block_v1_s16k'
    results = source/('flow/results/nangate45/'+top+'/base')
    files = [results/('4_1_pre_repair_setup_hold.'+suffix) for suffix in ('odb', 'sdc')]
    bound = {str(p): file_sha(p) for p in files}
    for p in files:
        assert file_sha(p) == receipt['outputs'][str(p.relative_to(source))]
    platform = Path('/OpenROAD-flow-scripts/flow/platforms/nangate45')
    (out/'native-cts-script.txt').write_bytes(Path('/OpenROAD-flow-scripts/flow/scripts/cts.tcl').read_bytes())
    body = 'set_thread_count 16\nread_liberty {'+str(platform/'lib/NangateOpenCellLibrary_typical.lib')+'}\n'
    body += 'read_db {'+str(files[0])+'}\nread_sdc {'+str(files[1])+'}\nsource {'+str(platform/'setRC.tcl')+'}\n'
    body += '''set_propagated_clock [all_clocks]
estimate_parasitics -placement
report_worst_slack -min -digits 9 > before-summary.rpt
report_worst_slack -max -digits 9 >> before-summary.rpt
set block [ord::get_db_block]
set master [[ord::get_db] findMaster BUF_X1]
if {$master eq "NULL"} {error "BUF_X1 absent"}
set inventory [open input-delay.tsv w]
set count 0
set ports 0
foreach port [$block getBTerms] {
  if {[$port getIoType] ne "INPUT" || [$port getSigType] in {POWER GROUND} || [$port getName] eq "clk"} {continue}
  set original [$port getNet]
  if {$original eq "NULL"} {error "Floating input"}
  set loads {}
  foreach term [$original getITerms] {
    if {[[$term getMTerm] getIoType] eq "INPUT" && [[$term getMTerm] getSigType] ni {POWER GROUND} && [[$term getInst] getMaster] ne [[ord::get_db] findMaster ANTENNA_X1]} {
      lappend loads $term
    }
  }
  if {[llength $loads] == 0} {continue}
  set anchor [[lindex $loads 0] getInst]
  lassign [$anchor getLocation] x y
  set previous $original
  for {set stage 0} {$stage < 24} {incr stage} {
    set name bv1_delay_probe_$count
    if {[$block findInst $name] ne "NULL" || [$block findNet ${name}_Z] ne "NULL"} {error "Duplicate delay object"}
    set inst [odb::dbInst_create $block $master $name]
    set next [odb::dbNet_create $block ${name}_Z]
    $inst setLocation $x $y
    $inst setOrient [$anchor getOrient]
    $inst setPlacementStatus PLACED
    [$inst findITerm A] connect $previous
    [$inst findITerm Z] connect $next
    foreach term [$inst getITerms] {
      set type [[$term getMTerm] getSigType]
      if {$type in {POWER GROUND}} {
        set supply [$block findNet [expr {$type eq "POWER" ? "VDD" : "VSS"}]]
        if {$supply eq "NULL"} {error "Supply absent"}
        $term connect $supply
      }
    }
    puts $inventory "$name\t[$port getName]\t$stage\t[$previous getName]\t[$next getName]"
    set previous $next
    incr count
  }
  foreach term $loads {$term disconnect; $term connect $previous}
  incr ports
}
close $inventory
if {$count != 24*$ports || $ports == 0} {error "Delay inventory mismatch"}
# Synchronize STA after OpenDB edits; retain each explicit physical delay cell.
foreach cell [get_cells bv1_delay_probe_*] {set_dont_touch $cell}
detailed_placement
check_placement -verbose
estimate_parasitics -placement
report_worst_slack -min -digits 9 > padded-summary.rpt
report_worst_slack -max -digits 9 >> padded-summary.rpt
report_checks -path_delay min_max -group_path_count 10 -digits 9 -format full_clock_expanded > padded.rpt
report_check_types -max_capacitance -max_slew -violators -digits 9 > padded-electrical.rpt
write_db padded.odb
write_verilog padded.v
write_sdc -digits 12 padded.sdc
set status [catch {repair_timing -hold -max_buffer_percent 20 -hold_margin 0.020 -verbose} message]
set stream [open repair-status.txt w]
puts $stream [list $status $message]
close $stream
detailed_placement
check_placement -verbose
estimate_parasitics -placement
report_worst_slack -min -digits 9 > repaired-summary.rpt
report_worst_slack -max -digits 9 >> repaired-summary.rpt
report_checks -path_delay min_max -group_path_count 10 -digits 9 -format full_clock_expanded > repaired.rpt
report_check_types -max_capacitance -max_slew -violators -digits 9 > repaired-electrical.rpt
write_db repaired.odb
write_verilog repaired.v
write_sdc -digits 12 repaired.sdc
puts "BV1_DELAY_PROBE ports=$ports buffers=$count"
'''
    (out/'input-delay.tcl').write_text(body)
    run(['openroad', '-no_init', '-exit', out/'input-delay.tcl'], 'input-delay.log')
    assert all(file_sha(Path(name)) == digest for name, digest in bound.items())
    inventory = (out/'input-delay.tsv').read_text().splitlines()
    assert inventory and len(inventory) % 24 == 0
    result = dict(passed=True, source_receipt_sha256=file_sha(source/'receipt.json'),
                  source_files_sha256=bound, source_unchanged=True, stages_per_input=24,
                  buffer_count=len(inventory), input_count=len(inventory)//24,
                  qualified_hard_macro=False, max_buffer_percent=20, hold_margin_ns=0.020,
                  scope='Physical input-delay plus ordinary hold-repair probe only; placement RC, no route or final acceptance')
    (out/'revision300-input-delay-probe.json').write_text(json.dumps(result, indent=2)+'\n')
