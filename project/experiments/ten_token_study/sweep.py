"""Explicit resource-budget study; no parameter is treated as existing hardware."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import argparse, hashlib, json, os, subprocess, time

PROFILE='gap_dma_partial_coalesce_sched_k256'
DESIGNS={
 'prior17':{},
 'batch17':{'batch_exp':1},
 'bw34_only':{'bw':34.2,'batch_exp':1},
 'b68_p2_m2_e8':{'bw':68.4,'beat':128,'swidth':128,'pcount':2,'mscale':2,'elanes':8,'batch_exp':1},
 'b68_p3_m2_e8':{'bw':68.4,'beat':128,'swidth':128,'pcount':3,'mscale':2,'elanes':8,'batch_exp':1},
 'b68_p3_m4_e8':{'bw':68.4,'beat':128,'swidth':128,'pcount':3,'mscale':4,'elanes':8,'batch_exp':1},
 'b68_p3_m4_e16':{'bw':68.4,'beat':128,'swidth':128,'pcount':3,'mscale':4,'elanes':16,'batch_exp':1},
 'b136_p3_m4_e8':{'bw':136.8,'beat':256,'swidth':256,'pcount':3,'mscale':4,'elanes':8,'batch_exp':1},
 'b136_p3_m4_e8_w16':{'bw':136.8,'beat':256,'swidth':256,'pcount':3,'mscale':4,'elanes':8,'batch_exp':1,'weight_bits':16},
 'b136_p3_m8_e8_w16':{'bw':136.8,'beat':256,'swidth':256,'pcount':3,'mscale':8,'elanes':8,'batch_exp':1,'weight_bits':16},
 'fixed17_w4_head8':{'pcount':3,'mscale':2,'elanes':8,'batch_exp':1,'weight_bits':4,'head8':1},
 'fixed17_w4':{'pcount':3,'mscale':2,'elanes':8,'batch_exp':1,'weight_bits':4},
 'fixed17_w2_head8':{'pcount':3,'mscale':2,'elanes':8,'batch_exp':1,'weight_bits':2,'head8':1},
 'b68_balanced_m2_e8':{'bw':68.4,'beat':128,'swidth':128,'pcount':3,'mscale':2,'elanes':8,'batch_exp':1,'channel_balance':1},
 'b68_balanced_m4_e8':{'bw':68.4,'beat':128,'swidth':128,'pcount':3,'mscale':4,'elanes':8,'batch_exp':1,'channel_balance':1},
 'b136_balanced_m4_e8_w16':{'bw':136.8,'beat':256,'swidth':256,'pcount':3,'mscale':4,'elanes':8,'batch_exp':1,'channel_balance':1,'weight_bits':16},
 'b85_balanced_m2_e8':{'bw':85.5,'beat':256,'swidth':128,'pcount':3,'mscale':2,'elanes':8,'batch_exp':1,'channel_balance':1},
 'b85_p3_m2_e8':{'bw':85.5,'beat':256,'swidth':128,'pcount':3,'mscale':2,'elanes':8,'batch_exp':1},
 'b85_p3_m4_e8':{'bw':85.5,'beat':256,'swidth':128,'pcount':3,'mscale':4,'elanes':8,'batch_exp':1},
 'b102_p2_m2_e8':{'bw':102.4,'beat':256,'swidth':128,'pcount':2,'mscale':2,'elanes':8,'batch_exp':1},
 'b102_p3_m2_e8':{'bw':102.4,'beat':256,'swidth':128,'pcount':3,'mscale':2,'elanes':8,'batch_exp':1},
}
# All resource candidates now use the independently testable byte-plane M
# ABI. Preserve prior17 as the explicitly historical abstraction.
for name, cfg in DESIGNS.items():
 if name!='prior17':cfg['byte_m']=1
def run(case):
 workload,design=case;cfg=DESIGNS[design];start=time.monotonic()
 exe=Path(os.environ.get('TEN_TOKEN_MODEL','model.exe')).resolve()
 command=[str(exe),str(Path('generated',workload+'.trace')),PROFILE]+[f'{k}={v}' for k,v in cfg.items()]
 launch_errors=[]
 for attempt in range(4):
  try:r=subprocess.run(command,capture_output=True,text=True);break
  except PermissionError as exc:
   launch_errors.append(str(exc))
   if attempt==3:raise
   time.sleep(1)
 log=Path('generated',workload+'-'+design+'.log');log.write_text(r.stdout+r.stderr)
 if r.returncode:raise RuntimeError((case,r.stdout,r.stderr))
 d=json.loads(next(x[7:] for x in r.stdout.splitlines() if x.startswith('RESULT ')))
 d.update(workload=workload,design=design,overrides=cfg,command=command,host_seconds=time.monotonic()-start,
          numeric_qualification=False,physical_qualification=False,launch_errors=launch_errors)
 Path('generated',workload+'-'+design+'.json').write_text(json.dumps(d,indent=2)+'\n')
 print(workload,design,d['tokens_per_second'],flush=True);return d

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--workload',default='decode512');p.add_argument('--workers',type=int,default=3)
 p.add_argument('--designs',nargs='*');p.add_argument('--output',default='sweep.json');a=p.parse_args()
 cases=[(a.workload,d) for d in (a.designs or list(DESIGNS))]
 with ThreadPoolExecutor(max_workers=a.workers) as pool:results=list(pool.map(run,cases))
 Path('generated',a.output).write_text(json.dumps(results,indent=2)+'\n')
 print('SWEEP_PASS',len(results))
