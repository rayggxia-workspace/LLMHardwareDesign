from pathlib import Path
import base64,hashlib,json,subprocess,shlex,tarfile
q=r'''from pathlib import Path
import json,base64,hashlib,subprocess,datetime
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121');r=b/'block-v1-20261101-827';p=r/'tasks/revision300-route-r'
receipt=json.loads((p/'receipt.json').read_text());flow=json.loads((p/'revision300-native-flow.json').read_text())
archive=hashlib.sha256((r/'source.tar').read_bytes()).hexdigest()
assert archive=='3c40abeef7c73bce224652d8ba7c0060576394f0bf4a6152bd4fe25c065380f1'
assert json.loads((r/'node-queue-state.json').read_text())['tasks']['revision300-route-r']['status']=='PASSED'
assert flow['rtl_sha256']=={'project/rtl/block_library_v1/block_v1_r.sv':'634f7f7793ced998423a59d4f744c45191c3c7e02f37cebf1b1f183563a7560b'}
sacct=subprocess.check_output(['sacct','-X','-n','-P','-j','94320','--format=JobIDRaw,State,ExitCode,NodeList'],universal_newlines=True)
assert '94320|COMPLETED|0:0|' in sacct, sacct
assert receipt['passed'] and flow['passed'] and flow['pipeline_completed']
assert flow['stages']==['do-1_synth','do-floorplan','do-place','do-cts','do-route','do-finish']
assert flow['inherited_physical_stages']==[] and not flow['qualified_hard_macro']
assert flow['source_mapping_task']=='block-v1-20261101-826/tasks/revision300-map-r'
assert flow['source_function_task']=='block-v1-20261101-826/tasks/revision300-test-r'
for kind in ('mapping','function'):
 dependency=b/flow['source_'+kind+'_task']/'receipt.json'
 assert hashlib.sha256(dependency.read_bytes()).hexdigest()==flow['source_'+kind+'_receipt_sha256']
assert set(flow['final_files'])=={'6_final.'+suffix for suffix in ('v','sdc','def','odb','spef')}
changed={}
paths=[r/n for n in('manifest.json','node-queue.json','dispatch-state.json','node-queue-state.json','stage-identity-proof.json')]
paths +=[r/'tasks/native-node-queue'/n for n in('image.sha256','queue-live.json')]
paths +=[p/n for n in receipt['outputs']]+[p/'receipt.json']
files={};large={};actual={}
for f in paths:
 h=hashlib.sha256()
 with f.open('rb')as stream:
  for chunk in iter(lambda:stream.read(1024*1024),b''):h.update(chunk)
 digest=h.hexdigest();row=dict(sha256=digest,bytes=f.stat().st_size);name=str(f.relative_to(b))
 if p in f.parents and f.name!='receipt.json':
  original=receipt['outputs'][str(f.relative_to(p))]
  if original!=digest:
   assert str(f.relative_to(p))=='node-queue-child.log'
   changed[name]=dict(receipt_sha256=original,captured_sha256=digest,scope='Post-receipt queue child log; no qualification output waiver')
 if row['bytes']>3000000:large[name]=row
 else:row['base64']=base64.b64encode(f.read_bytes()).decode();files[name]=row
 actual[name]=digest
for name,row in flow['final_files'].items():
 final=Path(row['path']);assert p in final.parents and final.name==name
 assert actual[str(final.relative_to(b))]==row['sha256'] and final.stat().st_size==row['bytes']
source={v['path']:hashlib.sha256((r/'src'/v['path']).read_bytes()).hexdigest()for v in json.loads((r/'src/bundle-manifest.json').read_text())['files']}
controller=b/'admission-20261101-830';status=json.loads((controller/'status.json').read_text())
print(json.dumps(dict(captured_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),files=files,server_only=large,all_receipt_outputs_actual_verified=len(receipt['outputs']),actual_remote_archive_sha256=archive,actual_remote_source_sha256=source,actual_final_files=flow['final_files'],controller_status=status,post_receipt_log_appends=changed,sacct=sacct)))'''
d=json.loads(subprocess.check_output(['ssh','-o','BatchMode=yes','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)]))
dest=Path('work/YUZE-LU/121/review-20261028/r-827-native-835');assert not dest.exists();raw_files={}
for name,row in d['files'].items():
 raw=base64.b64decode(row.pop('base64'));assert hashlib.sha256(raw).hexdigest()==row['sha256'] and len(raw)==row['bytes'];raw_files[name]=raw
with tarfile.open('.local/issue121/source827.tar')as tar:
 m=json.load(tar.extractfile('bundle-manifest.json'));assert hashlib.sha256(Path('.local/issue121/source827.tar').read_bytes()).hexdigest()=='3c40abeef7c73bce224652d8ba7c0060576394f0bf4a6152bd4fe25c065380f1';assert d['actual_remote_source_sha256']=={v['path']:v['sha256']for v in m['files']}
 oids=[v['git_blob']for v in m['files']];raw=subprocess.check_output(['git','cat-file','--batch'],input=''.join(v+'\n'for v in oids).encode());offset=0
 for row in m['files']:
  end=raw.index(b'\n',offset);fields=raw[offset:end].split();assert fields[0].decode()==row['git_blob']and fields[1]==b'blob';size=int(fields[2]);offset=end+1
  assert raw[offset:offset+size]==tar.extractfile(row['path']).read();offset+=size+1
 assert offset==len(raw)
 r=json.loads(raw_files['block-v1-20261101-827/tasks/revision300-route-r/receipt.json']);assert r['source_commit']==m['source_commit']
 for name,h in r['inputs'].items():
  if '/__pycache__/'not in name:assert hashlib.sha256(tar.extractfile(name).read()).hexdigest()==h
d.update(source_commit=m['source_commit'],source_archive_sha256=hashlib.sha256(Path('.local/issue121/source827.tar').read_bytes()).hexdigest(),archive_git_blobs_verified=len(m['files']),receipt_archive_inputs_match=True,final_acceptance=False,scope='Actual827 natural completed native six-stage flow; actual365 archived source files Git verified and new826 mapping/function receipt hashes bound. Five actual native final files indexed. Independent final-source828 RCX/STA/DRC/full GDS/function/LEC/full signal geometry and829 interfaces remain separate; no final macro acceptance implied.')
dest.mkdir()
for name,raw in raw_files.items():
 p=dest/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
(dest/'index.json').write_text(json.dumps(d,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps({k:d[k]for k in('captured_utc','all_receipt_outputs_actual_verified','archive_git_blobs_verified','source_commit','sacct')}));print('raw',len(d['files']),'large',len(d['server_only']),'controller828',d['controller_status']['runs'].get('block-v1-20261101-828'))
