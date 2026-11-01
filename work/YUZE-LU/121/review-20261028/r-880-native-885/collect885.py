from pathlib import Path
import base64,hashlib,json,shlex,subprocess,tarfile
q=r'''from pathlib import Path
import base64,hashlib,json,datetime,subprocess,sys,re
from collections import Counter
r=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/block-v1-20261101-880')
sacct=subprocess.check_output(['sacct','-X','-j','94498','-n','-P','--format=JobIDRaw,State,ExitCode,Elapsed,NodeList'],universal_newlines=True);assert any('94498|'+v in sacct for v in ['RUNNING|','FAILED|1:0|','COMPLETED|0:0|'])
files={};large={};summary=[];failures=[]
def violations(t):return Counter(re.sub(r'\s+',' ',v).strip()for v in re.findall(r'violation type:.*?(?=violation type:|\Z)',t,re.S))
old=violations((r.parent/'block-v1-20261101-851/tasks/revision300-r-current-neighborhood/native-whole-drc.rpt').read_text())
for s,mode in enumerate(['revision300-r-composed-vias']+['revision300-r-ns-wide-'+str(i)for i in range(6)]):
 p=r/'tasks'/mode;receipt=json.loads((p/'receipt.json').read_text())
 reportname='revision300-r-composed-vias.json'if mode=='revision300-r-composed-vias'else'revision300-r-clearance-corners.json'
 d=json.loads((p/reportname).read_text());d['actual_mode']=mode;summary.append(d)
 assert d['passed']==receipt['passed']and d['original_inputs_unchanged']and(d.get('exact_expected_rectangles_and_nonrect_net_routes')or d.get('exact_normal_net_header_path_rect_and_nonnet_delta'))
 for n in ['receipt.json']+list(receipt['outputs']):
  f=p/n;h=hashlib.sha256()
  with f.open('rb')as stream:
   for v in iter(lambda:stream.read(1024*1024),b''):h.update(v)
  row=dict(bytes=f.stat().st_size,sha256=h.hexdigest());name=str(f.relative_to(r))
  if row['bytes']<3000000:row['base64']=base64.b64encode(f.read_bytes()).decode();files[name]=row
  else:large[name]=row
 baseline=violations((r.parent/'block-v1-20261101-866/tasks/revision300-r-corner-compose/corner-native-drc.rpt').read_text())if mode=='revision300-r-composed-vias'else old
 added=violations((p/('composed-native-drc.rpt'if mode=='revision300-r-composed-vias'else'corner-native-drc.rpt')).read_text())-baseline
 assert sum(added.values())==d['added_markers']
 failures.append(dict(shard=s,added=list(added.elements())))
print(json.dumps(dict(captured_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),files=files,actual_server_large=large,sacct=sacct,summary=summary,actual_added_markers=failures)))'''
d=json.loads(Path('.local/issue121/885-actual-capture.json').read_bytes())if Path('.local/issue121/885-actual-capture.json').exists()else json.loads(subprocess.check_output(['ssh','-o','BatchMode=yes','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)]))
Path('.local/issue121/885-actual-capture.json').write_bytes(json.dumps(d).encode())
raw={n:base64.b64decode(row['base64'])for n,row in d['files'].items()}
for n,v in raw.items():assert len(v)==d['files'][n]['bytes']and hashlib.sha256(v).hexdigest()==d['files'][n]['sha256']
mutable=[]
with tarfile.open('.local/issue121/source880.tar')as tar:
 for s,mode in enumerate(['revision300-r-composed-vias']+['revision300-r-ns-wide-'+str(i)for i in range(6)]):
  prefix='tasks/'+mode+'/'
  r=json.loads(raw[prefix+'receipt.json']);assert r['source_commit']=='4728365de856d8e99effb8b18f4849036346af33'
  for n,h in r['inputs'].items():
   if '/__pycache__/'not in n:assert hashlib.sha256(tar.extractfile(n).read()).hexdigest()==h
  for n,h in r['outputs'].items():
   actual=d['files'].get(prefix+n,d['actual_server_large'].get(prefix+n))['sha256']
   if n=='node-queue-child.log'and actual!=h:
    assert not r['passed'];mutable.append(dict(shard=s,name=n,receipt_sha256=h,actual_terminal_sha256=actual,reason='Python traceback flushed after finally wrote receipt; terminal raw preserved. Stable EDA outputs all exact.'))
   else:assert actual==h,(s,n,h,actual)
out=Path('work/YUZE-LU/121/review-20261028/r-880-native-885');assert not out.exists();out.mkdir()
for n,v in raw.items():
 p=out/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(v);d['files'][n].pop('base64')
d.update(all_inputs_and_stable_outputs_verified=True,mutable_terminal_logs=mutable,source_proof='../r-880-repair-stage-884/index.json',physical_acceptance=False)
(out/'index.json').write_bytes((json.dumps(d,indent=2)+'\n').encode())
for s in d['summary']:print({k:s[k]for k in ('actual_mode','passed','candidate_native_count','added_markers','removed_markers')})
print('added',d['actual_added_markers']);print('885',len(raw),'raw',len(d['actual_server_large']),'large',d['sacct'])
