"""Independent complete-cohort controls and checks within a 16-CPU allocation.

Two cases can each run at most two 4-thread OpenROAD instances. Observe actual
kernel memory because this cluster advertises only 1MB in Slurm node metadata.
"""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import datetime,json,os,subprocess,sys
from run_exports import ROOT
DRIVER=Path(__file__).resolve().parent
rev=sys.argv[1];cases=sys.argv[2:];assert 1<=len(cases)<=4 and len(set(cases))==len(cases)
assert int(os.environ['SLURM_CPUS_PER_TASK'])>=16
memory={line.split(':')[0]:int(line.split()[1]) for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith(('MemTotal:','MemAvailable:'))}
workers=2 if memory.get('MemAvailable',0)>=220*1024*1024 else 1
def one(case):
    log=ROOT/'logs'/('control-pack-'+rev+'-'+case+'.log')
    with log.open('x') as f:
        route=subprocess.run(['python3','-B',str(DRIVER/'run_trials.py'),case,rev,'A_replay,Aopt,B'],stdout=f,stderr=subprocess.STDOUT)
        # Continue independent completed controls even if one actual trial fails.
        check=subprocess.run(['python3','-B',str(DRIVER/'run_finalize_clean.py'),case,rev,'A_replay','Aopt','B'],stdout=f,stderr=subprocess.STDOUT)
    print('CONTROL_PACK_FINISHED',case,route.returncode,check.returncode,flush=True)
    return {'case':case,'route_driver_returncode':route.returncode,'independent_check_driver_returncode':check.returncode,
      'qualification':'Read individual native DRC/geometry/STA/electrical receipts; driver completion is not physical qualification'}
with ThreadPoolExecutor(max_workers=workers) as pool:results=list(pool.map(one,cases))
out=ROOT/'trials'/rev
with (out/'pack.json').open('x') as f:json.dump({'scheduler_job':os.environ['SLURM_JOB_ID'],'allocated_cpus':os.environ['SLURM_CPUS_PER_TASK'],
  'actual_meminfo_kB_at_start':memory,'concurrent_cases':workers,'max_OpenROAD_processes':workers*2,'OpenROAD_threads_each':4,
  'finished_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'results':results},f,indent=2)
