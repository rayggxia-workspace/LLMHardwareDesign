from pathlib import Path
import subprocess,sys,time,json,hashlib
home=Path(__file__).resolve().parent;out=home/'control162-r256-watch-280';out.mkdir(exist_ok=True);last=None
for index in range(80):
 rows=[]
 for name in ['control162-latest262.py','control162-r256-upper267.py']:
  try:r=subprocess.check_output([sys.executable,'-X','utf8',str(home/name)],timeout=55).decode('utf-8');rows.append(dict(helper=name,sha256=hashlib.sha256((home/name).read_bytes()).hexdigest(),output=r))
  except (subprocess.CalledProcessError,subprocess.TimeoutExpired)as e:rows.append(dict(helper=name,error=repr(e)))
 state=dict(time=time.time(),rows=rows,whole_system_qualified=False);raw=json.dumps(state,ensure_ascii=True,indent=2);p=out/('status-'+str(time.time_ns())+'.json');p.write_text(raw,encoding='utf-8');digest=hashlib.sha256(json.dumps(rows,sort_keys=True).encode()).hexdigest()
 if digest!=last:
  print(json.dumps(dict(index=index,time=state['time'],path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest())),flush=True)
  for row in rows:print(row.get('output',row.get('error')),flush=True)
 last=digest;time.sleep(45)
