"""Pack four independent four-thread KLayout checks into one 16-CPU job."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import json,os,subprocess,sys
from run_exports import ROOT
DRIVER=Path(__file__).resolve().parent
revision=sys.argv[1];cases=sys.argv[2:]
assert len(cases)<=4 and len(set(cases))==len(cases)
assert int(os.environ['SLURM_CPUS_PER_TASK'])>=4*len(cases)
def one(case):
    with (ROOT/'logs'/('stream-pack-'+revision+'-'+case+'.log')).open('x') as f:
        result=subprocess.run(['python3','-B',str(DRIVER/'run_streamout_probe.py'),revision,case],stdout=f,stderr=subprocess.STDOUT)
    print('PACKED_STREAM_FINISHED',case,result.returncode,flush=True)
    return {'case':case,'driver_returncode':result.returncode,'physical_status':'Read actual merge/DRC receipts; process completion is not a pass'}
with ThreadPoolExecutor(max_workers=len(cases)) as pool:results=list(pool.map(one,cases))
out=ROOT/'streamout'/revision
with (out/'pack.json').open('x') as f:json.dump({'scheduler_job':os.environ['SLURM_JOB_ID'],'allocated_cpus':os.environ['SLURM_CPUS_PER_TASK'],'per_KLayout_DRC_threads':4,'results':results},f,indent=2)
sys.exit(0 if all(r['driver_returncode']==0 for r in results) else 1)
