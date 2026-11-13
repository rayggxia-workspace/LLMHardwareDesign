"""Run independent SystemC processes; do not modify parent sources/jobs."""
from concurrent.futures import ThreadPoolExecutor,as_completed
import argparse,json,os,subprocess,time
from pathlib import Path

SIM=['/public/software/singularity-ce-4.3.4/bin/singularity','exec','--cleanenv','--bind','/public/home/yuzelu','/public/home/yuzelu/opt/eda/containers/orfs-26Q1-repacked.sif','./model']
if os.environ.get('BLOCK_STUDY_MODEL'):SIM=[os.environ['BLOCK_STUDY_MODEL']]
elif os.environ.get('BLOCK_STUDY_LOCAL')=='1':SIM=[str(Path('model.exe').resolve())]
CASES=[('prefill2',p) for p in ['packed_k32','local_stream','native32','reference_io','reference_io_w8','reference_io_k256','reference_io_w8_k256','unfused']]
CASES += [('decode512',p) for p in ['packed_k32','native32','reference_io','reference_io_w8','reference_io_k256','reference_io_w8_k256']]
CASES += [(w,'reference_io_w8_k256') for w in ['decode128','decode2048']]
CASES += [(w,p) for w in ['prefill2','decode512'] for p in ['stream_p','stream_p_resident','stream_p_w8','stream_p_w8_resident']]
CASES += [(w,'stream_p_w8_resident') for w in ['decode128','decode2048']]
CASES += [(w,p) for w in ['prefill2','decode512'] for p in ['queued_p_w8','queued_pipe_w8','queued_pipe_w16']]
CASES += [(w,'queued_pipe_w8') for w in ['decode128','decode2048']]

def run(case):
    workload,profile=case;start=time.time()
    p=subprocess.run(SIM+['generated/'+workload+'.trace',profile],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
    text=p.stdout;Path('generated/'+workload+'-'+profile+'.log').write_text(text)
    if p.returncode:raise RuntimeError(str(case)+' exit '+str(p.returncode)+' '+text[-1400:])
    rows=[json.loads(s[7:]) for s in text.splitlines() if s.startswith('RESULT ')]
    if len(rows)!=1:raise RuntimeError('missing result '+str(case))
    r=rows[0];r.update(workload=workload,host_seconds=time.time()-start)
    Path('generated/'+workload+'-'+profile+'.json').write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps(r),flush=True);return r

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--candidate-only',action='store_true');parser.add_argument('--round2',action='store_true');parser.add_argument('--round3',action='store_true');parser.add_argument('--workers',type=int,default=4);args=parser.parse_args()
    cases=[c for c in CASES if c[1] not in ('packed_k32','local_stream','unfused')] if args.candidate_only else CASES
    if args.round2:cases=[c for c in cases if c[1].startswith('stream_p')]
    if args.round3:cases=[c for c in cases if c[1].startswith('queued') or c[1]=='stream_p_resident']
    results=[]
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for f in as_completed([pool.submit(run,c) for c in cases]):results.append(f.result())
    Path('generated/results.json').write_text(json.dumps(results,indent=2)+'\n')
    print('SWEEP_PASS',len(results),flush=True)
