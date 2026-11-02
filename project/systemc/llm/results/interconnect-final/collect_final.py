from pathlib import Path
import subprocess,tarfile,io,json,hashlib,datetime,shutil
r='/public/home/yuzelu/project-circuit/LLMHardwareDesign/systemc-llm-issue153'
audit_path=Path('.local/interconnect/interconnect-audit-f17.json')
if not audit_path.exists():subprocess.run(['scp','yuzelu@10.129.166.172:'+r+'/continuation-r8/interconnect-audit-f17.json',str(audit_path)],check=True)
a=json.loads(audit_path.read_text());assert len(a['runs'])==54
expected=dict(a['files']);expected.update(a['large_input_files'])
for row in a['runs']:expected.update(row['files'])
names=set()
small=('flow-summary.json','validation.json','systemc_receipt.json','tensor-link.json','run-inputs.sha256','numerical-gates.json','flow-controls.jsonl')
cp_small=('metadata.txt','weights.index','weights.scales','parameters.scales','prompt.txt','export_receipt.json')
for row in a['runs']:
 c=row['case']
 for base,files in [(c['run'],small),(c['checkpoint'],cp_small)]:
  for n in files:
   p=base+'/'+n
   if r+'/'+p in expected:names.add(p)
 names.add(c['log'])
for p,h in a['files'].items():
 n=p[len(r)+1:]
 if n.endswith(('.json','.py','.sbatch','.sha256','.log','.out')):names.add(n)
names.update('build-'+v+'/Testing/Temporary/LastTest.log'for v in ('f2','f6','f14'))
paths=sorted(names)
code='import tarfile,sys\nr='+repr(r)+'\nwith tarfile.open(fileobj=sys.stdout.buffer,mode="w|gz",dereference=True) as t:\n for p in '+repr(paths)+':t.add(r+"/"+p,arcname=p)\n'
result=subprocess.run(['ssh','-o','BatchMode=yes','yuzelu@10.129.166.172','python3 -'],input=code.encode(),capture_output=True,check=True)
out=Path('project/systemc/llm/results/interconnect-final');out.mkdir(exist_ok=False)
index=dict(scope=a['scope'],remote_root=r,collected_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
 source_parent='d6f033ecb6d9a28ec35fce1bb2465f28c5638df1',files={},source_archives={},reports={})
def digest(raw):return dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
index['allocated_audit']=dict(remote=r+'/continuation-r8/interconnect-audit-f17.json',**digest(audit_path.read_bytes()))
index['collection_tool']=dict(path='collect_final.py',**digest(Path(__file__).read_bytes()))
shutil.copyfile(Path(__file__),out/'collect_final.py')
with tarfile.open(fileobj=io.BytesIO(result.stdout))as t:
 for m in t.getmembers():
  assert m.isfile()and m.name in paths,m.name
  raw=t.extractfile(m).read();p=out/m.name;p.parent.mkdir(parents=True,exist_ok=True)
  assert digest(raw)==expected[r+'/'+m.name],m.name
  p.write_bytes(raw);index['files'][m.name]=dict(remote=r+'/'+m.name,matched_independent_allocated_audit=True,**digest(raw))
assert len(index['files'])==len(paths)
for rev in ('f1','f2','f6','f14'):
 p=Path('.local/continuation')/('systemc-src-'+rev+'.tar.gz');assert digest(p.read_bytes())==a['files'][r+'/'+p.name]
 with tarfile.open(p)as t:members={m.name:hashlib.sha256(t.extractfile(m).read()).hexdigest()for m in t.getmembers()}
 index['source_archives'][rev]=dict(**digest(p.read_bytes()),members=members)
 p=Path('.local/continuation')/('source-'+rev+'.json');shutil.copyfile(p,out/p.name)
for row in a['runs']:
 c=row['case'];index['reports'][c['run']]=dict(case=c,gates=row['gates'],controls=row['controls'])
shutil.copyfile(audit_path,out/'remote-audit.json')
(out/'index.json').write_bytes((json.dumps(index,indent=2,ensure_ascii=False)+'\n').encode())
(out/'README.md').write_text('''# Dataflow, finite bridge and extended-sequence evidence

54 complete real text-model experiments: seven observations, 21 width/queue
comparisons, seven first extended cases, five repair isolation cases, seven final
extended cases, and seven final original-prompt/link rechecks. Six failing runs
are intentionally retained. All final seven models pass frozen gates at all nine
positions using the same f14 executable; Llama is deferred. Eleven conditional
FP32 weight/parameter diagnostics are separate from complete SystemC runs.

remote-audit.json independently reassesses gates and strictly checks dependencies,
lifetimes, macro totals, controls, finite link limits, full binary equivalence,
original source/weight/scales/reference provenance and actual execution hashes.
It retains original FP32 metrics; it does not recompute those expensive forwards.
index.json verifies each collected raw small file byte-for-byte against that
allocated-node audit. Full weights, binaries, events and value CSV remain at the
indexed authorized server paths. Source archives f1/f2/f6/f14 were uncommitted
snapshots based on d6f033; archive/member SHA, not the parent alone, binds execution.
Actual staged runners are separately hashed. f9 was cancelled before execution.

The bridge carries host-mediated outer Tensor boundaries. Static matrix weights
and raw R state are outside it; internal macro arithmetic remains untimed. Timings
are assumptions, not M11/M12 geometry, chip throughput or finite total memory.
Sequential model execution shows no queue-depth benefit. Separate CTest senders
cover contention, corruption and missing-response rejection.

Chronology, failures, fixes, format costs and limits:
docs/SYSTEMC_INTERCONNECT_EXPERIMENTS.md. Local UBSan/13 CTest and synthetic
fixtures are a separate interconnect-local-f14 collection, not pretrained models.
''',encoding='utf-8')
print('COLLECTED',len(paths),'exact raw files; 54 runs; six retained failures; final 7/7')
