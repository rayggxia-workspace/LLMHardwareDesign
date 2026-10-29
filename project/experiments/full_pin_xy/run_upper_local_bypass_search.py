"""Source-bound local M11/M12 bypass search; native implementation not claimed."""
from pathlib import Path
import datetime,json,os,sys,traceback
from run_exports import ROOT,sha
from plan_upper_local_bypass import plan
DRIVER=Path(__file__).resolve().parent

def run(revision):
    source=ROOT/'upper_branch_repair/r02/llaccel';rp=source/'execution.json';q=json.loads(rp.read_text())
    assert q.get('completed_utc') and q['all_closed_sources_unchanged'] and q['fresh_DRC_count']==2
    branches=source/'branch_access.tsv.gz';obs=source/'after_branch.OBS.tsv'
    for p in [branches,obs]:assert sha(p)==q['files'][p.name]['sha256']
    inputs={str(p):sha(p) for p in [rp,branches,obs]}
    out=ROOT/'upper_local_bypass_search'/revision;out.mkdir(parents=True,exist_ok=False)
    rec={'scope':'ACTUAL_CLOSED_TWO_SHORT_SOURCE_GEOMETRIC_SEARCH_NOT_NATIVE_IMPLEMENTATION_OR_SYSTEM','source_SHA':inputs,'full_qualification':False,'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip(),'scheduler_job':os.environ['SLURM_JOB_ID'],'source_mode':'llaccel','source_native_DRC_count':2,'native_edit_route_DRC_RC_STA':'NOT_EXECUTED','fixed_M10_and_hook_changes_requested':0}
    try:rec['geometric_result']=plan(branches,obs,out/'proposed_bypass_NOT_IMPLEMENTED.json')
    except Exception:rec['actual_failure']=traceback.format_exc()
    rec['all_closed_sources_unchanged']=all(sha(Path(p))==s for p,s in inputs.items())
    rec['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    rec['files']={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in out.iterdir() if p.is_file()}
    (out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n')
    return 0 if not rec.get('actual_failure') and rec['all_closed_sources_unchanged'] and rec.get('geometric_result',{}).get('status')=='PROPOSED_LOCAL_BYPASSES_NATIVE_IMPLEMENTATION_REQUIRED' else 1
if __name__=='__main__':sys.exit(run(sys.argv[1]))
