"""Real MXU one-pin via-tip ECO, full native/PG/RC/STA gates, no qualification claim."""
from pathlib import Path
from collections import Counter
import csv,datetime,gzip,json,os,re,subprocess,sys,traceback
from run_exports import ROOT,IMAGE,BIN,sha
from run_parent_trial import tcl
from run_escape_fixture import execute
from run_llsys_actual_tips import pin_contract
from check_access import check
from compare_native_route_representations import routing_box_hashes

DRIVER=Path(__file__).resolve().parent
TARGETS={'act_data[12]':('metal6',[656930,2177280,657210,2177560])}
REMOVED=[('metal6',656510,2137600,657770,2137880),('metal6',657490,2137600,657770,2139480),
         ('metal6',656930,2139200,657770,2139480),('metal6',656930,2139200,657210,2177560)]


def run(revision):
    source=ROOT/'pin_escape_route/r02/mxu-C';rp=source/'execution.json';prior=json.loads(rp.read_text())
    assert prior.get('completed_utc') and prior['native_returncodes']['implementation']==prior['native_returncodes']['fresh_DRC']==0
    assert prior['fresh_DRC_count']==0 and prior['whole_signal_geometry']['pass'] and prior['all_closed_sources_unchanged']
    odb=source/'routed.odb';geometry=source/'whole_access.tsv.gz'
    for p in [odb,geometry]:assert sha(p)==prior['files'][p.name]['sha256']
    view=ROOT/'pin_escape_views/r01/mxu-C';vp=view/'execution.json';v=json.loads(vp.read_text())
    assert v['native_export_returncode']==0 and v['source_geometry_sha256']==sha(odb) and v['matching_all_signal_model_pins']==2172
    target=view/'target_pin_access.tsv.gz';assert sha(target)==v['files'][target.name]['sha256']
    trial=ROOT/'trials/access-r03/mxu-C/execution.json';old=json.loads(trial.read_text());sdc=Path(old['source_sdc'])
    assert sha(sdc)==old['input_sha256'][str(sdc)]
    inputs={str(p):sha(p) for p in [rp,odb,geometry,vp,target,trial,sdc]}
    out=ROOT/'mxu_actual_via_tip'/revision;out.mkdir(parents=True,exist_ok=False)
    rec={'scope':'ACTUAL_ONE_M6_PIN_VIA_TIP_NATIVE_ROUTE_ECO_NOT_FULL_QUALIFICATION',
      'source_SHA':inputs,'full_qualification':False,'native_returncodes':{},
      'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip(),'scheduler_job':os.environ['SLURM_JOB_ID'],
      'new_cells_or_sizes':0,'inherited_cost':'One original MXU costed/r04 sizing retained; not a pure XY benefit.',
      'edit':'Move act_data[12] on original M6/0.14-square to its existing own via5 M6 cap; delete exactly four old M6 terminal WIRE rectangles; preserve every actual via.',
      'GRT_or_DRT_search_reexecuted':False,'actual_implementation':'Native routed dbWire encoder, not final LEF editing',
      'parent_access_full_GDS_RTL':'NOT_EXECUTED; old parent results cannot qualify this new source',
      'historical_target_layers':'PARTIAL_OR_UNKNOWN_UNCHANGED; no new historical target assigned'}
    save=lambda:(out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n')
    save()
    common=['singularity','exec','--cleanenv','--bind',str(ROOT/'tmp')+':/tmp',
      '--bind','/public/home/yuzelu/PingyangHuang/issue-55:/public/home/yuzelu/PingyangHuang/issue-55:ro',
      '--bind','/public/home/yuzelu/project-circuit:/public/home/yuzelu/project-circuit:ro',
      '--home',str(ROOT/'home'),'--pwd',str(out)]
    try:
        lib='/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib'
        rec['container_library_SHA256']=subprocess.check_output(common+[IMAGE,'sha256sum',lib]).decode().split()[0]
        rec['actual_OpenROAD_binary_SHA256']=subprocess.check_output(common+[IMAGE,'sha256sum',BIN]).decode().split()[0]
        helper=(DRIVER/'physical_trial.tcl').read_text().split('if {![stage load {',1)[0]
        contracts=(DRIVER/'output_chain_placement.tcl').read_text().split('read_db $::env(PINXY_CHAIN_SOURCE)',1)[0]
        lines=[helper,contracts]+['read_liberty '+tcl(p) for p in old['libs']]
        lines+=['read_db '+tcl(odb),'read_sdc '+tcl(sdc),'source /OpenROAD-flow-scripts/flow/platforms/nangate45/setRC.tcl',
          'set_routing_layers -signal metal2-metal8 -clock metal4-metal8','fingerprint '+tcl(out/'before'),
          'set original_obs [obs_snapshot]',
          'if {![stage actual_one_net_pin_and_route_edit {source '+tcl(DRIVER/'mxu_move_to_actual_via_tip.tcl')+'}]} {catch {write_db '+tcl(out/'failed_edit.odb')+'};close $stages;exit 1}',
          'if {[obs_snapshot] ne $original_obs} {error "Original OBS changed"}',
          'fingerprint '+tcl(out/'after'),'write_db '+tcl(out/'routed.odb'),'write_def '+tcl(out/'routed.def'),'write_verilog '+tcl(out/'mapped.v'),
          'stage VDD {check_power_grid -net VDD -error_file '+tcl(out/'VDD.rpt')+'}',
          'stage VSS {check_power_grid -net VSS -error_file '+tcl(out/'VSS.rpt')+'}',
          'stage whole_signal_geometry {source '+tcl(DRIVER/'export_access.tcl')+'}',
          'stage rcx {define_process_corner -ext_model_index 0 X;set_extraction_rules_file /OpenROAD-flow-scripts/flow/platforms/nangate45/rcx_patterns.rules;extract_parasitics;write_spef '+tcl(out/'extracted.spef')+';read_spef '+tcl(out/'extracted.spef')+'}',
          'stage sta {report_worst_slack -max -digits 6 > '+tcl(out/'setup.txt')+';report_worst_slack -min -digits 6 > '+tcl(out/'hold.txt')+';report_check_types -violators -max_delay -min_delay -max_slew -max_capacitance -max_fanout -recovery -removal -max_count 1000000 -digits 6 > '+tcl(out/'checks.txt')+';check_setup -verbose > '+tcl(out/'constraint_coverage.txt')+';report_parasitic_annotation -report_unannotated > '+tcl(out/'parasitic_coverage.txt')+'}','close $stages']
        script=out/'edit.tcl';script.write_text('\n'.join(lines)+'\n')
        env='PINXY_OUTPUT='+str(out)+',PINXY_ACCESS_ALL=1,PINXY_ACCESS_OUT='+str(out/'whole_access.tsv.gz')
        rec['native_returncodes']['actual_edit_and_analysis']=execute(common,script,out/'native.log',env,threads=4);save()
        if (out/'routed.odb').exists():
            script=out/'fresh.tcl';script.write_text('read_db '+tcl(out/'routed.odb')+'\nset_routing_layers -signal metal2-metal8 -clock metal4-metal8\ndrt::check_drc -output_file '+tcl(out/'independent.drc')+'\n')
            rec['native_returncodes']['fresh_DRC']=execute(common,script,out/'independent.log',threads=1)
            if rec['native_returncodes']['fresh_DRC']==0:rec['fresh_DRC_count']=len(re.findall(r'^violation type:',(out/'independent.drc').read_text(),re.M))
        if (out/'whole_access.tsv.gz').exists():
            rec['whole_signal_geometry']=check(out/'whole_access.tsv.gz',True)
            a,_=routing_box_hashes(geometry,191438);b,_=routing_box_hashes(out/'whole_access.tsv.gz',191438)
            assert set(a)==set(b) and {n for n in a if a[n]!=b[n]}==set(TARGETS)
            rec['all_other_191437_multiterminal_route_box_multisets_identical']=True
            def material(path):
                result=Counter()
                with gzip.open(path,'rt') as f:
                    for r in csv.DictReader(f,delimiter='\t'):
                        if r['net'] in TARGETS and r['kind'] in ['WIRE','VIA']:result[tuple(r[k] for k in ['kind','layer','x0','y0','x1','y1'])]+=1
                return result
            before,after=material(geometry),material(out/'whole_access.tsv.gz')
            want=Counter(('WIRE',r[0])+tuple(map(str,r[1:])) for r in REMOVED)
            assert not after-before and before-after==want
            rec['exactly_four_actual_M6_WIRE_rectangles_removed_all_vias_unchanged']=True
        if (out/'after.pins.tsv').exists():rec['complete_pin_contract']=pin_contract(out,TARGETS,2172)
        rec['all_cells_signal_connections_PG_die_unchanged']={k:(out/('after.'+k+'.tsv')).exists() and sha(out/('before.'+k+'.tsv'))==sha(out/('after.'+k+'.tsv')) for k in ['cells','pdn','die']}
        for k in ['setup','hold']:
            p=out/(k+'.txt')
            if p.exists():rec[k+'_ns']=float(re.search(r'worst slack (?:max|min)\s+([-\d.]+)',p.read_text())[1])
        if (out/'checks.txt').exists():rec['literal_VIOLATED_markers_not_complete_failure_count']=(out/'checks.txt').read_text().count('(VIOLATED)')
        if (out/'stages.tsv').exists():
            with (out/'stages.tsv').open() as f:rec['native_stage_status']={r['stage']:r['status'] for r in csv.DictReader(f,delimiter='\t')}
        rec['container_library_unchanged']=subprocess.check_output(common+[IMAGE,'sha256sum',lib]).decode().split()[0]==rec['container_library_SHA256']
    except Exception:rec['actual_failure']=traceback.format_exc()
    rec['all_closed_sources_unchanged']=all(sha(Path(p))==h for p,h in inputs.items())
    rec['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    rec['files']={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in out.iterdir() if p.is_file() and p.name!='execution.json'};save()
    passed=('actual_failure' not in rec and rec['native_returncodes'].get('actual_edit_and_analysis')==0 and rec.get('fresh_DRC_count')==0 and rec.get('whole_signal_geometry',{}).get('pass') and rec.get('complete_pin_contract') and all(rec.get('all_cells_signal_connections_PG_die_unchanged',{}).values()) and rec.get('all_other_191437_multiterminal_route_box_multisets_identical') and rec.get('exactly_four_actual_M6_WIRE_rectangles_removed_all_vias_unchanged') and rec.get('setup_ns',-1)>=0 and rec.get('hold_ns',-1)>=0 and rec.get('literal_VIOLATED_markers_not_complete_failure_count')==0 and rec.get('container_library_unchanged') and rec['all_closed_sources_unchanged'] and all(rec.get('native_stage_status',{}).get(k)=='EXECUTED' for k in ['VDD','VSS','rcx','sta','whole_signal_geometry']))
    return 0 if passed else 1


if __name__=='__main__':sys.exit(run(sys.argv[1]))
