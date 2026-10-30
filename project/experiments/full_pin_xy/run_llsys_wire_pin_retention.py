"""Actual remaining WIRE BPin edit, retaining old conductor material exactly.

Original routed dbWire opcodes are appended to, never reconstructed. Actual
metallization union is preserved; no reduction in routed length is claimed.
"""
from pathlib import Path
from collections import defaultdict
import csv,datetime,json,os,re,subprocess,sys,traceback
from run_exports import ROOT,IMAGE,BIN,sha
from run_parent_trial import tcl
from run_escape_fixture import execute
from run_llsys_actual_tips import pin_contract
from compare_native_route_representations import routing_box_hashes
from check_access import check
DRIVER=Path(__file__).resolve().parent

def run(revision):
    audit=ROOT/'wire_candidate_metal_preflight/r01';aq=json.loads((audit/'execution.json').read_text());table=audit/'all2832_current_wire_metal_preflight.csv'
    assert aq.get('completed_utc') and aq['all_closed_sources_unchanged'] and aq['all_2832_original_pin_contracts_and_current_candidate_WIRE_verified']
    assert sha(table)==aq['files'][table.name]['sha256'];selected=list(csv.DictReader(table.open()));assert len(selected)==2832
    proof=ROOT/'pin_retention_consumers/r02/execution.json';pq=json.loads(proof.read_text());consumer=pq['actual_stream_consumer']
    assert pq.get('completed_utc') and all(v==0 for v in pq['native_returncodes'].values()) and consumer['all_M5_GDS_roundtrip_XOR_empty']
    assert all(v['exact_expected_metal_present'] and not v['local_extra_metal'] for v in consumer['methods'].values())
    append_proof=ROOT/'native_wire_append_api/r02/execution.json';app=json.loads(append_proof.read_text());assert app['native_returncode']==0 and app['actual_rectangle_multisets_and_native_FIXED_ROUTED_path_flags_preserved']
    source=ROOT/'owned_cap_wire_restore/r01';rp=source/'execution.json';sq=json.loads(rp.read_text());odb=source/'routed.odb';geometry=source/'whole_access.tsv.gz'
    assert sq.get('completed_utc') and sq['fresh_DRC_count']==0 and sq['whole_signal_geometry']['pass'] and sq['all_closed_sources_unchanged']
    for p in [odb,geometry]:assert sha(p)==sq['files'][p.name]['sha256']
    assert aq['source_SHA'][str(odb)]==sha(odb)
    trial=ROOT/'trials/llsys-pg-r03/llaccel_aux-C/execution.json';old=json.loads(trial.read_text());sdc=Path(old['source_sdc']);assert sha(sdc)==old['input_sha256'][str(sdc)]
    inputs={str(p):sha(p) for p in [audit/'execution.json',table,proof,append_proof,rp,odb,geometry,trial,sdc]}
    out=ROOT/'llsys_wire_pin_retention'/revision;out.mkdir(parents=True,exist_ok=False)
    rec={'scope':'ACTUAL_2832_WIRE_ACCESS_PIN_EDITS_WITH_EXACT_OLD_METAL_RETENTION_NOT_PARENT_ACCESS_OR_FULL_QUALIFICATION','source_SHA':inputs,'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip(),'scheduler_job':os.environ['SLURM_JOB_ID'],'native_returncodes':{},'full_qualification':False,'requested_pin_changes':2832,'prior_10261_internal_points_retained':True,'new_cells_sizes_or_vias':0,'GRT_DRT_search_reexecuted':False,'allowed_routing_layers':{'signal':'metal2-metal8','clock':'metal4-metal8'},'historical_parent_target_layers':'PARTIAL_OR_UNKNOWN_UNCHANGED','parent_access_full_rules_GDS_RTL':'NOT_EXECUTED','not_routed_length_or_area_saving':True}
    save=lambda:(out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n');save()
    targets={};specs=[];extras=defaultdict(list)
    for r in selected:
        x,y=int(r['candidate_x']),int(r['candidate_y']);targets[r['pin']]=(r['layer'],[x-140,y-140,x+140,y+140]);retain=int(r['old_pin_metal_that_would_be_removed_DBU2'])>0
        if retain:extras[r['net']].append(('WIRE',r['layer'])+tuple(int(r[k]) for k in ['x0','y0','x1','y1']))
        specs.append(tcl(' '.join([r['pin'],r['net'],r['layer']]+[r[k] for k in ['x0','y0','x1','y1','candidate_x','candidate_y']]+[str(int(retain))])))
    assert sum(map(len,extras.values()))==2827
    (out/'source_bound_specs.tcl').write_text('set specs {\n'+'\n'.join(specs)+'\n}\n')
    common=['singularity','exec','--cleanenv','--bind',str(ROOT/'tmp')+':/tmp','--bind','/public/home/yuzelu/project-circuit:/public/home/yuzelu/project-circuit:ro','--bind','/public/home/yuzelu/PingyangHuang/issue-55:/public/home/yuzelu/PingyangHuang/issue-55:ro','--home',str(ROOT/'home'),'--pwd',str(out)]
    try:
        rec['actual_OpenROAD_binary_SHA256']=subprocess.check_output(common+[IMAGE,'sha256sum',BIN]).decode().split()[0];assert rec['actual_OpenROAD_binary_SHA256']==sq['actual_OpenROAD_binary_SHA256']
        helper=(DRIVER/'physical_trial.tcl').read_text().split('if {![stage load {',1)[0];contracts=(DRIVER/'output_chain_placement.tcl').read_text().split('read_db $::env(PINXY_CHAIN_SOURCE)',1)[0]
        prefix=[helper,contracts]+['read_liberty '+tcl(p) for p in old['libs']]
        lines=prefix+['read_db '+tcl(odb),'set_routing_layers -signal metal2-metal8 -clock metal4-metal8','fingerprint '+tcl(out/'before'),'set original_obs [obs_snapshot]','source '+tcl(out/'source_bound_specs.tcl'),
          'if {![stage actual_wire_pin_retention {source '+tcl(DRIVER/'llsys_wire_pin_retention_edit.tcl')+'}]} {catch {write_db '+tcl(out/'failed_edit.odb')+'};close $stages;exit 1}',
          'if {[obs_snapshot] ne $original_obs} {error "Original OBS changed"}','fingerprint '+tcl(out/'after'),'write_db '+tcl(out/'routed.odb'),'write_def '+tcl(out/'routed.def'),'write_verilog '+tcl(out/'mapped.v'),
          'stage VDD {check_power_grid -net VDD -error_file '+tcl(out/'VDD.rpt')+'}','stage VSS {check_power_grid -net VSS -error_file '+tcl(out/'VSS.rpt')+'}','stage whole_signal_geometry {source '+tcl(DRIVER/'export_access.tcl')+'}','close $stages']
        script=out/'edit.tcl';script.write_text('\n'.join(lines)+'\n');rec['native_returncodes']['actual_edit_and_export']=execute(common,script,out/'native.log','PINXY_OUTPUT='+str(out)+',PINXY_ACCESS_ALL=1,PINXY_ACCESS_OUT='+str(out/'whole_access.tsv.gz'),threads=4);save();assert rec['native_returncodes']['actual_edit_and_export']==0
        rec['complete_pin_contract']=pin_contract(out,targets,13507);rec['all_original_cells_connections_PG_die_exact']={k:sha(out/('before.'+k+'.tsv'))==sha(out/('after.'+k+'.tsv')) for k in ['cells','pdn','die']};assert all(rec['all_original_cells_connections_PG_die_exact'].values());save()
        script=out/'fresh.tcl';script.write_text('read_db '+tcl(out/'routed.odb')+'\nset_routing_layers -signal metal2-metal8 -clock metal4-metal8\ndrt::check_drc -output_file '+tcl(out/'independent.drc')+'\n');rec['native_returncodes']['fresh_DRC']=execute(common,script,out/'independent.log',threads=1)
        if rec['native_returncodes']['fresh_DRC']==0:rec['fresh_DRC_count']=len(re.findall(r'^violation type:',(out/'independent.drc').read_text(),re.M))
        save();rec['whole_signal_geometry']=check(out/'whole_access.tsv.gz',True)
        expected,total=routing_box_hashes(geometry,725253,extras);actual,actual_total=routing_box_hashes(out/'whole_access.tsv.gz',725253)
        assert expected==actual and total==actual_total and rec['whole_signal_geometry']['pass']
        rec['all_original_WIRE_VIA_exact_plus_only_2827_requested_old_pin_WIRE_squares']=True;rec['actual_metal_union_unchanged_from_source_wire_via_plus_original_BPins']=True;save()
        lines=prefix+['read_db '+tcl(out/'routed.odb'),'read_sdc '+tcl(sdc),'source /OpenROAD-flow-scripts/flow/platforms/nangate45/setRC.tcl','set_routing_layers -signal metal2-metal8 -clock metal4-metal8',
          'stage rcx {define_process_corner -ext_model_index 0 X;set_extraction_rules_file /OpenROAD-flow-scripts/flow/platforms/nangate45/rcx_patterns.rules;extract_parasitics;write_spef '+tcl(out/'extracted.spef')+';read_spef '+tcl(out/'extracted.spef')+'}',
          'stage sta {report_worst_slack -max -digits 6 > '+tcl(out/'setup.txt')+';report_worst_slack -min -digits 6 > '+tcl(out/'hold.txt')+';report_check_types -violators -max_delay -min_delay -max_slew -max_capacitance -max_fanout -recovery -removal -max_count 1000000 -digits 6 > '+tcl(out/'checks.txt')+';check_setup -verbose > '+tcl(out/'constraint_coverage.txt')+';report_parasitic_annotation -report_unannotated > '+tcl(out/'parasitic_coverage.txt')+'}','close $stages']
        script=out/'extract_and_time.tcl';script.write_text(('\n'.join(lines)+'\n').replace('$out/stages.tsv','$out/RC_STA_stages.tsv'));rec['native_returncodes']['RC_STA']=execute(common,script,out/'RC_STA.log','PINXY_OUTPUT='+str(out),threads=4)
        for kind in ['setup','hold']:
            p=out/(kind+'.txt')
            if p.exists():rec[kind+'_ns']=float(re.search(r'worst slack (?:max|min)\s+([-\d.]+)',p.read_text())[1])
        if (out/'checks.txt').exists():rec['literal_VIOLATED_markers_not_complete_failure_count']=(out/'checks.txt').read_text().count('(VIOLATED)')
    except Exception:rec['actual_failure']=traceback.format_exc()
    for filename,key in [('stages.tsv','native_edit_stage_status'),('RC_STA_stages.tsv','native_RC_STA_stage_status')]:
        if (out/filename).exists():rec[key]={r['stage']:r['status'] for r in csv.DictReader((out/filename).open(),delimiter='\t')}
    rec['all_closed_sources_unchanged']=all(sha(Path(p))==s for p,s in inputs.items());rec['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();rec['files']={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in out.iterdir() if p.is_file() and p.name!='execution.json'};save()
    return 0 if not rec.get('actual_failure') and rec.get('fresh_DRC_count')==0 and rec.get('setup_ns',-1)>=0 and rec.get('hold_ns',-1)>=0 and rec.get('literal_VIOLATED_markers_not_complete_failure_count')==0 and rec['all_closed_sources_unchanged'] else 1
if __name__=='__main__':sys.exit(run(sys.argv[1]))
