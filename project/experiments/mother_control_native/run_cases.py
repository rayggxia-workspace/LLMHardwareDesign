"""Slurm worker: actual native64 mother/PM, bounded finite peers."""
import argparse,hashlib,json,os,subprocess
from pathlib import Path
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,required=True);parser.add_argument('--seed',type=int,required=True);args=parser.parse_args()
    root=args.root.resolve();rows=[]
    runtime='/public/software/singularity-ce-4.3.4/bin/singularity'
    image='/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif'
    for initial in (0,1,2):
        for case in json.loads((root/'images/cases.json').read_text()):
            if os.getenv('MC_CASE_FILTER') and case['name'] not in os.environ['MC_CASE_FILTER'].split(','):continue
            name=f"{case['name']}-{args.seed}-{initial}"
            cmd=[runtime,'exec','--cleanenv','--bind','/public/home/yuzelu',image,str(root/'build/Vtb_mc_native'),
                 '+IMAGE='+case['image'],f'+verilator+seed+{args.seed}',f'+verilator+rand+reset+{initial}']
            cmd+=['+'+key+'='+str(value) for key,value in case.items() if key not in ('name','image')]
            if case.get('TIMING',0):cmd+=['+TIMING_TRACE='+str(root/'results'/(name+'.csv'))]
            path=root/'results'/(name+'.log')
            with path.open('w') as log:
                result=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT)
            passed=result.returncode==0 and 'PASS mother' in path.read_text()
            rows.append(dict(case=case['name'],seed=args.seed,reset_initial=initial,passed=passed,returncode=result.returncode,
                             log=path.name,log_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                             image_sha256=hashlib.sha256(Path(case['image']).read_bytes()).hexdigest()))
            if not passed:
                print('FAIL',name,flush=True)
    (root/'results'/f'worker-{args.seed}.json').write_text(json.dumps({'Slurm_job':os.getenv('SLURM_JOB_ID'),'passed':all(row['passed'] for row in rows),'results':rows},indent=2)+'\n')
    if not all(row['passed'] for row in rows):raise SystemExit(1)
    print('PASS native mother worker',args.seed,len(rows),flush=True)
if __name__=='__main__':main()
