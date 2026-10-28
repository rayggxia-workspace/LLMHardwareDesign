"""Upgrade a real complete parent fixture to its current actual child view.

Reuse its closed routed wires/PG and all 2172 endpoints. Only the macro view is
swapped to the source-bound new actual OBS; no original occupied OBS is cut.
This tests the new source, never inherits the old fixture's DRC result.
"""
from pathlib import Path
import csv,datetime,json,os,re,sys,traceback
from run_exports import ROOT,sha
from run_parent_trial import tcl,alias_view
from run_escape_fixture import execute
from check_access import check
from lef_view_contract import parse

DRIVER=Path(__file__).resolve().parent


def run(revision):
    source=ROOT/'escape_landing/r02/mxu-C';rp=source/'execution.json';prior=json.loads(rp.read_text())
    assert prior.get('completed_utc') and prior['native_route_returncode']==0 and prior['fresh_DRC_count']==1
    assert prior['whole_signal_geometry']['pass'] and prior['all_PG_geometry_byteexact_unchanged'] and prior['both_power_grids_pass']
    odb=source/'routed.odb';assert sha(odb)==prior['files'][odb.name]['sha256']
    view=ROOT/'pin_escape_views/r01/mxu-C';vp=view/'execution.json';v=json.loads(vp.read_text())
    assert v.get('completed_utc') and v['native_export_returncode']==v['fresh_model_read_returncode']==0
    assert v['matching_all_signal_model_pins']==2172 and v['all_original_signal_and_PG_pins_and_size_exactly_preserved']
    assert v['SPEF_replay_matches_source'] and v['all_sources_and_pre_RCX_geometry_unchanged']
    for name in ['abstract.lef','detailed.lef','timing.lib','pins.tsv','clean.odb']:assert sha(view/name)==v['files'][name]['sha256']
    assert sha(view/'clean.odb')==v['source_geometry_sha256']
    oldview=ROOT/'eco_views/r02/mxu-C/abstract.lef';assert parse(oldview)[:2]==parse(view/'abstract.lef')[:2]
    out=ROOT/'escape_view_recheck'/revision/'mxu-C';out.mkdir(parents=True,exist_ok=False)
    inputs={str(p):sha(p) for p in [rp,odb,vp,oldview,view/'abstract.lef',view/'detailed.lef',view/'timing.lib',view/'pins.tsv',view/'clean.odb']}
    rec={'scope':'ALL2172_REAL_PARENT_ACCESS_RECHECK_NEW_ACTUAL_CHILD_OBS_NOT_OLD_FIXTURE_OR_COMMON_BASE_QUALIFICATION',
      'source_SHA':inputs,'old_parent_native_DRC_count':1,'actual_new_leaf_ODB_SHA256':v['source_geometry_sha256'],
      'new_source_research_model_SHA256':sha(view/'timing.lib'),'all_original_leaf_signal_pins':2172,
      'old_parent_routes_and_PG_reused_not_assumed_valid':True,'global_or_detailed_router_engine_reexecuted':False,
      'parent_RC_STA':'NOT_EXECUTED_ACCESS_RECHECK_ONLY','full_qualification':False,'native_returncodes':{},
      'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip(),'scheduler_job':os.environ['SLURM_JOB_ID'],
      'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    def save():(out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n')
    save()
    common=['singularity','exec','--cleanenv','--bind',str(ROOT/'tmp')+':/tmp','--home',str(ROOT/'home'),'--pwd',str(out)]
    try:
        with (view/'detailed.lef').open() as f:
            masters=[line.split()[1] for line in f if line.startswith('MACRO ')]
        assert len(masters)==1;alias='p126_mxu_M6_escape_r01';alias_view(view/'detailed.lef',out/'actual_child.lef',masters[0],alias)
        # Name-only model alias: every number and pin definition stays intact.
        text=(view/'timing.lib').read_text();text,n=re.subn(r'(\bcell\s*\(\s*"?)'+re.escape(masters[0])+r'("?\s*\))',lambda m:m[1]+alias+m[2],text);assert n==1
        (out/'actual_child_timing.lib').write_text(text)
        helper=(DRIVER/'physical_trial.tcl').read_text().split('if {![stage load {',1)[0]
        code='''proc parent_terms {file} {
 set f [open $file w];puts $f "pin\\tdirection\\tuse\\tnet\\tlayer\\tx0\\ty0\\tx1\\ty1"
 set b [ord::get_db_block];set inst [$b findInst u_macro]
 foreach it [$inst getITerms] {
  set n [$it getNet];if {$n eq "NULL"} {set nn NULL} else {set nn [$n getName]}
  foreach g [$it getGeometries] {set layer [lindex $g 0];set r [lindex $g 1];puts $f [join [list [[$it getMTerm] getName] [$it getIoType] [$it getSigType] $nn [$layer getName] [$r xMin] [$r yMin] [$r xMax] [$r yMax]] "\\t"]}
 };close $f
}'''
        lines=[helper,code,'read_db '+tcl(odb),'fingerprint '+tcl(out/'before'),'parent_terms '+tcl(out/'before.child_terms.tsv'),
          'set b [ord::get_db_block];set inst [$b findInst u_macro];set old_xy [$inst getLocation];set old_ori [$inst getOrient]',
          'read_lef '+tcl(out/'actual_child.lef'),
          'if {![stage upgrade_to_actual_source_view {set replacement [[ord::get_db] findMaster '+tcl(alias)+'];if {$replacement eq "NULL"} {error "New actual child master missing"};if {![$inst swapMaster $replacement]} {error "Native macro view swap rejected"};if {[$inst getLocation] ne $old_xy || [$inst getOrient] ne $old_ori} {error "Original macro pose changed"};write_db '+tcl(out/'upgraded_parent_NOT_SYSTEM.odb')+'}]} {close $stages;exit 1}',
          'fingerprint '+tcl(out/'after'),'parent_terms '+tcl(out/'after.child_terms.tsv'),
          'stage VDD {check_power_grid -net VDD -error_file '+tcl(out/'VDD.rpt')+'}',
          'stage VSS {check_power_grid -net VSS -error_file '+tcl(out/'VSS.rpt')+'}',
          'stage all_parent_signal_geometry {source '+tcl(DRIVER/'export_access.tcl')+'}','close $stages']
        script=out/'upgrade.tcl';script.write_text('\n'.join(lines)+'\n')
        rec['native_returncodes']['actual_view_swap_and_access_export']=execute(common,script,out/'native.log','PINXY_OUTPUT='+str(out)+',PINXY_ACCESS_ALL=1,PINXY_ACCESS_OUT='+str(out/'whole_access.tsv.gz'),threads=4);save()
        if (out/'upgraded_parent_NOT_SYSTEM.odb').exists():
            script=out/'fresh.tcl';script.write_text('read_db '+tcl(out/'upgraded_parent_NOT_SYSTEM.odb')+'\nset_routing_layers -signal metal2-metal10 -clock metal4-metal10\ndrt::check_drc -output_file '+tcl(out/'independent.drc')+'\n')
            rec['native_returncodes']['fresh_DRC']=execute(common,script,out/'independent.log',threads=1)
            if rec['native_returncodes']['fresh_DRC']==0:rec['fresh_DRC_count']=len(re.findall(r'^violation type:',(out/'independent.drc').read_text(),re.M))
        rec['all_original_parent_BTerm_PG_die_geometry_unchanged']={k:(out/('after.'+k+'.tsv')).exists() and sha(out/('before.'+k+'.tsv'))==sha(out/('after.'+k+'.tsv')) for k in ['pins','pdn','die']}
        if (out/'after.child_terms.tsv').exists():
            def terms(p):
                with p.open() as f:return sorted(tuple(r.items()) for r in csv.DictReader(f,delimiter='\t'))
            rec['all_original_macro_pin_rectangles_net_directions_layers_in_parent_exactly_unchanged']=terms(out/'before.child_terms.tsv')==terms(out/'after.child_terms.tsv')
        if (out/'whole_access.tsv.gz').exists():rec['whole_parent_signal_geometry']=check(out/'whole_access.tsv.gz',True)
        if (out/'stages.tsv').exists():
            with (out/'stages.tsv').open() as f:rec['native_stage_status']={r['stage']:r['status'] for r in csv.DictReader(f,delimiter='\t')}
    except Exception:rec['actual_failure']=traceback.format_exc()
    rec['all_closed_sources_unchanged']=all(sha(Path(p))==v for p,v in inputs.items())
    rec['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    rec['files']={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in out.iterdir() if p.is_file() and p.name!='execution.json'};save()
    return 0 if 'actual_failure' not in rec and rec.get('fresh_DRC_count')==0 and rec.get('whole_parent_signal_geometry',{}).get('pass') and all(rec.get('all_original_parent_BTerm_PG_die_geometry_unchanged',{}).values()) and rec.get('all_original_macro_pin_rectangles_net_directions_layers_in_parent_exactly_unchanged') and rec['all_closed_sources_unchanged'] and all(rec.get('native_stage_status',{}).get(k)=='EXECUTED' for k in ['VDD','VSS']) else 1


if __name__=='__main__':sys.exit(run(sys.argv[1]))
