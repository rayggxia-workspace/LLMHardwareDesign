import subprocess,json,time
from pathlib import Path
script=Path(r'D:\Data\电路实验\control162-launch-compile136.py');previous=None
while True:
 result=subprocess.run(['python',str(script)],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 if result.returncode:
  print(result.stdout.decode(errors='replace'),result.stderr.decode(errors='replace'),flush=True);raise SystemExit(result.returncode)
 text=result.stdout.decode().strip();data=json.loads(text)
 if text!=previous:print(text,flush=True);previous=text
 if 'job'in data:break
 assert data.get('ready')is False
 time.sleep(15)
