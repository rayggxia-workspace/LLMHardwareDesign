"""Native parent-view access check on immutable imported checkpoint.

Leaf AP success does not imply access through exported macro obstructions.
Probe the actual common parent independently while its routing job proceeds.
"""
from pathlib import Path
import csv,datetime,json,os,re,sys,traceback
from run_exports import ROOT,sha
from run_parent_trial import tcl
from run_escape_fixture import execute
DRIVER=Path(__file__).resolve().parent


def run(revision):
    source=ROOT/'common_checkpoint_def_import/corner-r01';q=json.loads((source/'execution.json').read_text())
    assert q['native_returncodes']['fresh_import']==0
    stages={r['stage']:r['status'] for r in csv.DictReader((source/'fresh_import.stages.tsv').open(),delimiter='\t')}
    assert all(stages.get(k)=='EXECUTED' for k in ['import_exact_checkpoint','VDD','VSS'])
    odb=source/'imported_current_NOT_ROUTED_NOT_FROZEN.odb'
    graph=source/'all_original_graph_check.json';assert graph.exists()
    out=ROOT/'current_common_pin_access'/revision;out.mkdir(parents=True,exist_ok=False)
    # The routing receipt is deliberately still mutable; archive its observed
    # content, but bind assertions only to completed immutable phase outputs.
    (out/'observed_ongoing_parent_receipt.json').write_text(json.dumps(q,indent=2)+'\n')
    inputs={str(p):sha(p) for p in [odb,graph,source/'after.pins.tsv',source/'after.instances.tsv',source/'after.shared.tsv']}
    r={'scope':'ACTUAL_IMPORTED_COMMON_PARENT_NATIVE_PIN_ACCESS_NOT_ROUTE_OR_FUNCTION_QUALIFICATION',
       'source_SHA':inputs,'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip(),'scheduler_job':os.environ['SLURM_JOB_ID'],
       'ongoing_source_receipt_is_observation_not_immutable_input':True,'actual_geometry_or_constraint_modification':False,
       'full_qualification':False,'all24767_leaf_signal_pins':'Actual same common parent master geometry, not detached leaf geometry',
       'routing_layers':'signal M2-M10; clock M4-M10 unchanged'}
    try:
        script=out/'check.tcl';script.write_text('read_db '+tcl(odb)+'\nset_routing_layers -signal metal2-metal10 -clock metal4-metal10\npin_access\n')
        common=['singularity','exec','--cleanenv','--bind',str(ROOT/'tmp')+':/tmp','--home',str(ROOT/'home'),'--pwd',str(out)]
        r['native_returncode']=execute(common,script,out/'native.log',threads=4)
        text=(out/'native.log').read_text();r['native_no_access_counters']={k:int(v) for k,v in re.findall(r'^#(\w*NoAp)\s*=\s*(\d+)',text,re.M)}
        r['exact_error_lines']=[s for s in text.splitlines() if '[ERROR ' in s or 'No access point' in s]
        r['native_AP_pass']=r['native_returncode']==0 and bool(r['native_no_access_counters']) and not any(r['native_no_access_counters'].values())
    except Exception:r['actual_failure']=traceback.format_exc();traceback.print_exc()
    r['all_immutable_phase_sources_unchanged']=all(sha(Path(p))==v for p,v in inputs.items());r['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    r['files']={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in out.iterdir() if p.is_file() and p.name!='execution.json'}
    (out/'execution.json').write_text(json.dumps(r,indent=2)+'\n')
    return int(bool(r.get('actual_failure')) or not r.get('native_AP_pass') or not r['all_immutable_phase_sources_unchanged'])
if __name__=='__main__':sys.exit(run(sys.argv[1]))
