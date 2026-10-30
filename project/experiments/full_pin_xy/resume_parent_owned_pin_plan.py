"""Realize the closed all13507 plan after pre-edit Python variable failure.

No repeated geometry search. Bind original source/plan hashes; execute native
pin edits, all-net geometry/unchanged-conductor proof, leaf DRC, parent AP and
fresh RC/STA separately. All remaining original constraints/failures retained.
"""
from pathlib import Path
import csv,datetime,gzip,json,os,re,sys,traceback
from run_exports import ROOT,sha
from run_parent_trial import tcl
from run_escape_fixture import execute
from run_llsys_actual_tips import pin_contract
from compare_native_route_representations import routing_box_hashes
from check_access import check
from probe_ll_parent_after_leaf_edit import probe
DRIVER=Path(__file__).resolve().parent


def run(revision):
    prior=ROOT/'all_llsys_access_stubs/parent-owned-r01';pp=prior/'execution.json';p=json.loads(pp.read_text())
    assert p.get('completed_utc') and p['profile']=='parent_owned_only' and p['all_closed_sources_unchanged']
    assert not p['native_returncodes'] and 'list indices must be integers or slices' in p['actual_failure']
    plan=prior/'all13507_source_bound_access_stub_plan.json';specs=prior/'actual_stub_specs.tcl'
    for f in [plan,specs]:assert sha(f)==p['files'][f.name]['sha256']
    assert all(sha(Path(f))==v for f,v in p['source_SHA'].items())
    source=ROOT/'parent1016_actual_m5_repair/r01';sp=source/'execution.json';s=json.loads(sp.read_text());odb=source/'routed.odb'
    assert s.get('completed_utc') and s['fresh_leaf_DRC_count']==0 and s['all_closed_sources_unchanged'] and s['native_DEF_NETS_byte_identical']
    assert sha(odb)==s['files'][odb.name]['sha256']==p['source_SHA'][str(odb)]
    geometry=ROOT/'llsys_corner_fill/r01';gp=geometry/'execution.json';g=json.loads(gp.read_text());geo=geometry/'whole_access.tsv.gz'
    assert g.get('completed_utc') and g['fresh_DRC_count']==0 and g['all_closed_sources_unchanged']
    assert sha(geo)==g['files'][geo.name]['sha256']==p['source_SHA'][str(geo)]
    trial=ROOT/'trials/llsys-pg-r03/llaccel_aux-C/execution.json';original=json.loads(trial.read_text());sdc=Path(original['source_sdc']);assert sha(sdc)==original['input_sha256'][str(sdc)]
    rows=json.loads(plan.read_text());assert len(rows)==13507 and len({r['pin'] for r in rows})==13507
    chosen=[r for r in rows if r['center_DBU']!=r['target_center_DBU']]
    assert len(chosen)==p['actual_requested_XY_and_stub_count'] and chosen
    assert all(r['access_method']=='OWN_EXISTING_METAL_NO_NEW_WIRE' and not r['stub_path_DBU'] and r['stub_L1_um']==0 for r in chosen)
    out=ROOT/'all_llsys_parent_owned_realization'/revision;out.mkdir(parents=True,exist_ok=False)
    inputs=dict(p['source_SHA']);inputs.update({str(f):sha(f) for f in [pp,plan,specs,sp,gp,trial,sdc]})
    r={'scope':'ACTUAL13507_INTERFACE_STRICT_UPPER_OBS_PLAN_REALIZATION_NO_NEW_CONDUCTORS_NOT_COMPLETE_SYSTEM',
       'source_SHA':inputs,'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip(),'scheduler_job':os.environ['SLURM_JOB_ID'],
       'full_qualification':False,'geometry_search_repeated':False,'source_program_failure':'Parent-owned planner finished, old coordinate variable shadowed original SDC dictionary before any native edit',
       'all_signal_pins':13507,'actual_requested_XY_changes':len(chosen),'new_cells_sizes_WIREs_vias_or_architecture_changes':0,
       'original_allowed_layers':'signal M2-M8; clock M4-M8 unchanged','original_SDC_clocks_and_loads':'UNCHANGED',
       'historical_target_layers':'PARTIAL_OR_UNKNOWN_RETAINED; controlled first-hop reservation is not an original target reassignment',
       'all13507_plan_statuses':p['all13507_status_counts'],'native_returncodes':{}}
    save=lambda:(out/'execution.json').write_text(json.dumps(r,indent=2)+'\n');save()
    helper=(DRIVER/'physical_trial.tcl').read_text().split('if {![stage load {',1)[0]
    common=['singularity','exec','--cleanenv','--bind',str(ROOT/'tmp')+':/tmp','--home',str(ROOT/'home'),'--pwd',str(out)]
    for prefix in ['/public/home/yuzelu/project-circuit','/public/home/yuzelu/PingyangHuang/issue-55']:common+=['--bind',prefix+':'+prefix+':ro']
    for lib in original['libs']:
        if Path(lib).is_file():common+=['--bind',lib+':'+lib+':ro']
    def native(label,body,threads=8):
        script=out/(label+'.tcl');script.write_text(helper.replace('$out/stages.tsv','$out/'+label+'.stages.tsv')+'\n'+body+'\n')
        rc=execute(common,script,out/(label+'.log'),'PINXY_OUTPUT='+str(out)+',PINXY_ACCESS_ALL=1,PINXY_ACCESS_OUT='+str(out/'whole_access.tsv.gz'),threads=threads)
        r['native_returncodes'][label]=rc;save();return rc
    try:
        libs=['read_liberty '+tcl(lib) for lib in original['libs']]
        body='\n'.join(libs+['read_db '+tcl(odb),'fingerprint '+tcl(out/'before'),'source '+tcl(specs)])+r'''
if {![stage actual_all_source_bound_pin_moves {
 set b [ord::get_db_block]
 foreach spec $stub_specs {
  lassign $spec pin net layer points tx ty method oldbox
  if {$method ne "OWN_EXISTING_METAL_NO_NEW_WIRE" || [llength $points]} {error "This resumption forbids new conductors"}
  set bt [$b findBTerm $pin];if {$bt eq "NULL" || [[$bt getNet] getName] ne $net || [$bt getSigType] in {POWER GROUND}} {error "Original interface peer changed"}
  place_pin -pin_name $pin -layer $layer -location [list [expr {$tx/2000.}] [expr {$ty/2000.}]] -pin_size {.14 .14}
 }
}]} {close $stages;exit 1}
'''
        body+='\n'+'\n'.join(['fingerprint '+tcl(out/'after'),'write_db '+tcl(out/'routed.odb'),'write_def '+tcl(out/'routed.def'),
            'stage VDD {check_power_grid -net VDD -error_file '+tcl(out/'VDD.rpt')+'}','stage VSS {check_power_grid -net VSS -error_file '+tcl(out/'VSS.rpt')+'}',
            'source '+tcl(DRIVER/'export_access.tcl'),'close $stages'])
        assert native('actual_edit_and_geometry',body)==0
        targets={x['pin']:(x['original_layer'],[x['target_center_DBU'][0]-140,x['target_center_DBU'][1]-140,x['target_center_DBU'][0]+140,x['target_center_DBU'][1]+140]) for x in chosen}
        r['complete_pin_contract']=pin_contract(out,targets,13507)
        r['all_cells_connections_PG_die_preserved']={k:sha(out/('before.'+k+'.tsv'))==sha(out/('after.'+k+'.tsv')) for k in ['cells','pdn','die']};assert all(r['all_cells_connections_PG_die_preserved'].values())
        before,bc=routing_box_hashes(geo,725253);after,ac=routing_box_hashes(out/'whole_access.tsv.gz',725253)
        r['all_original_WIRE_VIA_exact']=before==after and bc==ac;assert r['all_original_WIRE_VIA_exact']
        r['whole_signal_geometry']=check(out/'whole_access.tsv.gz',True);assert r['whole_signal_geometry']['pass']
        routing='set_routing_layers -signal metal2-metal8 -clock metal4-metal8'
        assert native('fresh_DRC','read_db '+tcl(out/'routed.odb')+'\n'+routing+'\ndrt::check_drc -output_file '+tcl(out/'independent.drc')+'\nclose $stages',4)==0
        r['fresh_DRC_count']=len(re.findall(r'^violation type:',(out/'independent.drc').read_text(),re.M));save()
        if r['fresh_DRC_count']==0:r['actual_full_parent_AP']=probe(out,native);save()
        assert native('RC_STA','\n'.join(libs+['read_db '+tcl(out/'routed.odb'),'read_sdc '+tcl(sdc),'source /OpenROAD-flow-scripts/flow/platforms/nangate45/setRC.tcl',
            'stage rcx {define_process_corner -ext_model_index 0 X;set_extraction_rules_file /OpenROAD-flow-scripts/flow/platforms/nangate45/rcx_patterns.rules;extract_parasitics;write_spef '+tcl(out/'extracted.spef')+';read_spef '+tcl(out/'extracted.spef')+'}',
            'stage sta {report_worst_slack -max -digits 6 > '+tcl(out/'setup.txt')+';report_worst_slack -min -digits 6 > '+tcl(out/'hold.txt')+';report_check_types -violators -max_delay -min_delay -max_slew -max_capacitance -max_fanout -recovery -removal -max_count 1000000 -digits 6 > '+tcl(out/'checks.txt')+';report_parasitic_annotation -report_unannotated > '+tcl(out/'parasitic_coverage.txt')+';check_setup -verbose > '+tcl(out/'constraint_coverage.txt')+'}','close $stages']))==0
        for kind in ['setup','hold']:r[kind+'_ns']=float(re.search(r'worst slack (?:max|min)\s+([-\d.]+)',(out/(kind+'.txt')).read_text())[1])
    except Exception:r['actual_failure']=traceback.format_exc();traceback.print_exc()
    r['native_stages']={f.name:{x['stage']:x['status'] for x in csv.DictReader(f.open(),delimiter='\t')} for f in out.glob('*stages.tsv')}
    r['all_closed_sources_unchanged']=all(sha(Path(f))==v for f,v in inputs.items());r['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    r['files']={f.name:{'bytes':f.stat().st_size,'sha256':sha(f)} for f in out.iterdir() if f.is_file() and f.name!='execution.json'};save()
    return int(bool(r.get('actual_failure')) or not r['all_closed_sources_unchanged'] or r.get('fresh_DRC_count')!=0 or not r.get('actual_full_parent_AP',{}).get('pass'))
if __name__=='__main__':sys.exit(run(sys.argv[1]))
