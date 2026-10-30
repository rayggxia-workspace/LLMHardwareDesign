"""Route around the proven NEW parent PG stripe; preserve all PG and leaf views.

The previous via-only repair deliberately refused to change a stripe. This
alternative adds one temporary, conservative M10 signal keepout around that
actual stripe, reroutes the fixture, removes only that new constraint, and checks
the real result independently. No physical rule or existing OBS is removed.
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
    old=json.loads((source/'execution.json').read_text())
    assert old['native_route_returncode']==0 and old['independent_DRC_count']==1 and old['whole_signal_geometry']['pass']
    marker=(source/'independent.drc').read_text()
    assert marker.count('violation type:')==1 and 'net:r_data[195] net:VDD' in marker and 'on Layer metal10' in marker
    out=ROOT/'escape_spacing_reroute'/revision/'act-C';out.mkdir(parents=True,exist_ok=False)
    guard_um=float(os.environ.get('PINXY_M10_STRIPE_GUARD_UM','.8'))
    assert guard_um in [.8,1.6,2.4], 'Explicit finite M10-only routing-constraint experiment'
    inputs={str(source/p):sha(source/p) for p in ['execution.json','routed.odb','independent.drc','landing_ports.csv','route.tcl']}
    commands=(source/'route.tcl').read_text().replace(str(source),str(out))
    commands=commands.replace('read_db '+tcl(out/'placed.odb'),'read_db '+tcl(source/'routed.odb'))
    start='''
set b [ord::get_db_block];set u [$b getDbUnitsPerMicron];set original_obs [lsort [$b getObstructions]]
proc pg_snapshot {file} {
 set f [open $file w]
 foreach n [[ord::get_db_block] getNets] {foreach sw [$n getSWires] {foreach s [$sw getWires] {
  if {[$s isVia]} {set v [$s getTechVia];if {$v eq "NULL"} {set v [$s getBlockVia]};set l [$v getName]} else {set l [[$s getTechLayer] getName]}
  puts $f [list [$n getName] $l [$s isVia] [$s xMin] [$s yMin] [$s xMax] [$s yMax]]
 }}}
 close $f
}
pg_snapshot '''+tcl(out/'before.pdn.tsv')+'''
set stripes {};foreach sw [[$b findNet VDD] getSWires] {foreach s [$sw getWires] {
 if {[$s isVia] || [[$s getTechLayer] getName] ne "metal10"} {continue}
 if {[$s xMin] < 147.17*$u && [$s xMax]>144.95*$u && [$s yMin]<367.67*$u && [$s yMax]>365.27*$u} {lappend stripes $s}
}}
if {[llength $stripes]!=1} {error "Expected exactly the proven parent PG stripe"}
set stripe [lindex $stripes 0];set guard [expr {round('''+str(guard_um)+'''*$u)}]
set temporary [odb::dbObstruction_create $b [[ord::get_db_tech] findLayer metal10] [expr {[$stripe xMin]-$guard}] [$stripe yMin] [expr {[$stripe xMax]+$guard}] [$stripe yMax]]
puts "NEW_TEMPORARY_SIGNAL_KEEPOUT_AROUND_ACTUAL_PARENT_M10_STRIPE"
foreach n [$b getNets] {if {[$n getSigType] ni {POWER GROUND}} {set w [$n getWire];if {$w ne "NULL"} {odb::dbWire_destroy $w}}}
'''
    pos=commands.index('global_route ');commands=commands[:pos]+start+commands[pos:]
    remove='''odb::dbObstruction_destroy $temporary
if {[lsort [[ord::get_db_block] getObstructions]] ne $original_obs} {error "Original OBS changed"}
pg_snapshot '''+tcl(out/'after.pdn.tsv')+'\n'
    commands=commands.replace('write_db '+tcl(out/'routed.odb'),remove+'write_db '+tcl(out/'routed.odb'))
    (out/'route.tcl').write_text(commands)
    common=['singularity','exec','--cleanenv','--bind',str(ROOT/'tmp')+':/tmp','--home',str(ROOT/'home'),'--pwd',str(out)]
    rc=execute(common,out/'route.tcl',out/'route.log','PINXY_ACCESS_ALL=1,PINXY_ACCESS_OUT='+str(out/'whole_access.tsv.gz'))
    rec={'scope':'REAL_PARENT_FIXTURE_REROUTE_NOT_COMMON_BASE_OR_SYSTEM_QUALIFICATION','source':str(source),'source_inputs_SHA':inputs,
         'native_route_returncode':rc,'temporary_keepout_guard_um':guard_um,'guard_basis':'M10 minimum spacing .8um and PRL maximum1.5um; finite conservative signal keepout sensitivity. No pin/via rule change.',
         'all_leaf_pins_layers_shapes_and_all_PG_preserved':True,'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip(),
         'scheduler_job':os.environ['SLURM_JOB_ID'],'full_qualification':False,'GRT_overflow_retained_not_a_pass':True}
    if rc==0:
        fresh=out/'fresh.tcl';fresh.write_text('read_db '+tcl(out/'routed.odb')+'\nset_routing_layers -signal metal2-metal10 -clock metal4-metal10\ndrt::check_drc -output_file '+tcl(out/'independent.drc')+'\n')
        rec['fresh_DRC_returncode']=execute(common,fresh,out/'independent.log',threads=1)
        p=out/'independent.drc';rec['fresh_DRC_count']=len(re.findall(r'^violation type:',p.read_text(),re.M)) if rec['fresh_DRC_returncode']==0 and p.exists() else None
        rec['whole_signal_geometry']=check(out/'whole_access.tsv.gz',True)
        rec['all_PG_geometry_byteexact_unchanged']=sha(out/'before.pdn.tsv')==sha(out/'after.pdn.tsv')
        log=(out/'route.log').read_text();rec['both_power_grids_pass']=all('All shapes on net '+s+' are connected.' in log for s in ['VDD','VSS'])
    rec['source_unchanged']=all(sha(Path(p))==h for p,h in inputs.items())
    passed=rc==0 and rec.get('fresh_DRC_count')==0 and rec.get('whole_signal_geometry',{}).get('pass') and rec.get('both_power_grids_pass') and rec.get('all_PG_geometry_byteexact_unchanged') and rec['source_unchanged']
    rec['status']='PARENT_ESCAPE_GEOMETRY_GATES_PASSED_NOT_FULL_SYSTEM_QUALIFIED' if passed else 'ACTUAL_ESCAPE_REROUTE_FAILED_OR_INCOMPLETE'
    rec['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    rec['files']={p.name:{'sha256':sha(p),'bytes':p.stat().st_size} for p in out.iterdir() if p.is_file()}
    (out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n');print(rec['status'],flush=True)
    return 0 if passed else 1


if __name__=='__main__':sys.exit(run(*sys.argv[1:3]))
