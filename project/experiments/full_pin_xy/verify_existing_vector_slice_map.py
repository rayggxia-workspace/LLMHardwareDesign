"""Continue completed mapping, recognizing signal-free Yosys scope metadata.

Do not rerun ABC mapping or delete any Boolean primitive. Fresh functional
models and independent CEC must pass before a physical replacement is allowed.
"""
from pathlib import Path
from collections import Counter
import datetime,hashlib,json,os,re,subprocess,sys,traceback
from run_exports import ROOT,IMAGE,sha
from cell_semantics import groups
from verify_ram_sync_wrapper import YOSYS
DRIVER=Path(__file__).resolve().parent
LIB='/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib'


def run(revision):
    source=ROOT/'vector_critical_cone_remap/r03';rp=source/'execution.json';q=json.loads(rp.read_text())
    assert q.get('completed_utc') and q['native_returncodes']['mapping']==0 and q['all_closed_sources_unchanged']
    assert q['original_selected_cells']==351 and q['cut_inputs']==396 and q['all_cut_outputs']==209
    assert 'AssertionError' in q['actual_failure'] and '$scopeinfo' in q['new_cut_cell_types']
    files=[source/n for n in ['reference.blif','remapped.v','remapped.json','boundary_binding.json.gz','cut.v']]
    for p in files:assert sha(p)==q['files'][p.name]['sha256']
    inputs={str(p):sha(p) for p in files+[rp]};inputs.update(q['source_SHA'])
    assert all(sha(Path(p))==v for p,v in inputs.items())
    out=ROOT/'vector_slice_map_CEC'/revision;out.mkdir(parents=True,exist_ok=False)
    r={'scope':'RELATIVE_BOOLEAN_CEC_OF_ACTUAL_MAPPED351_GATE_SLICE_NOT_PHYSICAL_TIMING_OR_RTL_QUALIFICATION',
       'source_SHA':inputs,'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip(),'scheduler_job':os.environ['SLURM_JOB_ID'],
       'mapping_repeated':False,'actual_source_ODB_edited':False,'native_returncodes':{},'full_qualification':False,
       'original_state_clock_tree_pipeline_ports_and_constraints':'UNCHANGED; physical ECO not installed',
       'physical_route_RC_STA':'NOT_EXECUTED','relative_combinational_equivalence':'NOT_EXECUTED'}
    save=lambda:(out/'execution.json').write_text(json.dumps(r,indent=2)+'\n');save()
    common=['singularity','exec','--cleanenv','--bind',str(ROOT/'tmp')+':/tmp','--home',str(ROOT/'home'),'--pwd',str(out),IMAGE]
    def command(label,args):
        with (out/(label+'.log')).open('x') as f:
            try:r['native_returncodes'][label]=subprocess.call(common+args,stdout=f,stderr=subprocess.STDOUT,timeout=300)
            except subprocess.TimeoutExpired:r['native_returncodes'][label]='TIMEOUT_300s';save();raise
        save();assert r['native_returncodes'][label]==0
    try:
        raw=subprocess.check_output(common+['cat',LIB]);assert hashlib.sha256(raw).hexdigest()=='8d540a4d4cf6d09d27c87ad067857a9c0c2eeb023ab7a56e058cd3113db4e9b1'
        models=dict(groups(raw.decode(),'cell'));mapped=json.loads((source/'remapped.json').read_text())['modules']['hpy_vector_cut']
        metadata={n:c for n,c in mapped['cells'].items() if c['type']=='$scopeinfo'}
        assert len(metadata)==351 and all(not c.get('connections') and not c.get('port_directions') for c in metadata.values())
        hardware={n:c for n,c in mapped['cells'].items() if n not in metadata}
        assert hardware and all(c['type'] in models and not list(groups(models[c['type']],'ff')) and not list(groups(models[c['type']],'latch')) for c in hardware.values())
        r['verified_scope_metadata_cells_no_signal_ports']=len(metadata);r['actual_mapped_hardware_cells']=len(hardware)
        r['actual_mapped_hardware_types']=dict(Counter(c['type'] for c in hardware.values()))
        r['preserved_cut_observation_contract']={'original_selected_cells':351,'arbitrary_boundary_inputs':396,'all_crossing_outputs':209,'original_state_instances_protected':4117}
        save()
        script=['read_liberty -ignore_miss_func '+LIB,'read_verilog '+str(source/'remapped.v'),'hierarchy -check -top hpy_vector_cut','flatten','proc','opt','techmap','opt','clean','write_blif implementation.blif']
        (out/'candidate_to_blif.ys').write_text('\n'.join(script)+'\n');command('fresh_candidate_boolean_model',[YOSYS,'-s','candidate_to_blif.ys'])
        command('independent_combinational_CEC',[YOSYS.rsplit('/',1)[0]+'/yosys-abc','-c','cec '+str(source/'reference.blif')+' implementation.blif'])
        text=(out/'independent_combinational_CEC.log').read_text()
        assert re.search(r'Networks are equivalent',text) and not re.search(r'NOT EQUIVALENT|not equivalent|Error:',text,re.I)
        r['relative_combinational_equivalence']='PASS_ALL209_CROSSING_OUTPUTS_FOR_ARBITRARY396_INPUTS; whole original RTL and physical ECO not qualified'
    except Exception:r['actual_failure']=traceback.format_exc();traceback.print_exc()
    r['all_closed_sources_unchanged']=all(sha(Path(p))==v for p,v in inputs.items());r['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    r['files']={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in out.iterdir() if p.is_file() and p.name!='execution.json'};save()
    return int(bool(r.get('actual_failure')) or not r['all_closed_sources_unchanged'] or not r['relative_combinational_equivalence'].startswith('PASS'))
if __name__=='__main__':sys.exit(run(sys.argv[1]))
