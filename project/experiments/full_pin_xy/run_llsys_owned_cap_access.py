"""Native LL access-pin ECO reusing real existing same-net via metal.

No final-LEF editing and no invented wire. This intentionally retains original
wire stubs and their cost. GRT/DRT search is not reexecuted: actual source routes
are reused unchanged, then independently checked and extracted. Parent AP and
complete qualification remain separate required stages.
"""
from pathlib import Path
import csv,datetime,json,os,re,subprocess,sys,traceback
from run_exports import ROOT,IMAGE,BIN,sha
from run_parent_trial import tcl
from run_escape_fixture import execute
from run_llsys_actual_tips import pin_contract
from compare_native_route_representations import routing_box_hashes
from check_access import check

DRIVER=Path(__file__).resolve().parent


def run(revision):
    audit=ROOT/'all_llsys_actual_access_caps/r01';aq=json.loads((audit/'execution.json').read_text())
    assert aq.get('completed_utc') and aq['native_read_only_returncode']==0 and aq['all_closed_sources_unchanged'] and aq['duplicate_candidate_pins']==0
    table=audit/'all13507_actual_own_via_candidates.tsv';assert sha(table)==aq['files'][table.name]['sha256']
    selected=[r for r in csv.DictReader(table.open(),delimiter='\t') if r['candidate_x']]
    assert len(selected)==10261
    source=ROOT/'llsys_parent_access_tip/r01';rp=source/'execution.json';prior=json.loads(rp.read_text())
    assert prior.get('completed_utc') and prior['fresh_DRC_count']==0 and prior['whole_signal_geometry']['pass'] and prior['all_closed_sources_unchanged']
    odb=source/'routed.odb';geometry=source/'whole_access.tsv.gz'
    for p in [odb,geometry]:assert sha(p)==prior['files'][p.name]['sha256']
    assert sha(odb)==aq['source_geometry_SHA256']
    trial=ROOT/'trials/llsys-pg-r03/llaccel_aux-C/execution.json';old=json.loads(trial.read_text());sdc=Path(old['source_sdc'])
    assert sha(sdc)==old['input_sha256'][str(sdc)]
    inputs={str(p):sha(p) for p in [audit/'execution.json',table,rp,odb,geometry,trial,sdc]}
    out=ROOT/'llsys_owned_cap_access'/revision;out.mkdir(parents=True,exist_ok=False)
    rec={'scope':'ACTUAL_NATIVE_BPIN_ACCESS_ECO_ON_EXISTING_SAME_NET_ROUTED_METAL_NOT_PARENT_ACCESS_OR_FULL_QUALIFICATION',
         'source_SHA':inputs,'source_native_DRC_count':0,'full_qualification':False,
         'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip(),'scheduler_job':os.environ['SLURM_JOB_ID'],
         'native_returncodes':{},'new_cells_or_sizes':0,'requested_actual_pin_changes':10261,
         'original_signal_pins':13507,'GRT_or_DRT_search_reexecuted':False,
         'wire_stub_policy':'Retain all original real WIRE/VIA material and cost; new BPin must fit an existing same-net via cap. No route-length reduction assumed.',
         'historical_parent_target_layers':'PARTIAL_OR_UNKNOWN_UNCHANGED','new_parent_AP_complete_GDS_RTL':'NOT_EXECUTED',
         'allowed_layers':{'signal':'metal2-metal8','clock':'metal4-metal8'},
         'physical_status':'RUNNING_NATIVE_EDIT_AND_SEPARATE_GATES'}
    save=lambda:(out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n');save()
    targets={}
    specs=[]
    for r in selected:
        x,y=int(r['candidate_x']),int(r['candidate_y']);new=[x-140,y-140,x+140,y+140]
        targets[r['pin']]=(r['layer'],new)
        specs.append(tcl(' '.join([r['pin'],r['net'],r['layer']]+[r[k] for k in ['x0','y0','x1','y1','candidate_x','candidate_y','via']])))
    (out/'source_bound_specs.tcl').write_text('set specs {\n'+'\n'.join(specs)+'\n}\n')
    common=['singularity','exec','--cleanenv','--bind',str(ROOT/'tmp')+':/tmp',
            '--bind','/public/home/yuzelu/project-circuit:/public/home/yuzelu/project-circuit:ro',
            '--bind','/public/home/yuzelu/PingyangHuang/issue-55:/public/home/yuzelu/PingyangHuang/issue-55:ro',
            '--home',str(ROOT/'home'),'--pwd',str(out)]
    try:
        rec['actual_OpenROAD_binary_SHA256']=subprocess.check_output(common+[IMAGE,'sha256sum',BIN]).decode().split()[0]
        helper=(DRIVER/'physical_trial.tcl').read_text().split('if {![stage load {',1)[0]
        contracts=(DRIVER/'output_chain_placement.tcl').read_text().split('read_db $::env(PINXY_CHAIN_SOURCE)',1)[0]
        prefix=[helper,contracts]+['read_liberty '+tcl(p) for p in old['libs']]
        lines=prefix+['read_db '+tcl(odb),'set_routing_layers -signal metal2-metal8 -clock metal4-metal8',
          'fingerprint '+tcl(out/'before'),'set original_obs [obs_snapshot]',
          'source '+tcl(out/'source_bound_specs.tcl'),
          'if {![stage actual_existing_metal_pin_edit {source '+tcl(DRIVER/'llsys_owned_cap_pin_edit.tcl')+'}]} {catch {write_db '+tcl(out/'failed_edit.odb')+'};close $stages;exit 1}',
          'if {[obs_snapshot] ne $original_obs} {error "Original OBS changed"}',
          'fingerprint '+tcl(out/'after'),'write_db '+tcl(out/'routed.odb'),'write_def '+tcl(out/'routed.def'),'write_verilog '+tcl(out/'mapped.v'),
          'stage VDD {check_power_grid -net VDD -error_file '+tcl(out/'VDD.rpt')+'}',
          'stage VSS {check_power_grid -net VSS -error_file '+tcl(out/'VSS.rpt')+'}',
          'stage whole_signal_geometry {source '+tcl(DRIVER/'export_access.tcl')+'}','close $stages']
        script=out/'edit.tcl';script.write_text('\n'.join(lines)+'\n')
        rec['native_returncodes']['actual_edit_and_geometry_export']=execute(common,script,out/'native.log','PINXY_OUTPUT='+str(out)+',PINXY_ACCESS_ALL=1,PINXY_ACCESS_OUT='+str(out/'whole_access.tsv.gz'),threads=4);save()
        assert rec['native_returncodes']['actual_edit_and_geometry_export']==0
        rec['complete_pin_contract']=pin_contract(out,targets,13507)
        rec['all_original_cells_signal_connections_PG_die_unchanged']={k:sha(out/('before.'+k+'.tsv'))==sha(out/('after.'+k+'.tsv')) for k in ['cells','pdn','die']}
        assert all(rec['all_original_cells_signal_connections_PG_die_unchanged'].values());save()
        script=out/'fresh.tcl';script.write_text('read_db '+tcl(out/'routed.odb')+'\nset_routing_layers -signal metal2-metal8 -clock metal4-metal8\ndrt::check_drc -output_file '+tcl(out/'independent.drc')+'\n')
        rec['native_returncodes']['fresh_DRC']=execute(common,script,out/'independent.log',threads=1)
        if rec['native_returncodes']['fresh_DRC']==0:rec['fresh_DRC_count']=len(re.findall(r'^violation type:',(out/'independent.drc').read_text(),re.M))
        save()
        rec['whole_signal_geometry']=check(out/'whole_access.tsv.gz',True)
        a,_=routing_box_hashes(geometry,725253);b,_=routing_box_hashes(out/'whole_access.tsv.gz',725253)
        rec['all_725253_original_WIRE_VIA_rectangle_multisets_identical']=a==b
        assert a==b and rec['whole_signal_geometry']['pass'];save()
        lines=prefix+['read_db '+tcl(out/'routed.odb'),'read_sdc '+tcl(sdc),'source /OpenROAD-flow-scripts/flow/platforms/nangate45/setRC.tcl',
          'set_routing_layers -signal metal2-metal8 -clock metal4-metal8',
          'stage rcx {define_process_corner -ext_model_index 0 X;set_extraction_rules_file /OpenROAD-flow-scripts/flow/platforms/nangate45/rcx_patterns.rules;extract_parasitics;write_spef '+tcl(out/'extracted.spef')+';read_spef '+tcl(out/'extracted.spef')+'}',
          'stage sta {report_worst_slack -max -digits 6 > '+tcl(out/'setup.txt')+';report_worst_slack -min -digits 6 > '+tcl(out/'hold.txt')+';report_check_types -violators -max_delay -min_delay -max_slew -max_capacitance -max_fanout -recovery -removal -max_count 1000000 -digits 6 > '+tcl(out/'checks.txt')+';check_setup -verbose > '+tcl(out/'constraint_coverage.txt')+';report_parasitic_annotation -report_unannotated > '+tcl(out/'parasitic_coverage.txt')+'}','close $stages']
        script=out/'extract_and_time.tcl';script.write_text('\n'.join(lines)+'\n')
        # Independent stage filename: do not overwrite the edit-stage ledger.
        script.write_text(script.read_text().replace('$out/stages.tsv','$out/RC_STA_stages.tsv'))
        rec['native_returncodes']['RC_STA']=execute(common,script,out/'RC_STA.log','PINXY_OUTPUT='+str(out),threads=4)
        for kind in ['setup','hold']:
            p=out/(kind+'.txt')
            if p.exists():rec[kind+'_ns']=float(re.search(r'worst slack (?:max|min)\s+([-\d.]+)',p.read_text())[1])
        if (out/'checks.txt').exists():rec['literal_VIOLATED_markers_not_complete_failure_count']=(out/'checks.txt').read_text().count('(VIOLATED)')
        rec['physical_status']='NATIVE_ACCESS_ECO_GATES_COLLECTED_NOT_PARENT_OR_FULL_QUALIFICATION'
    except Exception:rec['actual_failure']=traceback.format_exc()
    for filename,key in [('stages.tsv','native_edit_stage_status'),('RC_STA_stages.tsv','native_RC_STA_stage_status')]:
        if (out/filename).exists():
            with (out/filename).open() as f:rec[key]={r['stage']:r['status'] for r in csv.DictReader(f,delimiter='\t')}
    rec['all_closed_sources_unchanged']=all(sha(Path(p))==s for p,s in inputs.items())
    rec['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    rec['files']={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in out.iterdir() if p.is_file() and p.name!='execution.json'};save()
    passed='actual_failure' not in rec and rec.get('fresh_DRC_count')==0 and rec.get('setup_ns',-1)>=0 and rec.get('hold_ns',-1)>=0 and rec.get('literal_VIOLATED_markers_not_complete_failure_count')==0
    passed=passed and all(rec.get('native_edit_stage_status',{}).get(k)=='EXECUTED' for k in ['actual_existing_metal_pin_edit','VDD','VSS','whole_signal_geometry']) and all(rec.get('native_RC_STA_stage_status',{}).get(k)=='EXECUTED' for k in ['rcx','sta'])
    return 0 if passed and rec['all_closed_sources_unchanged'] else 1


if __name__=='__main__':sys.exit(run(sys.argv[1]))
