"""Locate reported global-route electrical failures in the exact unchanged DB."""
from pathlib import Path
import argparse,hashlib,json,subprocess,re
p=argparse.ArgumentParser();p.add_argument('--physical',type=Path,required=True);p.add_argument('--capacity',type=int,required=True);a=p.parse_args()
R=a.physical/'flow/results/nangate45'/('r166_'+str(a.capacity))/'base'
report=a.physical/'flow/reports/nangate45'/('r166_'+str(a.capacity))/'base/5_global_route.rpt'
O=Path.cwd()/'global-driver-audit';O.mkdir(exist_ok=False)
sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
inputs={str(f):sha(f)for f in [R/'5_1_grt.odb',report]}
section=report.read_text().split('report_check_types -max_slew -max_cap -max_fanout -violators',1)[1].split('global route max_',1)[0]
pins=sorted(set(re.findall(r'^(\S+/\S+)\s+.*\(VIOLATED\)$',section,re.M)))
assert pins
(O/'pins.txt').write_text('\n'.join(pins)+'\n')
t='''set_thread_count 1
read_db {%s}
set b [ord::get_db_block]
set canonical [dict create]
foreach cell [$b getInsts] {
 set key [string map [list [format %%c 92] {}] [$cell getName]]
 if {[dict exists $canonical $key]} {error "Ambiguous normalized instance $key"}
 dict set canonical $key $cell
}
set input [open pins.txt r];set out [open drivers.tsv w]
puts $out "DRIVER\tmaster\tstatus\tnet\tfanout\tspan_x_dbu\tspan_y_dbu\tgroup"
while {[gets $input pin]>=0} {
 set split [string last / $pin];set name [string range $pin 0 [expr {$split-1}]];set term [string range $pin [expr {$split+1}] end]
 set inst [$b findInst $name]
 if {$inst eq "NULL" && [dict exists $canonical $name]} {set inst [dict get $canonical $name]}
 if {$inst eq "NULL"} {error "Missing exact reported driver $name"}
 set it [$inst findITerm $term];if {$it eq "NULL" || [$it getNet] eq "NULL"} {error "Missing actual net $pin"}
 set net [$it getNet];lassign [$inst getLocation] dx dy;set xs [list $dx];set ys [list $dy];set count 0
 foreach load [$net getITerms] {
  if {[[$load getMTerm] getIoType] ne "INPUT"} {continue}
  incr count;set cell [$load getInst];lassign [$cell getLocation] x y;lappend xs $x;lappend ys $y
  puts $out "LOAD\t$pin\t[$cell getName]\t[[$cell getMaster] getName]\t$x\t$y"
 }
 set xs [lsort -integer $xs];set ys [lsort -integer $ys];set group [$inst getGroup];set owner none
 if {$group ne "NULL"} {set owner [$group getName]}
 puts $out "$pin\t[[$inst getMaster] getName]\t[$inst getPlacementStatus]\t[$net getName]\t$count\t[expr {[lindex $xs end]-[lindex $xs 0]}]\t[expr {[lindex $ys end]-[lindex $ys 0]}]\t$owner"
}
close $input;close $out
'''%str(R/'5_1_grt.odb')
(O/'probe.tcl').write_text(t)
with(O/'probe.log').open('w')as log:r=subprocess.run(['openroad','-no_init','-exit','probe.tcl'],cwd=O,stdout=log,stderr=subprocess.STDOUT)
assert inputs=={f:sha(Path(f))for f in inputs}
rec=dict(passed=r.returncode==0,reported_drivers=len(pins),inputs=inputs,scope='Read-only actual global-route reported-driver ownership, fanout and geometry; no final timing or qualification.')
if(O/'drivers.tsv').is_file():rec['drivers_sha256']=sha(O/'drivers.tsv')
(O/'receipt.json').write_text(json.dumps(rec,indent=2)+'\n');raise SystemExit(r.returncode)
