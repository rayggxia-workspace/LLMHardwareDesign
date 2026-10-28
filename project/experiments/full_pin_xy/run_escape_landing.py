"""Actual one-parent-landing move/reroute, with original leaf and PG unchanged."""
from pathlib import Path
import csv,datetime,gzip,hashlib,json,os,re,sys
from run_exports import ROOT,sha
from run_parent_trial import tcl
from run_escape_fixture import execute
from check_access import check

DRIVER=Path(__file__).resolve().parent


def run(input_set,revision):
    inputs=ROOT/'inputs'/input_set;delta=json.loads((inputs/'landing_delta.json').read_text())
    source=Path(delta.get('source_fixture',str(ROOT/'escape_fixtures/r04/act-C'))).resolve()
    assert (ROOT/'escape_fixtures').resolve() in source.parents
    case=delta.get('case','act');assert case in ['act','gemm','mxu']
    expected=delta.get('expected_source_native_DRC_count',1)
    assert expected==1 or (case=='mxu' and expected==2)
    old=json.loads((source/'execution.json').read_text());assert old['native_route_returncode']==0 and old['independent_DRC_count']==expected
    for name,digest in delta['source_files_uncompressed_SHA'].items():
        p=source/(name if name=='whole_access.tsv.gz' else name[:-3]);content=gzip.decompress(p.read_bytes()) if p.suffix=='.gz' else p.read_bytes()
        assert hashlib.sha256(content).hexdigest()==digest,(name,'Actual input geometry differs')
    out=ROOT/'escape_landing'/revision/(case+'-C');out.mkdir(parents=True,exist_ok=False)
    source_sha=sha(source/'routed.odb');commands=(source/'route.tcl').read_text().replace(str(source),str(out))
    commands=commands.replace('read_db '+tcl(out/'placed.odb'),'read_db '+tcl(source/'routed.odb'))
    commands='\n'.join(s for s in commands.splitlines() if not s.startswith('place_pin '))+'\n'
    assert 'placed.odb' not in commands
    snapshots='''
proc snapshot_parent {prefix} {
 set b [ord::get_db_block];set f [open $prefix.pins.tsv w];puts $f "pin\\tdirection\\tuse\\tnet\\tlayer\\tx0\\ty0\\tx1\\ty1"
 foreach t [$b getBTerms] {foreach p [$t getBPins] {foreach s [$p getBoxes] {
  puts $f [join [list [$t getName] [$t getIoType] [$t getSigType] [[$t getNet] getName] [[$s getTechLayer] getName] [$s xMin] [$s yMin] [$s xMax] [$s yMax]] "\\t"]
 }}};close $f
 set f [open $prefix.pdn.tsv w]
 foreach n [$b getNets] {foreach sw [$n getSWires] {foreach s [$sw getWires] {
  if {[$s isVia]} {set v [$s getTechVia];if {$v eq "NULL"} {set v [$s getBlockVia]};set layer [$v getName]} else {set layer [[$s getTechLayer] getName]}
  puts $f [list [$n getName] $layer [$s isVia] [$s xMin] [$s yMin] [$s xMax] [$s yMax]]
 }}};close $f
}
snapshot_parent '''+tcl(out/'before')+'\n'
    x,y=delta['new_parent_xy_um'];net=delta['net']
    change=snapshots+'place_pin -pin_name '+tcl(net)+' -layer metal10 -location {'+str(x)+' '+str(y)+'} -pin_size {.8 .8}\n'
    change+='set net [[ord::get_db_block] findNet '+tcl(net)+'];set wire [$net getWire];if {$wire eq "NULL"} {error "Expected original offending signal route"};odb::dbWire_destroy $wire\n'
    pos=commands.index('global_route ');commands=commands[:pos]+change+commands[pos:]
    commands=commands.replace('write_db '+tcl(out/'routed.odb'),'snapshot_parent '+tcl(out/'after')+'\nwrite_db '+tcl(out/'routed.odb'))
    (out/'route.tcl').write_text(commands)
    common=['singularity','exec','--cleanenv','--bind',str(ROOT/'tmp')+':/tmp','--home',str(ROOT/'home'),'--pwd',str(out)]
    rc=execute(common,out/'route.tcl',out/'route.log','PINXY_ACCESS_ALL=1,PINXY_ACCESS_OUT='+str(out/'whole_access.tsv.gz'))
    rec={'scope':'NEW_PARENT_M10_LANDING_XY_REPAIR_NOT_LEAF_PIN_CHANGE_OR_COMMON_BASE','input_delta':delta,'delta_SHA':sha(inputs/'landing_delta.json'),
         'source_fixture':str(source),'case':case,'source_leaf_ODB_SHA':old.get('source_clean_ODB_SHA'),
         'native_route_returncode':rc,'source_routed_ODB_SHA':source_sha,'source_unchanged':source_sha==sha(source/'routed.odb'),
         'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip(),'scheduler_job':os.environ['SLURM_JOB_ID'],'full_qualification':False}
    if rc==0:
        def pins(p):
            with p.open() as f:return {r['pin']:r for r in csv.DictReader(f,delimiter='\t')}
        a,b=pins(out/'before.pins.tsv'),pins(out/'after.pins.tsv');assert set(a)==set(b)
        changes=[p for p in a if a[p]!=b[p]];assert changes==[net],changes
        for k in ['direction','use','net','layer']:assert a[net][k]==b[net][k]
        assert all(abs(int(b[net][k])/2000-v)<1e-6 for k,v in zip(['x0','y0','x1','y1'],[x-.4,y-.4,x+.4,y+.4]))
        rec['exactly_one_parent_M10_pin_XY_changed_all_other_rectangles_unchanged']=True
        rec['all_PG_geometry_byteexact_unchanged']=sha(out/'before.pdn.tsv')==sha(out/'after.pdn.tsv')
        fresh=out/'fresh.tcl';fresh.write_text('read_db '+tcl(out/'routed.odb')+'\nset_routing_layers -signal metal2-metal10 -clock metal4-metal10\ndrt::check_drc -output_file '+tcl(out/'independent.drc')+'\n')
        rec['fresh_DRC_returncode']=execute(common,fresh,out/'independent.log',threads=1)
        p=out/'independent.drc';rec['fresh_DRC_count']=len(re.findall(r'^violation type:',p.read_text(),re.M)) if rec['fresh_DRC_returncode']==0 and p.exists() else None
        rec['whole_signal_geometry']=check(out/'whole_access.tsv.gz',True)
        log=(out/'route.log').read_text();rec['both_power_grids_pass']=all('All shapes on net '+s+' are connected.' in log for s in ['VDD','VSS'])
    passed=rc==0 and rec.get('fresh_DRC_count')==0 and rec.get('whole_signal_geometry',{}).get('pass') and rec.get('all_PG_geometry_byteexact_unchanged') and rec.get('both_power_grids_pass') and rec['source_unchanged']
    rec['status']='PARENT_LANDING_GEOMETRY_GATES_PASSED_NOT_SYSTEM_QUALIFICATION' if passed else 'ACTUAL_PARENT_LANDING_REPAIR_FAILED_OR_INCOMPLETE'
    rec['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();rec['files']={p.name:{'sha256':sha(p),'bytes':p.stat().st_size} for p in out.iterdir() if p.is_file()}
    (out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n');print(rec['status'],flush=True)
    return 0 if passed else 1


if __name__=='__main__':sys.exit(run(*sys.argv[1:3]))
