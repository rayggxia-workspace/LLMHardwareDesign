"""Read-only post-GRT S reset branch measurements; no timing qualification."""
import hashlib,json,os,re,subprocess
from pathlib import Path


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb')as stream:
        for data in iter(lambda:stream.read(1048576),b''):h.update(data)
    return h.hexdigest()


def slacks(path):
    text=path.read_text()
    return [float(value)for value in re.findall(r'([-+]?\d+\.\d+)\s+slack \((?:MET|VIOLATED)\)',text)]


def inspect(a):
    assert os.environ.get('SLURM_JOB_ID')and len(os.sched_getaffinity(0))<=16
    base=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162').resolve()
    folder=a.s_grt_folder.resolve();assert base in folder.parents
    assert folder.name=='base'and folder.parent.name=='bv1_block_feed_s_macro'
    a.out=a.out.resolve();assert base in a.out.parents;a.out.mkdir(parents=True,exist_ok=False)
    lib=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib')
    rc=lib.parents[1]/'setRC.tcl';odb=folder/'5_1_grt.odb';sdc=folder/'5_1_grt.sdc'
    report=folder.parents[3]/'reports/nangate45/bv1_block_feed_s_macro/base/5_global_route.rpt'
    inputs={str(p):sha(p)for p in [odb,sdc,lib,rc,report,Path(__file__)]}
    receipt=dict(passed=False,diagnostic_only=True,native_leaf_qualified=False,whole_system_qualified=False,
        inputs=inputs,job=os.environ['SLURM_JOB_ID'],
        scope='Read-only completed post-GRT S database; placement RC only for branch diagnostics. Original global-route report separately bound. No new cells, wires, constraints or qualification.')
    try:
        script='set_thread_count 16\nread_liberty {'+str(lib)+'}\nread_db {'+str(odb)+'}\nread_sdc {'+str(sdc)+'}\nsource {'+str(rc)+'}\nestimate_parasitics -placement\n'
        script+=r'''
set block [ord::get_db_block]
if {[$block getName] ne "block_feed_s_macro"} {error "S diagnostic scope mismatch"}
set reset [$block findBTerm reset]
if {$reset eq "NULL" || [$reset getIoType] ne "INPUT"} {error "Missing actual S reset input"}
set todo [list [list [$reset getNet] 0]]
set visited [dict create];set branches {};set buffers {}
while {[llength $todo]} {
 lassign [lindex $todo 0] net depth;set todo [lrange $todo 1 end]
 if {$depth>16 || [dict size $visited]>4096} {error "Unexpected reset buffer cone"}
 if {[dict exists $visited [$net getName]]} {continue}
 dict set visited [$net getName] 1
 foreach pin [$net getITerms] {
  if {[[$pin getMTerm] getSigType] in {POWER GROUND} || [[$pin getMTerm] getIoType] ne "INPUT"} {continue}
  set inst [$pin getInst];set master [[$inst getMaster] getName]
  if {[regexp {^(BUF|CLKBUF)_X[0-9]+$} $master]} {
   set outputs {}
   foreach term [$inst getITerms] {
    if {[[$term getMTerm] getSigType] ni {POWER GROUND} && [[$term getMTerm] getIoType] eq "OUTPUT"} {lappend outputs $term}
   }
   if {[llength $outputs]!=1} {error "Reset buffer output identity"}
   lappend buffers [list [$inst getName] $master [$net getName]]
   lappend todo [list [[lindex $outputs 0] getNet] [expr {$depth+1}]]
  } else {
   lappend branches [list [$inst getName] [[$pin getMTerm] getName] $master [$net getName]]
  }
 }
}
if {![llength $branches] || [llength $branches]>128} {error "Unbounded or absent reset branches"}
set f [open reset-buffer-cone.tsv w]
foreach row $buffers {puts $f [join $row "\t"]};close $f
set f [open reset-branches.tsv w];set index 0
foreach row $branches {
 lassign $row inst term master net
 set pin [get_pins [list ${inst}/$term]]
 if {[llength $pin]!=1} {error "Actual reset branch STA pin missing"}
 puts $f [join [linsert $row 0 $index] "\t"]
 foreach kind {min max} {
  report_checks -from [get_ports reset] -through $pin -path_delay $kind -group_path_count 8 -format full_clock_expanded -fields {slew cap fanout input net} -digits 9 > branch-$index-$kind.rpt
 }
 incr index
}
close $f
report_checks -from [get_ports reset] -path_delay min -group_path_count 128 -format full_clock_expanded -fields {slew cap fanout input net} -digits 9 > reset-min.rpt
report_check_types -max_capacitance -max_slew -violators -digits 9 > electrical.rpt
report_worst_slack -max
report_worst_slack -min
'''
        path=a.out/'inspect-reset-branches.tcl';path.write_text(script)
        with(a.out/'inspect-reset-branches.log').open('w')as stream:
            result=subprocess.run(['openroad','-no_init','-exit',path],cwd=a.out,stdout=stream,stderr=subprocess.STDOUT)
        receipt['returncode']=result.returncode;assert result.returncode==0
        assert all(sha(p)==digest for p,digest in inputs.items()),'Read-only S diagnostic input changed'
        rows=[]
        for line in(a.out/'reset-branches.tsv').read_text().splitlines():
            index,inst,pin,master,net=line.split('\t')
            minimum=slacks(a.out/('branch-'+index+'-min.rpt'));maximum=slacks(a.out/('branch-'+index+'-max.rpt'))
            assert bool(minimum)==bool(maximum),'Incomplete branch min/max paths'
            rows.append(dict(index=int(index),instance=inst,pin=pin,master=master,net=net,
                has_timed_reset_path=bool(minimum),minimum_hold_ns=min(minimum)if minimum else None,
                minimum_setup_ns=min(maximum)if maximum else None))
        assert rows and any(r['has_timed_reset_path']for r in rows)
        proof=dict(passed=True,diagnostic_only=True,rc_model='placement-estimate-on-completed-post-GRT-ODB',
            source_actual_global_route_report=str(report),source_actual_global_route_report_sha256=inputs[str(report)],
            no_database_or_constraint_mutation=True,branches=rows,
            scope='Measure reset-only input branches before selecting a physical data-delay ECO. No delay cells inserted; all final and global-route RC gates remain mandatory.')
        (a.out/'reset-branch-measurements.json').write_text(json.dumps(proof,indent=2)+'\n')
        receipt['passed']=True
    finally:
        receipt['outputs']={p.name:sha(p)for p in a.out.iterdir()if p.is_file()}
        (a.out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
