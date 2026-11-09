"""Independent traffic/budget audit and adversarial ACK/cache-line tests."""
from pathlib import Path
import argparse, hashlib, json, math, os, subprocess

PROFILE='gap_dma_partial_coalesce_sched_k256'

def graph(path):
 lines=path.read_text().splitlines();nt,no,tokens=map(int,lines[0].split())
 tensors=[tuple(map(int,x.split())) for x in lines[1:1+nt]];ops=[]
 for line in lines[1+nt:]:
  x=line.split();ops.append(dict(kind=x[1],r=int(x[3]),n=int(x[4]),k=int(x[5]),batches=int(x[6]),layout=int(x[8]),inputs=list(map(int,x[10:]))))
 assert len(ops)==no
 return tensors,ops,tokens

def audit(r):
 ts,ops,tokens=graph(Path('generated',r['workload']+'.trace'));cfg=r['overrides']
 weights=macs=0
 for o in ops:
  if o['kind']!='Dot':continue
  macs+=o['batches']*o['r']*o['n']*o['k']
  if o['layout']==0:
   bits=8 if cfg.get('head8') and o['n']==151936 else cfg.get('weight_bits',8)
   weights+=o['batches']*math.ceil(o['r']/8)*math.ceil(o['n']*o['k']*bits/8)
 assert r['logical_read_bytes']>=weights
 assert r['read_bus_bytes']>=r['logical_read_bytes'] and r['write_bus_bytes']>=r['logical_write_bytes']
 assert r['channel0_bytes']+r['channel1_bytes']==r['read_bus_bytes']+r['write_bus_bytes']
 assert r['P_scratch_peak_bytes']<=cfg.get('pbytes',16384) and r['U_cache_peak_bytes']+4096<=16384
 assert r['max_outstanding_beats']<=32 and r['max_outstanding_descriptors']<=32
 assert r['KV_state_write_bytes']==(73728 if r['workload'].startswith('decode') else 0)
 assert abs(r['seconds']-r['ticks']/300e6)<1/300e6+1e-10
 assert abs(r['tokens_per_second']*r['seconds']-tokens)<1e-8
 assert abs(sum(r['spans_ticks'].values())-r['ticks'])<=len(r['spans_ticks'])
 bw=cfg.get('bw',17.1)*1e9
 assert max(r['channel0_bytes'],r['channel1_bytes'])<=r['seconds']*bw/2+512
 return dict(workload=r['workload'],design=r['design'],matrix_MACs=macs,static_weight_bytes_minimum=weights)

def adversarial():
 exe=str(Path(os.environ.get('TEN_TOKEN_MODEL','model.exe')).resolve());checks=0
 def run(name,trace,options=(),error=None):
  nonlocal checks
  path=Path('generated/check-'+name+'.trace');path.write_text(trace)
  r=subprocess.run([exe,str(path),PROFILE,*options],capture_output=True,text=True)
  Path('generated/check-'+name+'.log').write_text(r.stdout+r.stderr)
  if error:assert r.returncode and error in r.stdout+r.stderr,(name,r.stdout,r.stderr)
  else:assert not r.returncode,(name,r.stdout,r.stderr)
  checks+=1
  return r
 # A dirty produced line supplies several N packets. Releasing it after the
 # first packet must fail the later read: this catches the discarded-line bug.
 for bits in [16,32]:
  for n in [1,7,8,9,17,33,129]:
   trace=f'3 2 1\n0 {n} {bits} 1\n1 {n} {bits} 0\n2 {n} 32 0\n1 Convert {n} 1 {n} 1 1 0 0 1 0\n2 NExp {n} 1 {n} 1 1 0 0 1 1\n'
   run(f'nexp-{bits}-{n}',trace,['batch_exp=1','byte_m=1'])
 # Uneven N ownership, split final row and a long accumulation. Runtime
 # coverage rejects duplicate/missing outputs and requires actual write ACKs.
 for rows,n,k in [(1,1,1),(1,9,13),(2,17,128),(9,24,129),(9,49,1025)]:
  trace=f'3 1 {rows*n}\n0 {rows*k} 32 1\n1 {k*n} 16 1\n2 {rows*n} 32 0\n2 Dot {rows*n} {rows} {n} {k} 1 16 0 2 0 1\n'
  for bits in [2,4,8,16]:
   for balanced in [0,1]:
    run(f'matrix-{rows}-{n}-{k}-w{bits}-b{balanced}',trace,[f'weight_bits={bits}','pcount=3',f'channel_balance={balanced}','byte_m=1','mscale=2'])
 missing='2 1 1\n0 4 32 0\n1 4 32 0\n1 Convert 4 1 4 1 1 0 0 1 0\n'
 run('missing-ack',missing,error='read before producer write/ACK')
 tiny='3 1 1\n0 1 32 1\n1 1 16 1\n2 1 32 0\n2 Dot 1 1 1 1 1 0 0 2 0 1\n'
 for option in ['mscale=3','pcount=4','swidth=96','weight_bits=3','bw=nan','beat=12']:
  run('invalid-'+option.replace('=','-'),tiny,[option],error='CONFIG_FAILURE')
 return checks

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--results',nargs='+',required=True);a=p.parse_args()
 rows=[]
 for file in a.results:
  for r in json.loads(Path('generated',file).read_text()):rows.append(audit(r))
 report=dict(scope=__doc__,work_audits=rows,adversarial_checks=adversarial(),
  model_sha256=hashlib.sha256(Path('model.cpp').read_bytes()).hexdigest(),
  numerical_whole_model_qualification=False,physical_qualification=False)
 Path('generated/candidate-audit.json').write_text(json.dumps(report,indent=2)+'\n')
 print('CANDIDATE_AUDIT_PASS',len(rows),report['adversarial_checks'])
