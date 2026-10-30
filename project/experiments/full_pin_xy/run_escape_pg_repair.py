"""Bounded repair of NEW parent PG vias, retaining the actual leaf and signal route.

Only the original fixture's single proven M10 signal/PG spacing marker is
eligible. Remove complete redundant parent PG via-site groups near that marker;
never touch master geometry, PG stripes, original leaf PDN or signal wiring.
Fresh native DRC, whole signal geometry and both power grids remain hard gates.
"""
from pathlib import Path
import datetime, json, os, re, sys
from run_exports import ROOT, sha
from run_parent_trial import tcl
from run_escape_fixture import execute
from check_access import check

DRIVER=Path(__file__).resolve().parent


def run(source_revision, revision):
    source=ROOT/'escape_fixtures'/source_revision/'act-C'
    previous=json.loads((source/'execution.json').read_text())
    assert previous['native_route_returncode']==0 and previous['independent_DRC_count']==1
    assert previous['whole_signal_geometry']['pass']
    drc=(source/'independent.drc').read_text()
    assert drc.count('violation type:')==1 and 'Metal Spacing' in drc and 'net:VDD' in drc and 'net:r_data[195]' in drc
    hit=re.search(r'bbox = \(([\d.]+), ([\d.]+)\) - \(([\d.]+), ([\d.]+)\) on Layer metal10',drc)
    assert hit,'Exact expected M10 marker required'
    bounds=list(map(float,hit.groups()))
    out=ROOT/'escape_pg_repair'/revision/'act-C';out.mkdir(parents=True,exist_ok=False)
    inputs={str(source/p):sha(source/p) for p in ['execution.json','routed.odb','independent.drc','whole_access.tsv.gz','landing_ports.csv']}
    common=['singularity','exec','--cleanenv','--bind',str(ROOT/'tmp')+':/tmp','--home',str(ROOT/'home'),'--pwd',str(out)]
    script=out/'repair.tcl'
    script.write_text('read_db '+tcl(source/'routed.odb')+'\n'+'''
set block [ord::get_db_block]; set u [$block getDbUnitsPerMicron]
# Snapshot objects that this limited repair has no authority to change.
set instance_signature {};foreach i [$block getInsts] {lappend instance_signature [list [$i getName] [[$i getMaster] getName] [$i getOrient] [$i getLocation]]}
set stripe_signature {};set groups [dict create];set rows [dict create]
foreach supply {VDD VSS} {
 foreach sw [[$block findNet $supply] getSWires] {foreach b [$sw getWires] {
  if {![$b isVia]} {lappend stripe_signature [list $supply [[$b getTechLayer] getName] [$b xMin] [$b yMin] [$b xMax] [$b yMax]];continue}
  lassign [$b getViaXY] x y;set key [list $supply $x $y];dict lappend groups $key $b
  set via [$b getTechVia];if {$via eq "NULL"} {set via [$b getBlockVia]};if {$via eq "NULL"} {error "Unresolved via"}
  foreach s [$via getBoxes] {if {[[$s getTechLayer] getName] eq "metal10"} {dict lappend rows $key [list [$via getName] [expr {[$s xMin]+$x}] [expr {[$s yMin]+$y}] [expr {[$s xMax]+$x}] [expr {[$s yMax]+$y}]]}}
 }}
}
set marker {}
foreach v {'''+ ' '.join(map(str,bounds))+'''} {lappend marker [expr {round($v*$u)}]}
lassign $marker x0 y0 x1 y1
set eligible {}
dict for {key landings} $rows {
 if {[lindex $key 0] ne "VDD"} {continue}
 foreach q $landings {
  lassign $q name a b c d
  if {$a<$x1+$u && $c>$x0-$u && $b<$y1+$u && $d>$y0-$u} {lappend eligible $key;break}
 }
}
if {[llength $eligible]<1 || [llength $eligible]>2} {error "Repair not bounded to 1-2 new parent PG sites: $eligible"}
set f [open '''+tcl(out/'removed_parent_pg_sites.tsv')+''' w]
puts $f "net\\tx_dbu\\ty_dbu\\tvia_name\\tx0\\ty0\\tx1\\ty1"
foreach key $eligible {
 foreach row [dict get $rows $key] {puts $f "[join $key \\t]\\t[join $row \\t]"}
 foreach box [dict get $groups $key] {odb::dbSBox_destroy $box}
}
close $f
set after {};foreach i [$block getInsts] {lappend after [list [$i getName] [[$i getMaster] getName] [$i getOrient] [$i getLocation]]}
if {$after ne $instance_signature} {error "Instance/master pose changed"}
set after {};foreach supply {VDD VSS} {foreach sw [[$block findNet $supply] getSWires] {foreach b [$sw getWires] {
 if {![$b isVia]} {lappend after [list $supply [[$b getTechLayer] getName] [$b xMin] [$b yMin] [$b xMax] [$b yMax]]}
}}}
if {$after ne $stripe_signature} {error "Parent PG stripe changed"}
puts "ORIGINAL_MASTER_INSTANCE_POSE_AND_ALL_NONVIA_PG_STRIPES_UNCHANGED"
write_db '''+tcl(out/'repaired.odb')+'\ncheck_power_grid -net VDD -error_file '+tcl(out/'VDD.rpt')+'\ncheck_power_grid -net VSS -error_file '+tcl(out/'VSS.rpt')+'\nsource '+tcl(DRIVER/'export_access.tcl')+'\n')
    rc=execute(common,script,out/'repair.log','PINXY_ACCESS_ALL=1,PINXY_ACCESS_OUT='+str(out/'whole_access.tsv.gz'),threads=1)
    record={'scope':'NEW_PARENT_PG_SITE_REPAIR_ONLY_NOT_COMMON_BASE_OR_FULL_QUALIFICATION','source':str(source),'source_inputs_SHA':inputs,
            'original_single_marker_um':bounds,'native_repair_returncode':rc,'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip(),
            'scheduler_job':os.environ['SLURM_JOB_ID'],'full_qualification':False}
    if rc==0:
        fresh=out/'fresh.tcl';fresh.write_text('read_db '+tcl(out/'repaired.odb')+'\nset_routing_layers -signal metal2-metal10 -clock metal4-metal10\ndrt::check_drc -output_file '+tcl(out/'independent.drc')+'\n')
        record['fresh_DRC_returncode']=execute(common,fresh,out/'independent.log',threads=1)
        p=out/'independent.drc';record['fresh_DRC_count']=len(re.findall(r'^violation type:',p.read_text(),re.M)) if record['fresh_DRC_returncode']==0 and p.exists() else None
        record['whole_signal_geometry']=check(out/'whole_access.tsv.gz',True)
        record['signal_and_terminal_geometry_byteexact_unchanged']=sha(out/'whole_access.tsv.gz')==inputs[str(source/'whole_access.tsv.gz')]
        log=(out/'repair.log').read_text();record['both_power_grids_pass']=all('All shapes on net '+s+' are connected.' in log for s in ['VDD','VSS'])
    record['source_unchanged']=all(sha(Path(p))==h for p,h in inputs.items())
    passed=rc==0 and record.get('fresh_DRC_count')==0 and record.get('whole_signal_geometry',{}).get('pass') and record.get('signal_and_terminal_geometry_byteexact_unchanged') and record.get('both_power_grids_pass') and record['source_unchanged']
    record['status']='PARENT_ESCAPE_GEOMETRY_GATES_PASSED_NOT_FULL_SYSTEM_QUALIFIED' if passed else 'PARENT_ESCAPE_REPAIR_FAILED_OR_INCOMPLETE'
    record['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    record['files']={p.name:{'sha256':sha(p),'bytes':p.stat().st_size} for p in out.iterdir() if p.is_file()}
    (out/'execution.json').write_text(json.dumps(record,indent=2)+'\n')
    print(record['status'],flush=True)
    return 0 if passed else 1


if __name__=='__main__':sys.exit(run(*sys.argv[1:3]))
