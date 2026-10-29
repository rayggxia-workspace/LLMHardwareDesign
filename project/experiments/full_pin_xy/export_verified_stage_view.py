"""Export a source-bound physical/research view from closed engineering stages.

Negative timing is retained, never a physical or system qualification claim.
Refuse a source with native DRC or PG failure; verify model/pins and SPEF replay.
"""
from pathlib import Path
from collections import Counter
import csv,datetime,json,os,re,shutil,sys,traceback
from run_exports import ROOT,sha
from run_parent_trial import tcl
from run_escape_fixture import execute
from lef_view_contract import verify
from coarsen_parent_low_obs import coarsen
DRIVER=Path(__file__).resolve().parent

def run(profile,revision):
    choices={
      'llsys_healed':('llaccel_aux',13507,'llsys_same_net_gap_heal/r02','llsys_gap_healed_views'),
      'vector_pose_fixed':('vector',2246,'vector_pose_route_fix/r01','vector_pose_fixed_views'),
      'perimeter_gemm':('gemm',3753,'same_source_perimeter/r01/gemm','same_source_perimeter_views'),
      'perimeter_vector':('vector',2246,'same_source_perimeter/r01/vector','same_source_perimeter_views'),
      'perimeter_opentpu_aux':('opentpu_aux',2229,'same_source_perimeter/r01/opentpu_aux','same_source_perimeter_views')}
    case,count,rel,family=choices[profile];source=ROOT/rel;rp=source/'execution.json';q=json.loads(rp.read_text())
    assert q.get('completed_utc') and not q.get('actual_failure') and q['fresh_DRC_count']==0
    assert q['native_returncodes']['fresh_DRC']==0 and q['whole_signal_geometry']['pass']
    stages=q['native_stages']
    flat={}
    for k,v in stages.items():
        if isinstance(v,dict):flat.update(v)
        else:flat[k]=v
    assert all(flat.get(k)=='EXECUTED' for k in ['VDD','VSS','rcx','sta'])
    if profile=='llsys_healed':
        assert all(q['all_original_cells_ports_connections_pin_XY_layers_sizes_PG_and_die_exact'].values())
        assert q['all_original_WIRE_VIA_exact_plus_requested_patch_rectangles'] and q['all_closed_sources_unchanged']
    elif profile.startswith('perimeter_'):
        assert all(q['exact_C_resource_cells_connections_poses_PG_and_die_preserved'].values()) and q['all_closed_sources_unchanged']
    else:
        assert q['all_closed_sources_unchanged']
    trial=ROOT/('trials/llsys-pg-r03/llaccel_aux-C' if case=='llaccel_aux' else 'trials/access-r03/'+case+'-C')/'execution.json'
    original=json.loads(trial.read_text());sdc=Path(original['source_sdc']);assert sha(sdc)==original['input_sha256'][str(sdc)]
    odb=source/'routed.odb';spef=source/'extracted.spef';pins=source/'after.pins.tsv'
    inputs={str(p):sha(p) for p in [rp,odb,spef,pins,trial,sdc]}
    for p in [odb,spef,pins]:assert sha(p)==q['files'][p.name]['sha256']
    out=ROOT/family/revision/(case+('-Aopt' if profile.startswith('perimeter_') else '-C'));out.mkdir(parents=True,exist_ok=False)
    rec={'scope':'ACTUAL_NATIVE0_PG_CONNECTED_SOURCE_PHYSICAL_RESEARCH_HANDOFF_NOT_FULL_QUALIFICATION','source_profile':profile,'source_receipt':str(rp),'source_SHA':inputs,
      'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip(),'scheduler_job':os.environ['SLURM_JOB_ID'],'full_qualification':False,
      'source_geometry_sha256':sha(odb),'source_SPEF_sha256':sha(spef),'source_setup_ns':q['setup_ns'],'source_min_slack_ns':q['hold_ns'],
      'historical_parent_target_layers':'PARTIAL_OR_UNKNOWN_RETAINED; new controlled M10 landing is not a recovered historical target',
      'original_pin_layers_sizes_function_networks':'UNCHANGED; current physical source after recorded engineering edits is the reference',
      'full_rules_RTL_GDS_and_system':'NOT_QUALIFIED; negative source timing/electrical not waived'}
    try:
        shutil.copyfile(str(odb),str(out/'clean.odb'));assert sha(out/'clean.odb')==sha(odb)
        common=['singularity','exec','--cleanenv','--bind',str(ROOT/'tmp')+':/tmp','--home',str(ROOT/'home'),'--pwd',str(out)]
        for prefix in ['/public/home/yuzelu/project-circuit','/public/home/yuzelu/PingyangHuang/issue-55']:common+=['--bind',prefix+':'+prefix+':ro']
        for lib in original['libs']:
            if Path(lib).is_file():common+=['--bind',lib+':'+lib+':ro']
        lines=['read_liberty '+tcl(lib) for lib in original['libs']]+['read_db '+tcl(out/'clean.odb'),
          'write_abstract_lef '+tcl(out/'abstract.lef'),'write_abstract_lef -bloat_factor 0 '+tcl(out/'detailed.lef'),
          'write_def '+tcl(out/'clean.def'),'write_verilog '+tcl(out/'clean.v'),
          'set b [ord::get_db_block];set f [open '+tcl(out/'pins.tsv')+' w];puts $f "pin\\tdirection\\tuse\\tnet\\tlayer\\tx0\\ty0\\tx1\\ty1";foreach p [$b getBTerms] {foreach bp [$p getBPins] {foreach r [$bp getBoxes] {puts $f [join [list [$p getName] [$p getIoType] [$p getSigType] [[$p getNet] getName] [[$r getTechLayer] getName] [$r xMin] [$r yMin] [$r xMax] [$r yMax]] "\\t"]}}};close $f',
          'read_sdc '+tcl(sdc),'source /OpenROAD-flow-scripts/flow/platforms/nangate45/setRC.tcl','read_spef '+tcl(spef),
          'report_worst_slack -max -digits 6 > '+tcl(out/'setup.txt'),'report_worst_slack -min -digits 6 > '+tcl(out/'hold.txt'),
          'report_parasitic_annotation -report_unannotated > '+tcl(out/'parasitic_coverage.txt'),
          'check_setup -verbose > '+tcl(out/'constraint_coverage.txt'),'write_timing_model '+tcl(out/'timing.lib')]
        script=out/'export.tcl';script.write_text('\n'.join(lines)+'\n');rec['native_export_returncode']=execute(common,script,out/'export.log',threads=4);assert rec['native_export_returncode']==0
        rec['detailed_OBS_view_contract']=verify(out/'abstract.lef',out/'detailed.lef')
        rec['conservative_parent_low_OBS_preparation']=coarsen(out/'detailed.lef',out/'parent_conservative_low.lef')
        norm=lambda line:tuple(x[1:-1] if x.startswith('{') and x.endswith('}') else x for x in line.split())
        assert Counter(norm(s) for s in (out/'pins.tsv').read_text().splitlines()[1:])==Counter(norm(s) for s in pins.read_text().splitlines())
        rec['all_current_signal_and_PG_pin_rows_exact']=True
        rec['SPEF_replay_matches_source']=all((source/(k+'.txt')).read_text()==(out/(k+'.txt')).read_text() for k in ['setup','hold']);assert rec['SPEF_replay_matches_source']
        script=out/'read_model.tcl';script.write_text('read_liberty '+tcl(out/'timing.lib')+'\nset f [open '+tcl(out/'model_pins.tsv')+' w];puts $f "pin\\tdirection";foreach p [get_lib_pins -of_objects [get_lib_cells *]] {puts $f "[get_full_name $p]\\t[get_property $p direction]"};close $f\n')
        rec['fresh_model_read_returncode']=execute(common,script,out/'read_model.log',threads=1);assert rec['fresh_model_read_returncode']==0
        physical=list(csv.DictReader((out/'pins.tsv').open(),delimiter='\t'));expected={p['pin'].replace('\\',''):p['direction'].lower() for p in physical if p['use'] not in ['POWER','GROUND']}
        modelrows=list(csv.DictReader((out/'model_pins.tsv').open(),delimiter='\t'));model={p['pin'].split('/')[-1].replace('\\',''):p['direction'].lower() for p in modelrows};assert len(model)==len(modelrows)
        assert len(expected)==count and {p:d for p,d in model.items() if p in expected}==expected
        pg={p['pin'].replace('\\','') for p in physical if p['use'] in ['POWER','GROUND']}
        for extra in set(model)-set(expected)-pg:
            members=[p for p in expected if re.fullmatch(re.escape(extra)+r'\[\d+\]',p)]
            assert len(members)>1 and all(expected[p]==model[extra] for p in members)
        rec['matching_all_signal_model_pins']=count
    except Exception:rec['actual_failure']=traceback.format_exc();traceback.print_exc()
    rec['all_closed_sources_unchanged']=all(sha(Path(p))==v for p,v in inputs.items());rec['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    rec['files']={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in out.iterdir() if p.is_file() and p.name!='execution.json'};(out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n')
    return int(bool(rec.get('actual_failure')) or not rec['all_closed_sources_unchanged'])
if __name__=='__main__':sys.exit(run(*sys.argv[1:]))
