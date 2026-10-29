"""Reuse complete current-source alias inputs without repeating leaf work."""
from pathlib import Path
import datetime,json,os,sys,traceback
from run_exports import ROOT,sha
from coarsen_parent_low_obs import coarsen
DRIVER=Path(__file__).resolve().parent
def run(revision):
    source=ROOT/'common_integration/deadline-current-r01/C';out=ROOT/'parent_conservative_low_views'/revision;out.mkdir(parents=True,exist_ok=False)
    expected=json.loads((DRIVER/'deadline_current_sources.json').read_text());rec={'scope':'CONSERVATIVE_PARENT_OBS_PREPARATION_NOT_BASE_ROUTE_OR_FREEZE','driver_commit':(DRIVER/'driver_commit.txt').read_text().strip(),'scheduler_job':os.environ['SLURM_JOB_ID'],'full_qualification':False,'source_SHA':{},'cases':{},'provenance':'Complete alias LEF inputs already consumed by active placement/PDN; that job is not claimed closed. Each selected real ODB SHA remains separately pinned; no active input or driver is modified.'}
    try:
        for case,row in expected.items():
            odb=Path(row['source_ODB']);assert sha(odb)==row['ODB_SHA256'];lef=source/('p126_'+case+'.lef');rec['source_SHA'].update({str(odb):sha(odb),str(lef):sha(lef)})
            rec['cases'][case]=coarsen(lef,out/lef.name)
    except Exception:rec['actual_failure']=traceback.format_exc()
    rec['all_sources_unchanged']=all(sha(Path(p))==s for p,s in rec['source_SHA'].items());rec['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();rec['files']={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in out.iterdir() if p.is_file()};(out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n');return int(bool(rec.get('actual_failure')) or not rec['all_sources_unchanged'])
if __name__=='__main__':sys.exit(run(sys.argv[1]))
