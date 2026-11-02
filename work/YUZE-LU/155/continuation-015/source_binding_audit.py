from pathlib import Path
import subprocess,hashlib,json,shlex,tarfile,io
root=Path.cwd();base='/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-155';specs=[('011','14deb5b9','source-gen011c.tar'),('012','4b459693','source-grid012.tar')];local=[]
for gen,commit,archive in specs:
 raw=subprocess.check_output(['git','-c','core.autocrlf=true','archive',commit,'project/rtl','project/experiments']);sha=hashlib.sha256(raw).hexdigest();members={}
 with tarfile.open(fileobj=io.BytesIO(raw))as t:
  for m in t.getmembers():
   if m.isfile():members[m.name]=hashlib.sha256(t.extractfile(m).read()).hexdigest()
 subprocess.run(['git','merge-base','--is-ancestor',commit,'d331a245'],check=True)
 local.append(dict(generation=gen,commit=subprocess.check_output(['git','rev-parse',commit],text=True).strip(),archive=archive,archive_sha256=sha,files=members))
q=r'''from pathlib import Path
import json,hashlib,tarfile,sys
b=Path(BASE);specs=json.load(sys.stdin);rows=[]
for d in specs:
 archive=b/d['archive'];assert hashlib.sha256(archive.read_bytes()).hexdigest()==d['archive_sha256'];producer=b/('generate-'+d['generation']);receipt=json.loads((producer/'submission.json').read_text());assert receipt['archive_sha256']==d['archive_sha256']
 actual={}
 with tarfile.open(archive)as t:
  for m in t.getmembers():
   if m.isfile():
    h=hashlib.sha256(t.extractfile(m).read()).hexdigest();p=producer/'source'/m.name;assert hashlib.sha256(p.read_bytes()).hexdigest()==h;actual[m.name]=h
 assert actual==d['files'];rows.append(dict(passed=True,source_commit=d['commit'],archive_path=str(archive),archive_sha256=d['archive_sha256'],extracted_source_path=str(producer/'source'),verified_file_count=len(actual),all_files_manifest_sha256=hashlib.sha256(json.dumps(actual,sort_keys=True).encode()).hexdigest(),s_sram_files={k:v for k,v in actual.items()if k.startswith(('project/experiments/s_sram/','project/rtl/s_sram/'))}))
print(json.dumps(dict(passed=True,qualified=False,archive_options={'core.autocrlf':'true','paths':['project/rtl','project/experiments']},scope='Exact git archive, submitted producer archive and every extracted source file binding; not circuit, timing or complete S acceptance',producers=rows)))
'''.replace('BASE',repr(base))
d=json.loads(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],input=json.dumps(local).encode()));bundle=Path('.local/issue155-source-history014.bundle');d['source_history_bundle']=dict(path=base+'/source-history-014.bundle',sha256=hashlib.sha256(bundle.read_bytes()).hexdigest(),requires_base_commit='30c7db51808957f5ae9245646357c822cd8ab1e0',head_commit='d331a245c3d50bfac92858abee0eff6bcdb2f3bf',native_bundle_verify_passed=True,producer_commits_are_ancestors_of_bundle_head=True);out=Path('work/YUZE-LU/155/continuation-015/source-recovery-binding.json');out.write_text(json.dumps(d,indent=2)+'\n',encoding='utf-8');print(json.dumps(dict(passed=d['passed'],counts=[p['verified_file_count']for p in d['producers']],archives=[p['archive_sha256']for p in d['producers']])))

