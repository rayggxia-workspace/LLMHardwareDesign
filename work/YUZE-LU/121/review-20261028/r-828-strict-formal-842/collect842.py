from pathlib import Path
import json,hashlib,base64,subprocess,shlex,tarfile
q=r'''from pathlib import Path
import json,hashlib,base64,datetime,subprocess
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121');r=b/'block-v1-20261101-828';files={};large={}
selected=json.loads((r/'tasks/revision300-final-source-r/revision300-final-source.json').read_text());native=Path(selected['raw_source']);assert native==b/'block-v1-20261101-827/tasks/revision300-route-r'
assert hashlib.sha256((native/'receipt.json').read_bytes()).hexdigest()==selected['source_native_receipt_sha256']
q=json.loads((r/'node-queue.json').read_text());state=json.loads((r/'node-queue-state.json').read_text())
assert len(q['tasks'])==8
archive=hashlib.sha256((r/'source.tar').read_bytes()).hexdigest()
assert archive=='3c40abeef7c73bce224652d8ba7c0060576394f0bf4a6152bd4fe25c065380f1'
job=json.loads((r/'dispatch-state.json').read_text())['tasks']['native-node-queue']['job_id'];assert str(job).isdigit()
sacct=subprocess.check_output(['sacct','-X','-j',str(job),'--format=JobIDRaw,State,ExitCode,Elapsed,NodeList','-n','-P'],universal_newlines=True)
assert str(job)+'|RUNNING|' in sacct or str(job)+'|COMPLETED|0:0|' in sacct, sacct
selected_tasks=('revision300-final-source-r','revision300-final-function-r','revision300-formal-r');assert all(state['tasks'][name]['status']=='PASSED'for name in selected_tasks)
paths=[r/n for n in ('manifest.json','node-queue.json','dispatch-state.json','node-queue-state.json','stage-identity-proof.json')]
for t in [v for v in q['tasks']if v['id']in selected_tasks]:
 p=r/'tasks'/t['id'];receipt=json.loads((p/'receipt.json').read_text());assert receipt['passed'];paths+=[p/'receipt.json']+[p/n for n in receipt['outputs']]
for p in dict.fromkeys(paths):
 h=hashlib.sha256()
 with p.open('rb')as f:
  for v in iter(lambda:f.read(1024*1024),b''):h.update(v)
 row=dict(bytes=p.stat().st_size,sha256=h.hexdigest());name=str(p.relative_to(b))
 if row['bytes']<3000000:row['base64']=base64.b64encode(p.read_bytes()).decode();files[name]=row
 else:large[name]=row
m=json.loads((r/'src/bundle-manifest.json').read_text());sources={v['path']:hashlib.sha256((r/'src'/v['path']).read_bytes()).hexdigest()for v in m['files']}
print(json.dumps(dict(captured_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),files=files,actual_server_large=large,actual_source_sha256=sources,actual_archive_sha256=archive,sacct=sacct)))'''
d=json.loads(subprocess.check_output(['ssh','-o','BatchMode=yes','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)]));out=Path('work/YUZE-LU/121/review-20261028/r-828-strict-formal-842');assert not out.exists();raw={n:base64.b64decode(v['base64'])for n,v in d['files'].items()}
for name,value in raw.items():
 row=d['files'][name];assert hashlib.sha256(value).hexdigest()==row['sha256'] and len(value)==row['bytes']
with tarfile.open('.local/issue121/source827.tar')as t:
 m=json.load(t.extractfile('bundle-manifest.json'));assert hashlib.sha256(Path('.local/issue121/source827.tar').read_bytes()).hexdigest()==d['actual_archive_sha256'];assert d['actual_source_sha256']=={v['path']:v['sha256']for v in m['files']}
 batch=subprocess.check_output(['git','cat-file','--batch'],input=''.join(v['git_blob']+'\n'for v in m['files']).encode());pos=0
 for row in m['files']:
  end=batch.index(b'\n',pos);header=batch[pos:end].split();assert header[0].decode()==row['git_blob'];n=int(header[2]);pos=end+1;assert batch[pos:pos+n]==t.extractfile(row['path']).read();pos+=n+1
 assert pos==len(batch)
 for n,value in raw.items():
  if not n.endswith('/receipt.json'):continue
  r=json.loads(value);assert r['passed']and r['source_commit']==m['source_commit']
  for path,h in r['inputs'].items():
   if '/__pycache__/'not in path:assert hashlib.sha256(t.extractfile(path).read()).hexdigest()==h
  for path,h in r['outputs'].items():
   key=n.rsplit('/',1)[0]+'/'+path;row=d['files'].get(key,d['actual_server_large'].get(key));assert row, key
   if row['sha256']!=h:
    assert path=='node-queue-child.log',(key,h)
    d.setdefault('post_receipt_child_log_appends',{})[key]=dict(receipt_sha256=h,actual_sha256=row['sha256'])
prefix='block-v1-20261101-828/tasks/'
report=lambda mode,name:json.loads(raw[prefix+mode+'/'+name])
source=report('revision300-final-source-r','revision300-final-source.json')
source_receipt=raw[prefix+'revision300-final-source-r/receipt.json'];source_sha=hashlib.sha256(source_receipt).hexdigest()
assert source['raw_source']=='/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/block-v1-20261101-827/tasks/revision300-route-r'
assert source['rtl_sha256']=={'project/rtl/block_library_v1/block_v1_r.sv':'634f7f7793ced998423a59d4f744c45191c3c7e02f37cebf1b1f183563a7560b'}
fn=report('revision300-final-function-r','five-macro-final-function.json')
assert fn['passed'] and fn['source_receipt_sha256']==source_sha
old_source=Path('work/YUZE-LU/121/review-20261028/r-828-physical-signal-838/block-v1-20261101-828/tasks/revision300-final-source-r/receipt.json').read_bytes()
assert old_source==source_receipt
native_receipt=Path('work/YUZE-LU/121/review-20261028/r-827-native-835/block-v1-20261101-827/tasks/revision300-route-r/receipt.json').read_bytes()
assert source['source_native_receipt_sha256']==hashlib.sha256(native_receipt).hexdigest()
view=fn['full_final_netlist'];assert view['passed'] and view['exact_other_signal_connectivity']['passed']
assert view['input_sha256']=={source['raw_source'].replace('block-v1-20261101-827/tasks/revision300-route-r','block-v1-20261101-828/tasks/revision300-final-source-r')+'/flow/results/nangate45/bv1_block_v1_r/base/'+n:source['final_files'][n]['sha256']for n in ('6_final.odb','6_final.v')}
proj=view['input_only_projection'];assert proj['passed'] and proj['exact_inverse_reconstruction'] and proj['allowed_master']=='ANTENNA_X1' and proj['removed_count']==146
assert set(fn['initial_runs'])=={'all-ones','random-121','random-122'}
for name,run in fn['initial_runs'].items():
 assert run['result']==dict(passed=True,random_recurrent_cases=240,conv_cases=100,checks=379979,cycles=178456)
 assert any(v['sha256']==run['log_sha256']for v in d['files'].values())
 assert (run['initial'],run['seed'])=={'all-ones':(1,121),'random-121':(2,121),'random-122':(2,122)}[name]
assert not fn['qualified_hard_macro'] and not fn['strict_formal_qualified']
formal=report('revision300-formal-r','five-macro-formal.json')
assert formal['passed'] and formal['source_receipt_sha256']==source_sha
assert formal['source_final_function_receipt_sha256']==hashlib.sha256(raw[prefix+'revision300-final-function-r/receipt.json']).hexdigest()
assert formal['strict_native_lec']['passed'] and all(formal['strict_native_lec']['checks'].values())
d.update(actual_strict_formal=formal)
d.update(source_commit=m['source_commit'],source_git_blobs_verified=len(m['files']),all_inputs_and_actual_outputs_verified=True,source_receipt_sha256=source_sha,actual_function_runs=fn['initial_runs'],full_final_view_structural_proof=view['exact_other_signal_connectivity'],same_final_source_bound=True,overall_final_acceptance=False,scope='Actual828 same-source full final netlist three-init function passed;365 archived source Git blobs, receipt inputs and stable actual outputs verified. Strict independent LEC passed. Full unmodified GDS DRC, final sixfiles, actual full geometry/view and829 interfaces remain pending. No old qualification transfer.')

out.mkdir()
for n,v in raw.items():
 row=d['files'][n];assert hashlib.sha256(v).hexdigest()==row['sha256']and len(v)==row['bytes'];row.pop('base64');p=out/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(v)
(out/'index.json').write_bytes((json.dumps(d,indent=2)+'\n').encode());print('842',len(raw),'raw',len(d['actual_server_large']),'large','source',m['source_commit']);print(d['sacct'])
