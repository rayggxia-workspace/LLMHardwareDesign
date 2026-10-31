from pathlib import Path
import subprocess,shlex,json,hashlib,base64,tarfile
out=Path('work/YUZE-LU/121/review-20261028/v-806-interface-821')
assert not out.exists()
q=r'''from pathlib import Path
import json,hashlib,base64,datetime
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121');run=b/'block-v1-20261031-806';p=run/'tasks/revision300-escape-v'
r=json.loads((p/'receipt.json').read_text());files={};large={}
paths=[p/'receipt.json']+[p/n for n in r['outputs']]
for f in dict.fromkeys(paths):
 assert f.is_file();f.resolve().relative_to(run.resolve());h=hashlib.sha256()
 with f.open('rb')as s:
  for chunk in iter(lambda:s.read(1024*1024),b''):h.update(chunk)
 row=dict(bytes=f.stat().st_size,sha256=h.hexdigest());key=str(f.relative_to(b))
 if row['bytes']<3000000:row['base64']=base64.b64encode(f.read_bytes()).decode();files[key]=row
 else:large[key]=row
print(json.dumps(dict(captured_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),files=files,actual_server_large=large)))'''
d=json.loads(subprocess.check_output(['ssh','-o','BatchMode=yes','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)]))
Path('.local/issue121/capture821-current.json').write_text(json.dumps(d),encoding='utf-8')
raw={n:base64.b64decode(r['base64'])for n,r in d['files'].items()}
for n,v in raw.items():assert hashlib.sha256(v).hexdigest()==d['files'][n]['sha256']and len(v)==d['files'][n]['bytes']
prefix='block-v1-20261031-806/tasks/revision300-escape-v/'
r=json.loads(raw[prefix+'receipt.json'])
with tarfile.open('.local/issue121/source804.tar')as tar:
 m=json.load(tar.extractfile('bundle-manifest.json'));assert r['source_commit']==m['source_commit']
 oids=''.join(v['git_blob']+'\n'for v in m['files']).encode();batch=subprocess.check_output(['git','cat-file','--batch'],input=oids);offset=0
 for row in m['files']:
  end=batch.index(b'\n',offset);header=batch[offset:end].split();assert header[0].decode()==row['git_blob']and header[1]==b'blob';size=int(header[2]);offset=end+1;assert batch[offset:offset+size]==tar.extractfile(row['path']).read();offset+=size+1
 assert offset==len(batch)
 for n,h in r['inputs'].items():
  if '/__pycache__/'not in n:assert hashlib.sha256(tar.extractfile(n).read()).hexdigest()==h,n
 for n,h in r['outputs'].items():
  row=d['files'].get(prefix+n,d['actual_server_large'].get(prefix+n));assert row
  if row['sha256']!=h:
   assert n=='node-queue-child.log'and not r['passed'];d.setdefault('post_receipt_failure_log_append',{})[n]=dict(receipt_sha256=h,captured_sha256=row['sha256'])
d.update(actual_interface_passed=r['passed'],source_commit=m['source_commit'],source_git_blobs_verified=len(m['files']),all_inputs_and_stable_outputs_verified=True,full_v_accepted=False)
if r['passed']:
 report=json.loads(raw[prefix+'revision300-escape.json']);joined=json.loads(raw[prefix+'joined-readback.json'])
 native=Path('work/YUZE-LU/121/review-20261028/v-805-delivery-geometry-818/block-v1-20261031-805/tasks')
 gh=hashlib.sha256((native/'revision300-geometry-v/receipt.json').read_bytes()).hexdigest()
 assert report['passed']and report['macro']=='V'and report['all_signal_bits']==report['simultaneous_connected_bits']==277
 assert report['source_geometry_receipt_sha256']==gh
 final=json.loads(Path('work/YUZE-LU/121/delivery-300mhz/V/final-native.json').read_bytes())
 assert report['source_odb_sha256']==final['final_files']['6_final.odb']['sha256']
 assert report['native_original_files_unchanged']and report['three_actual_odb_def_geometry_readbacks']
 assert report['independent_joined_gds']==joined and joined['passed']and all(joined['native_all_mask_xor_zero'].values())and joined['actual_added_native_m10_negative_rejected']
 assert report['negative_controls']['passed']and report['native_m10_obstruction_intersections']==0
 assert not report['combined_300mhz_interface_timing_qualified']and not report['m11_m12_system_qualified']
 d['actual_same805_geometry_bound']=True;d['all277_ports_readbacks_and_native_xor_zero']=True
out.mkdir()
for n,v in raw.items():p=out/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(v);d['files'][n].pop('base64')
(out/'index.json').write_text(json.dumps(d,indent=2)+'\n',encoding='utf-8')
print('Collected821',len(raw),'raw',len(d['actual_server_large']),'large; interface passed',r['passed'])
