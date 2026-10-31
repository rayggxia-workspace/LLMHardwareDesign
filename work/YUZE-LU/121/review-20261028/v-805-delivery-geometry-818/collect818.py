from pathlib import Path
import subprocess,shlex,json,hashlib,base64,tarfile,shutil
q=r'''from pathlib import Path
import json,hashlib,base64,datetime
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121');run=b/'block-v1-20261031-805';t=run/'tasks';paths={};reports={}
names={'final-source':'revision300-final-source.json','physical':'five-macro-physical.json','drc':'five-macro-drc.json','final-function':'five-macro-final-function.json','formal':'five-macro-formal.json','signal-connectivity':'revision300-signal-connectivity.json','delivery':'five-macro-delivery.json','geometry':'five-macro-geometry.json'}
for mode,name in names.items():
 p=t/('revision300-'+mode+'-v');r=json.loads((p/'receipt.json').read_text());assert r['passed']
 paths[str(p/'receipt.json')]=None;paths[str(p/name)]=r['outputs'][name];reports[mode]=json.loads((p/name).read_text())
 if mode in ('final-source','delivery','geometry'):
  for n,h in r['outputs'].items():paths[str(p/n)]=h
index=reports['delivery'];assert index['passed']and index['native_leaf_accepted']and index['implementation_count']==1
assert set(index['final_files'])=={'6_final.v','6_final.sdc','6_final.def','6_final.odb','6_final.gds','6_final.spef'}
for row in index['final_files'].values():paths[row['path']]=row['sha256']
files={};large={}
for name,expected in paths.items():
 p=Path(name);p.resolve().relative_to(run.resolve());h=hashlib.sha256()
 with p.open('rb')as s:
  for chunk in iter(lambda:s.read(1024*1024),b''):h.update(chunk)
 digest=h.hexdigest();assert expected is None or digest==expected
 row=dict(bytes=p.stat().st_size,sha256=digest);key=str(p.relative_to(b))
 if row['bytes']<3000000:row['base64']=base64.b64encode(p.read_bytes()).decode();files[key]=row
 else:large[key]=row
source={v['path']:hashlib.sha256((run/'src'/v['path']).read_bytes()).hexdigest()for v in json.loads((run/'src/bundle-manifest.json').read_text())['files']}
print(json.dumps(dict(captured_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),files=files,actual_server_large=large,actual_remote_source_sha256=source)))'''
d=json.loads(subprocess.check_output(['ssh','-o','BatchMode=yes','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)]))
Path('.local/issue121/capture818-current.json').write_text(json.dumps(d),encoding='utf-8')
data={n:base64.b64decode(row['base64'])for n,row in d['files'].items()}
for n,raw in data.items():assert hashlib.sha256(raw).hexdigest()==d['files'][n]['sha256']and len(raw)==d['files'][n]['bytes']
base='block-v1-20261031-805/tasks/'
def get(mode,name):return data[base+'revision300-'+mode+'-v/'+name]
def report(mode):return json.loads(get(mode,{'final-source':'revision300-final-source.json','signal-connectivity':'revision300-signal-connectivity.json'}.get(mode,'five-macro-'+mode+'.json')))
def digest(mode,name='receipt.json'):return hashlib.sha256(get(mode,name)).hexdigest()
with tarfile.open('.local/issue121/source804.tar')as tar:
 m=json.load(tar.extractfile('bundle-manifest.json'));assert d['actual_remote_source_sha256']=={v['path']:v['sha256']for v in m['files']}
 oids=''.join(v['git_blob']+'\n'for v in m['files']).encode();raw=subprocess.check_output(['git','cat-file','--batch'],input=oids);offset=0
 for row in m['files']:
  end=raw.index(b'\n',offset);fields=raw[offset:end].split();assert fields[0].decode()==row['git_blob']and fields[1]==b'blob';size=int(fields[2]);offset=end+1;assert raw[offset:offset+size]==tar.extractfile(row['path']).read();offset+=size+1
 assert offset==len(raw)
 checked=0
 for n,v in data.items():
  if not n.endswith('/receipt.json'):continue
  r=json.loads(v);assert r['passed']and r['source_commit']==m['source_commit']
  for name,h in r['inputs'].items():
   if '/__pycache__/'not in name:assert hashlib.sha256(tar.extractfile(name).read()).hexdigest()==h
  for name,h in r['outputs'].items():
   key=n.rsplit('/',1)[0]+'/'+name;row=d['files'].get(key,d['actual_server_large'].get(key))
   if row:assert row['sha256']==h;checked+=1
source=digest('final-source');index=report('delivery');g=report('geometry');assert index['source_receipt_sha256']==source
assert source=='9ef42c0fb71fdf9f076f37f4c746631eb1c9e96d0d7b9fae65d7b4d90e425009'
assert set(index['gate_receipts'])=={'physical','drc','final-function','formal'}
assert index['native_routing_layers']==['metal'+str(i)for i in range(1,11)]
for mode,folder in {'physical':'v-805-physical-signal-812','signal-connectivity':'v-805-physical-signal-812','drc':'v-805-drc-final-813','final-function':'v-805-final-function-814','formal':'v-805-final-formal-815'}.items():
 previous=Path('work/YUZE-LU/121/review-20261028')/folder/'block-v1-20261031-805/tasks'/('revision300-'+mode+'-v')/'receipt.json'
 assert hashlib.sha256(previous.read_bytes()).hexdigest()==digest(mode),mode
for mode,row in index['gate_receipts'].items():
 assert row['sha256']==digest(mode);assert row['report_sha256']==hashlib.sha256(get(mode,Path(row['report_path']).name)).hexdigest();assert report(mode)['passed']and report(mode)['source_receipt_sha256']==source
assert report('signal-connectivity')['source_receipt_sha256']==source and report('signal-connectivity')['connectivity']['totals']['nets']==562492
assert g['passed']and g['original_odb_unchanged']and g['native_def_rect_complete']and g['signal_bits']==277
assert g['source_odb_sha256']==index['final_files']['6_final.odb']['sha256']and g['rect_completion']['native_def_sha256']==index['final_files']['6_final.def']['sha256']
assert g['provenance']['delivery_receipt_sha256']==digest('delivery');w=g['provenance']['whole_signal_geometry'];assert w['receipt_sha256']==digest('signal-connectivity')and w['report_sha256']==hashlib.sha256(get('signal-connectivity','revision300-signal-connectivity.json')).hexdigest()
assert not g['abstract_coverage_qualified']and not g['hierarchical_lib_qualified']and not g['m11_m12_system_qualified']
for name,row in index['final_files'].items():
 key=Path(row['path']).relative_to('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121').as_posix();actual=d['files'].get(key,d['actual_server_large'].get(key));assert actual['sha256']==row['sha256']and actual['bytes']==row['bytes']
img=Path(index['image']['path']).name;assert hashlib.sha256(get('delivery',img)).hexdigest()==index['image']['sha256'];assert index['pins']['signal_bits']==277
out=Path('work/YUZE-LU/121/review-20261028/v-805-delivery-geometry-818');target=Path('work/YUZE-LU/121/delivery-300mhz/V');assert not out.exists()and not target.exists();out.mkdir();target.mkdir()
for n,raw in data.items():p=out/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw);d['files'][n].pop('base64')
for mode,name,leaf in [('delivery','five-macro-delivery.json','final-native.json'),('delivery','pins.json','pins.json'),('delivery',img,img),('geometry','five-macro-geometry.json','native-geometry.json'),('geometry','m10-access.json','m10-access.json')]: (target/leaf).write_bytes(get(mode,name))
d.update(passed=True,source_commit=m['source_commit'],archive_git_blobs_verified=len(m['files']),receipt_output_bindings_verified=checked,all_four_gate_same_source=True,whole_signal_geometry_same_source=True,six_final_files_actual_remote_hash_verified=True,image_actually_viewed=False,full_v_accepted=False,scope='Actual805 same-source four gates, six files and full native geometry; image must be viewed and806 complete interfaces/finiteRC verified before overall V acceptance. Candidate LEF/upper system remain unqualified.')
(out/'index.json').write_text(json.dumps(d,indent=2)+'\n',encoding='utf-8',newline='\n');(target/'image-source.json').write_text(json.dumps(dict(**index['image'],delivery_receipt_sha256=digest('delivery'),actually_viewed=False),indent=2)+'\n',encoding='utf-8',newline='\n')
print('Collected818',len(data),'raw',len(d['actual_server_large']),'large; view image next:',target/img)
