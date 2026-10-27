"""Index only our terminal known-invalid full-C checkpoints; preserve all bytes."""
import datetime,json,os,subprocess
from pathlib import Path
from run_exports import ROOT,sha

driver=Path(__file__).resolve().parent
directory=ROOT/'trials/full-other-r01/llaccel_aux-C'
source=json.loads((directory/'execution.json').read_text());assert source['scheduler_job']=='92369'
action=ROOT/'stage_failure_actions/stop-known-invalid-fixed-PG-92369.json';a=json.loads(action.read_text())
assert a['known_direct_short_pins']==26 and a['other_jobs_untouched']
state=subprocess.check_output(['sacct','-n','-X','-j','92369','--format=State%32']).decode().strip()
assert state.startswith(('CANCELLED','FAILED','COMPLETED')),state
out=ROOT/'failure_checkpoint_index/r01';out.mkdir(parents=True,exist_ok=False)
entries={}
for name in ['moved.odb','ripped.odb','global.odb','moved.pins.tsv','before.pdn.tsv','moved.pdn.tsv','route.guide','congestion.rpt','stages.tsv','openroad.log']:
    p=directory/name
    if not p.exists():continue
    before=p.stat();digest=sha(p);after=p.stat();assert before.st_size==after.st_size and before.st_mtime_ns==after.st_mtime_ns
    entries[name]={'path':str(p),'bytes':before.st_size,'sha256':digest,'mtime_ns':before.st_mtime_ns,'unchanged_during_index':True}
assert set(['moved.odb','ripped.odb','global.odb'])<=set(entries)
record={'case':'llaccel_aux','physical_trial_job':'92369','actual_terminal_scheduler_state':state,'index_job':os.environ['SLURM_JOB_ID'],
 'driver_commit':(driver/'driver_commit.txt').read_text().strip(),'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'source_original_odb_sha256':source['source_sha256'],'stop_action_sha256':sha(action),'full_route_completed':False,'full_physical_qualification':False,
 'scope':'Exact failed-trial checkpoints only; no source/database/job changes. Complete C pin migration and GRT checkpoints are not a completed legal route.',
 'routed_checkpoint_present':(directory/'routed.odb').exists(),'checkpoints':entries}
(out/'index.json').write_text(json.dumps(record,indent=2)+'\n')
print('FAILED_FULL_C_CHECKPOINTS_INDEXED',len(entries),sum(r['bytes'] for r in entries.values()))
