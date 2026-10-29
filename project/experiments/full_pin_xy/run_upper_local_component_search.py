"""Source-bound local route-component repair preparation; native gate follows."""
from pathlib import Path
import datetime,json,os,sys,traceback
from run_exports import ROOT,sha
from plan_upper_local_components import plan
DRIVER=Path(__file__).resolve().parent
def run(revision):
    source=ROOT/'upper_branch_repair/r02/llaccel';rp=source/'execution.json';q=json.loads(rp.read_text());assert q.get('completed_utc') and q['fresh_DRC_count']==2 and q['all_closed_sources_unchanged']
    proof=ROOT/'upper_cut_corner_probe/r03/execution.json';pq=json.loads(proof.read_text());assert pq['native_controls_prove_corner_square_test_was_overconservative'] and pq['all_sources_unchanged']
    paths=[source/n for n in ['branch_access.tsv.gz','after_branch.OBS.tsv','before_route.die.tsv']]
    for p in paths:assert sha(p)==q['files'][p.name]['sha256']
    inputs={str(p):sha(p) for p in [rp,proof]+paths};out=ROOT/'upper_local_component_search'/revision;out.mkdir(parents=True,exist_ok=False)
    rec={'scope':'CLOSED_REAL_SOURCE_LOCAL_COMPONENT_SEARCH_NOT_PHYSICAL_REPAIR','source_SHA':inputs,'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip(),'scheduler_job':os.environ['SLURM_JOB_ID'],'full_qualification':False,'native_implementation_DRC_RC_STA':'NOT_EXECUTED'}
    try:rec['geometric_result']=plan(*paths,out/'local_components_NOT_IMPLEMENTED.json')
    except Exception:rec['actual_failure']=traceback.format_exc()
    rec['all_closed_sources_unchanged']=all(sha(Path(p))==s for p,s in inputs.items());rec['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();rec['files']={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in out.iterdir() if p.is_file()};(out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n');return int(bool(rec.get('actual_failure')) or not rec.get('geometric_result',{}).get('solution'))
if __name__=='__main__':sys.exit(run(sys.argv[1]))
