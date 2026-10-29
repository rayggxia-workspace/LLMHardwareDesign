"""Upgrade a real complete parent fixture to its current actual child view.

Reuse its closed routed wires/PG and all 2172 endpoints. Only the macro view is
swapped to the source-bound new actual OBS; no original occupied OBS is cut.
This tests the new source, never inherits the old fixture's DRC result.
"""
from pathlib import Path
from collections import Counter
import csv,datetime,json,os,re,sys,traceback
from run_exports import ROOT,sha
from run_parent_trial import tcl,alias_view
from run_escape_fixture import execute
from check_access import check
from lef_view_contract import parse
from compare_native_route_representations import routing_box_hashes

DRIVER=Path(__file__).resolve().parent


def run(revision,profile='same_pins'):
    assert profile in ['same_pins','actual_tip'];tip=profile=='actual_tip'
    source=ROOT/'escape_landing/r02/mxu-C';rp=source/'execution.json';prior=json.loads(rp.read_text())
    assert prior.get('completed_utc') and prior['native_route_returncode']==0 and prior['fresh_DRC_count']==1
    assert prior['whole_signal_geometry']['pass'] and prior['all_PG_geometry_byteexact_unchanged'] and prior['both_power_grids_pass']
    odb=source/'routed.odb';assert sha(odb)==prior['files'][odb.name]['sha256']
    view=ROOT/('mxu_actual_tip_views/r01/mxu-C' if tip else 'pin_escape_views/r01/mxu-C');vp=view/'execution.json';v=json.loads(vp.read_text())
    assert v.get('completed_utc') and v['native_export_returncode']==v['fresh_model_read_returncode']==0
    assert v['matching_all_signal_model_pins']==2172 and v['all_original_signal_and_PG_pins_and_size_exactly_preserved']
    assert v['SPEF_replay_matches_source'] and v['all_sources_and_pre_RCX_geometry_unchanged']
    for name in ['abstract.lef','detailed.lef','timing.lib','pins.tsv','clean.odb']:assert sha(view/name)==v['files'][name]['sha256']
    assert sha(view/'clean.odb')==v['source_geometry_sha256']
    oldview=ROOT/'eco_views/r02/mxu-C/abstract.lef'
    if tip:
        a,b=parse(oldview),parse(view/'abstract.lef');assert a[0]==b[0] and set(a[1])==set(b[1])
        assert [p.replace('\\','') for p in a[1] if a[1][p]!=b[1][p]]==['act_data[12]']
        assert v['all_2172_current_pins_and_PG_match_actual_after_edit'] and v['source_native_DRC']==0
        guide=source/'route.guide';assert sha(guide)==prior['files'][guide.name]['sha256']
        source_geometry=source/'whole_access.tsv.gz';assert sha(source_geometry)==prior['files'][source_geometry.name]['sha256']
    else:assert parse(oldview)[:2]==parse(view/'abstract.lef')[:2]
    out=ROOT/('mxu_actual_tip_parent' if tip else 'escape_view_recheck')/revision/'mxu-C';out.mkdir(parents=True,exist_ok=False)
    inputs={str(p):sha(p) for p in [rp,odb,vp,oldview,view/'abstract.lef',view/'detailed.lef',view/'timing.lib',view/'pins.tsv',view/'clean.odb']}
    probe=ROOT/'clock_view_binding_probe/r01';proof=json.loads((probe/'execution.json').read_text())
    assert proof['native_probe_returncode']==0 and proof['all_closed_sources_unchanged']
    assert proof['actual_native_stage_rows'][1:3]==['after_LEF\tSIGNAL\tNULL\tNULL','after_Liberty\tCLOCK\tNULL\tNULL']
    if not tip:assert proof['source_SHA'][str(view/'timing.lib')]==sha(view/'timing.lib')
    for p in [probe/'execution.json',probe/'native_clock_types.tsv']:
        if p.name!='execution.json':assert sha(p)==proof['files'][p.name]['sha256']
        inputs[str(p)]=sha(p)
    if tip:inputs.update({str(p):sha(p) for p in [guide,source_geometry]})
    rec={'scope':'ALL2172_REAL_PARENT_ACCESS_RECHECK_NEW_ACTUAL_CHILD_OBS_NOT_OLD_FIXTURE_OR_COMMON_BASE_QUALIFICATION','profile':profile,
      'source_SHA':inputs,'old_parent_native_DRC_count':1,'actual_new_leaf_ODB_SHA256':v['source_geometry_sha256'],
      'new_source_research_model_SHA256':sha(view/'timing.lib'),'all_original_leaf_signal_pins':2172,
      'old_parent_routes_and_PG_reused_not_assumed_valid':True,'global_or_detailed_router_engine_reexecuted':tip,
      'parent_RC_STA':'NOT_EXECUTED_ACCESS_RECHECK_ONLY','full_qualification':False,'native_returncodes':{},
      'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip(),'scheduler_job':os.environ['SLURM_JOB_ID'],
      'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    rec['clock_binding_fix']='Read source-bound aliased Liberty after native swap, then write the physical ODB and independently read back all macro interfaces. No manual USE edit or clock constraint change. Prior r02 pre-swap model loading crashed; r03 saved ODB before model binding and lacks persisted-type proof; both histories retained.'
    def save():(out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n')
    save()
    common=['singularity','exec','--cleanenv','--bind',str(ROOT/'tmp')+':/tmp','--home',str(ROOT/'home'),'--pwd',str(out)]
    try:
        with (view/'detailed.lef').open() as f:
            masters=[line.split()[1] for line in f if line.startswith('MACRO ')]
        assert len(masters)==1;alias='p126_mxu_actual_tip_r01' if tip else 'p126_mxu_M6_escape_r01';alias_view(view/'detailed.lef',out/'actual_child.lef',masters[0],alias)
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
          'set f [open '+tcl(out/'original_macro_pose.tsv')+' w];puts $f [join [concat $old_xy [list $old_ori]] "\t"];close $f',
          'read_lef '+tcl(out/'actual_child.lef'),
          'if {![stage upgrade_to_actual_source_view {set replacement [[ord::get_db] findMaster '+tcl(alias)+'];if {$replacement eq "NULL"} {error "New actual child master missing"};if {![$inst swapMaster $replacement]} {error "Native macro view swap rejected"};if {[$inst getLocation] ne $old_xy || [$inst getOrient] ne $old_ori} {error "Original macro pose changed"}}]} {close $stages;exit 1}',
          'if {![stage bind_current_source_timing_model {read_liberty '+tcl(out/'actual_child_timing.lib')+'}]} {close $stages;exit 1}',
          'write_db '+tcl(out/'upgraded_parent_NOT_SYSTEM.odb'),
          'fingerprint '+tcl(out/'after'),'parent_terms '+tcl(out/'after.child_terms.tsv'),
          'stage VDD {check_power_grid -net VDD -error_file '+tcl(out/'VDD.rpt')+'}',
          'stage VSS {check_power_grid -net VSS -error_file '+tcl(out/'VSS.rpt')+'}',
          'stage all_parent_signal_geometry {source '+tcl(DRIVER/'export_access.tcl')+'}','close $stages']
        if tip:
            index=lines.index('write_db '+tcl(out/'upgraded_parent_NOT_SYSTEM.odb'))
            reroute=['set_routing_layers -signal metal2-metal10 -clock metal4-metal10','read_guides '+tcl(guide),
              'if {![stage begin_incremental {global_route -start_incremental}]} {close $stages;exit 1}',
              'if {![stage rip_changed_parent_signal_only {set it [$inst findITerm {act_data[12]}];if {$it eq "NULL"} {error "Actual target interface missing"};set n [$it getNet];if {[llength [$n getITerms]]!=1 || [llength [$n getBTerms]]!=1} {error "Original peer cardinality changed"};set bt [lindex [$n getBTerms] 0];if {[$bt getName] ne "act_data\\[12\\]"} {error "Original parent bit changed"};foreach bp [$bt getBPins] {foreach r [$bp getBoxes] {if {[[$r getTechLayer] getName] ne "metal10"} {error "Original controlled target layer changed"}}};set wire [$n getWire];if {$wire eq "NULL"} {error "Original parent wire missing"};odb::dbWire_destroy $wire;set_nets_to_route [list [$n getName]]}]} {close $stages;exit 1}',
              'if {![stage incremental_global_route {global_route -end_incremental -guide_file '+tcl(out/'route.guide')+' -congestion_report_file '+tcl(out/'congestion.rpt')+'}]} {catch {write_db '+tcl(out/'failed_global.odb')+'};close $stages;exit 1}',
              'if {![stage actual_tip_parent_detailed_route {detailed_route -output_drc '+tcl(out/'route.drc')+' -verbose 1}]} {close $stages;exit 1}',
              'stage report_parent_signal_wire_lengths {report_wire_length -detailed_route -summary -file '+tcl(out/'parent_wire_length.csv')+'}']
            lines[index:index]=reroute
            rec['only_requested_parent_reroute']='act_data[12]; actual router may change more material, never assumed otherwise'
            rec['unchanged_controlled_parent_target_layer']='metal10; original historical handoff remains partial/unknown'
        script=out/'upgrade.tcl';script.write_text('\n'.join(lines)+'\n')
        rec['native_returncodes']['actual_view_swap_and_access_export']=execute(common,script,out/'native.log','PINXY_OUTPUT='+str(out)+',PINXY_ACCESS_ALL=1,PINXY_ACCESS_OUT='+str(out/'whole_access.tsv.gz'),threads=4);save()
        if (out/'upgraded_parent_NOT_SYSTEM.odb').exists():
            script=out/'fresh.tcl';script.write_text('read_db '+tcl(out/'upgraded_parent_NOT_SYSTEM.odb')+'\n'+code+'\nparent_terms '+tcl(out/'persisted.child_terms.tsv')+'\nset_routing_layers -signal metal2-metal10 -clock metal4-metal10\ndrt::check_drc -output_file '+tcl(out/'independent.drc')+'\n')
            rec['native_returncodes']['fresh_DRC']=execute(common,script,out/'independent.log',threads=1)
            if rec['native_returncodes']['fresh_DRC']==0:rec['fresh_DRC_count']=len(re.findall(r'^violation type:',(out/'independent.drc').read_text(),re.M))
        rec['all_original_parent_BTerm_PG_die_geometry_unchanged']={k:(out/('after.'+k+'.tsv')).exists() and sha(out/('before.'+k+'.tsv'))==sha(out/('after.'+k+'.tsv')) for k in ['pins','pdn','die']}
        if (out/'after.child_terms.tsv').exists():
            def terms(p):
                with p.open() as f:return sorted(tuple(r.items()) for r in csv.DictReader(f,delimiter='\t'))
            rec['all_original_macro_pin_rectangles_net_directions_layers_in_parent_exactly_unchanged']=terms(out/'before.child_terms.tsv')==terms(out/'after.child_terms.tsv')
            if (out/'persisted.child_terms.tsv').exists():rec['all_original_macro_pin_contracts_persisted_and_independently_read_back']=terms(out/'before.child_terms.tsv')==terms(out/'after.child_terms.tsv')==terms(out/'persisted.child_terms.tsv')
            if tip:
                def load(p):
                    with p.open() as f:return list(csv.DictReader(f,delimiter='\t'))
                before,after=load(out/'before.child_terms.tsv'),load(out/'after.child_terms.tsv')
                target='act_data[12]';rest=lambda data:Counter(tuple(sorted(r.items())) for r in data if r['pin'].replace('\\','')!=target)
                assert len(before)==len(after)==2245 and rest(before)==rest(after)
                x=[r for r in before if r['pin'].replace('\\','')==target];y=[r for r in after if r['pin'].replace('\\','')==target]
                assert len(x)==len(y)==1
                assert all(x[0][k]==y[0][k] for k in ['pin','direction','use','net','layer']) and y[0]['layer']=='metal6'
                pose=(out/'original_macro_pose.tsv').read_text().split();assert pose[2]=='R0';dx,dy=map(int,pose[:2])
                with (view/'pins.tsv').open() as f:vpins=[r for r in csv.DictReader(f,delimiter='\t') if r['pin'].replace('\\','')==target]
                assert len(vpins)==1
                expected=[int(vpins[0][k])+d for k,d in zip(['x0','y0','x1','y1'],[dx,dy,dx,dy])]
                assert [int(y[0][k]) for k in ['x0','y0','x1','y1']]==expected
                assert all(int(r['x1'])-int(r['x0'])==int(r['y1'])-int(r['y0'])==280 for r in [x[0],y[0]])
                rec['all_macro_functions_layers_sizes_directions_networks_and_clock_USE_preserved_with_exactly_one_authorized_XY_change']=True
                rec['only_changed_macro_XY_pin']=target
                if (out/'persisted.child_terms.tsv').exists():rec['new_macro_contract_persisted_and_independently_read_back']=terms(out/'after.child_terms.tsv')==terms(out/'persisted.child_terms.tsv')
        if (out/'whole_access.tsv.gz').exists():rec['whole_parent_signal_geometry']=check(out/'whole_access.tsv.gz',True)
        if tip and rec.get('whole_parent_signal_geometry',{}).get('pass'):
            a,_=routing_box_hashes(source_geometry,2172);b,_=routing_box_hashes(out/'whole_access.tsv.gz',2172)
            assert set(a)==set(b)
            rec['actual_changed_parent_signal_wire_box_native_net_names']=sorted(n for n in a if a[n]!=b[n])
        if (out/'stages.tsv').exists():
            with (out/'stages.tsv').open() as f:rec['native_stage_status']={r['stage']:r['status'] for r in csv.DictReader(f,delimiter='\t')}
    except Exception:rec['actual_failure']=traceback.format_exc()
    rec['all_closed_sources_unchanged']=all(sha(Path(p))==v for p,v in inputs.items())
    rec['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    rec['files']={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in out.iterdir() if p.is_file() and p.name!='execution.json'};save()
    contract=(rec.get('all_macro_functions_layers_sizes_directions_networks_and_clock_USE_preserved_with_exactly_one_authorized_XY_change') and rec.get('new_macro_contract_persisted_and_independently_read_back')) if tip else (rec.get('all_original_macro_pin_rectangles_net_directions_layers_in_parent_exactly_unchanged') and rec.get('all_original_macro_pin_contracts_persisted_and_independently_read_back'))
    return 0 if 'actual_failure' not in rec and rec.get('fresh_DRC_count')==0 and rec.get('whole_parent_signal_geometry',{}).get('pass') and all(rec.get('all_original_parent_BTerm_PG_die_geometry_unchanged',{}).values()) and contract and rec['all_closed_sources_unchanged'] and all(rec.get('native_stage_status',{}).get(k)=='EXECUTED' for k in ['VDD','VSS']) else 1


if __name__=='__main__':sys.exit(run(*sys.argv[1:3]))
