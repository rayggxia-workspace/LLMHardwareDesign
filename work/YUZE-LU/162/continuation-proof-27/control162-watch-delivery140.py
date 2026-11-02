"""Actual-receipt-only collectors and exact-own superseded compile priority."""
from pathlib import Path
import subprocess,time,sys,json
home=Path(r'D:\Data\电路实验');repo=home/'LLMHardwareDesign-worktrees/issue-162-control'
log=home/'control162-watch-delivery140.log'
with log.open('x',encoding='utf-8',buffering=1)as stream:
 while True:
  for name in ['control162-block-ready140.py','control162-system-ready140.py']:
   if name.startswith('control162-block')and(repo/'work/YUZE-LU/162/block-delivery-ready140/index.json').exists():continue
   if name.startswith('control162-system')and not(repo/'work/YUZE-LU/162/block-delivery-ready140/index.json').exists():continue
   if name.startswith('control162-system')and(repo/'work/YUZE-LU/162/system-delivery-ready140/index.json').exists():print('Actual joint delivery collected',flush=True);raise SystemExit(0)
   result=subprocess.run([sys.executable,str(home/name)],capture_output=True,text=True,encoding='utf-8',errors='replace')
   stream.write(json.dumps(dict(time=time.time(),helper=name,returncode=result.returncode,stdout=result.stdout,stderr=result.stderr),ensure_ascii=False)+'\n')
   if result.returncode:print('Collector/prioritizer failure; preserved all evidence; inspect '+str(log),flush=True);raise SystemExit(result.returncode)
  time.sleep(45)
