"""Strict upper-route join for the same S with overlapping PG computation."""
from pathlib import Path
import subprocess,json,time
home=Path(r'D:\Data\电路实验');last=None;log=home/'control162-watch-upper137.log'
while True:
 result=subprocess.run(['python',str(home/'control162-S-upper-ready137.py')],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 output=result.stdout.decode(errors='replace').strip()
 if result.returncode:
  with log.open('a',encoding='utf-8')as stream:stream.write(str(time.time())+' ERROR '+output+' '+result.stderr.decode(errors='replace')+'\n')
  print('Strict dependency join failed; evidence retained:',str(log),flush=True);raise SystemExit(result.returncode)
 if output!=last:
  with log.open('a',encoding='utf-8')as stream:stream.write(str(time.time())+' '+output+'\n')
  print(output,flush=True);last=output
 if output.startswith('Already appended:'):break
 data=json.loads(output)
 if data.get('ready')is True:
  assert data['appended']==28;break
 assert data.get('ready')is False
 time.sleep(45)
