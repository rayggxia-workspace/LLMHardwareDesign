"""Slurm-only real native A/F integration with explicit destination S ACK."""
from pathlib import Path
import argparse,datetime,hashlib,json,os,platform,re,subprocess,sys
OWN=Path('/public/home/yuzelu/Melodydt')
def fp(path):
 h=hashlib.sha256();size=0
 with path.open('rb') as f:
  for x in iter(lambda:f.read(1048576),b''):size+=len(x);h.update(x)
 return dict(bytes=size,sha256=h.hexdigest())
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--vectors',type=Path,required=True);ap.add_argument('--source-commit',required=True);ap.add_argument('--container-sha256',required=True);a=ap.parse_args()
 root=a.root.resolve();out=a.output.resolve();vectors=a.vectors.resolve();assert all(OWN in p.parents for p in [root,out,vectors]) and not out.exists()
 assert os.environ.get('SLURM_JOB_ID','').isdigit() and os.environ.get('SLURM_JOB_NAME')=='zenanyan-w5-af' and int(os.environ.get('SLURM_CPUS_PER_TASK','0'))>=8
 assert a.container_sha256=='c742bf99ea498fb4da5135bc83fd1677abcebe0e64470e6a115f2baecb3905df'
 out.mkdir(parents=True);(out/'logs').mkdir();(out/'results').mkdir()
 receipt=dict(status='RUNNING_W5_NATIVE_AF',source_commit=a.source_commit,started_utc=now(),node=platform.node(),root=str(root),output=str(out),vectors=str(vectors),
              input_data_version='AF1024 frozen base fixture, original source b3e14e27e1c38afc697d383e33f5d8d90be62267',container_sha256=a.container_sha256,python=sys.version,
              Slurm={k:os.environ.get(k) for k in ['SLURM_JOB_ID','SLURM_JOB_NAME','SLURM_CPUS_PER_TASK','SLURM_JOB_PARTITION','SLURM_JOB_NODELIST']},commands=[],inputs=[],data=[],dumps=[],
              unit_tests=[],native_AF_passed=False,synthetic_profile=True,trained_quality_accepted=False,all_legal_graphs_proved=False,metal_ROM_qualified=False,physical_qualified=False)
 def save():(out/'results/run-receipt.json').write_bytes((json.dumps(receipt,indent=2)+'\n').encode())
 def run(label,argv):
  log=out/'logs'/(label+'.log');start=now()
  with log.open('wb') as f:r=subprocess.run(argv,cwd=root,stdout=f,stderr=subprocess.STDOUT)
  receipt['commands'].append(dict(label=label,argv=argv,exit_code=r.returncode,started_utc=start,ended_utc=now(),**fp(log)));save()
  if r.returncode:raise RuntimeError(label+' exit '+str(r.returncode))
  return log.read_text(errors='replace')
 try:
  manifest=json.loads((root/'source-manifest.json').read_text());assert manifest['source_commit']==a.source_commit
  for row in manifest['files']:
   p=(root/row['path']).resolve();assert root in p.parents and fp(p)=={k:row[k] for k in ['bytes','sha256']},row['path'];receipt['inputs'].append(row)
  contract=json.loads((root/'work/Melodydt/151/h2/af-contract.json').read_text())
  required=set(contract['compile_sources'])|set(contract['source_includes'])|set(contract['reference_dependencies'])|{'work/Melodydt/151/h2/'+n for n in ['af-contract.json','run_af.py','build_control_tables.py']}
  required|={p for u in contract.get('unit_tests',[]) for p in u['compile_sources']}
  assert required=={x['path'] for x in manifest['files']}
  old=json.loads((root/'work/Melodydt/151/af1024/fixture-contract.json').read_text())
  for name,expected in old['fixtures']['base']['files'].items():
   p=vectors/'base'/name;assert fp(p)==expected,name;receipt['data'].append(dict(path=str(p),**expected))
  for name,expected in old['dependencies'].items():assert fp(root/name)['sha256']==expected,name
  assert fp(root/contract['compile_sources'][-1])['sha256']==contract['tb_sha256']
  run('tables',['python3',str(root/'work/Melodydt/151/h2/build_control_tables.py'),'--root',str(root),'--output',str(out/'tables')])
  run('verilator-version',[contract['tool'],'--version']);run('compiler-version',['g++','--version'])
  for test in contract.get('unit_tests',[]):
   obj_u=out/('obj_'+test['id'])
   build_u=run('compile_'+test['id'],[contract['tool'],'--binary','--timing','--assert','--threads','1','-j','8','-Wno-fatal','--top-module',test['top'],'--Mdir',str(obj_u)]+test['compile_sources'])
   text_u=run('simulate_'+test['id'],[str(obj_u/('V'+test['top']))])
   observed=re.findall(r'^CASE_PASS ([A-Z][A-Z0-9_]+)\s*$',text_u,re.M)
   assert observed==test['cases'] and re.findall('^'+re.escape(test['summary'])+'\s*$',text_u,re.M)==[test['summary']]
   assert not re.search(r'FAIL_|%Error|%Fatal|Assertion failed|Aborting',text_u)
   receipt['unit_tests'].append(dict(id=test['id'],cases=observed,passed=True,warnings=re.findall(r'^%Warning[^\n]*',build_u,re.M)));save()
  obj=out/'obj_af';argv=[contract['tool'],'--binary','--timing','--assert','--threads','1','-j','8','-Wno-fatal','--top-module',contract['top'],'--Mdir',str(obj)]
  argv+=['-I'+str(root/x) for x in contract['include_dirs']]+contract['compile_sources']
  text=run('compile',argv);receipt['warnings']=re.findall(r'^%Warning[^\n]*',text,re.M)
  dump=out/'results/dumps';dump.mkdir()
  text=run('simulate',[str(obj/('V'+contract['top'])),'+rom='+str(out/'tables/g1_rom.hex'),'+meta='+str(out/'tables/g1_meta.hex'),'+vectors='+str(vectors),'+dump_dir='+str(dump)])
  cases=re.findall(r'^CASE_PASS ([A-Z][A-Z0-9_]+)\s*$',text,re.M);assert cases==contract['cases'],(cases,contract['cases'])
  assert re.findall('^'+re.escape(contract['summary'])+'\s*$',text,re.M)==[contract['summary']]
  assert not re.search(r'FAIL_|%Error|%Fatal|Assertion failed|Aborting',text)
  receipt['observed_case_ids']=cases
  assert {p.name for p in dump.iterdir() if p.is_file()}=={x['file'] for x in contract['dumps']}
  for row in contract['dumps']:
   actual=fp(dump/row['file']);assert actual=={k:row[k] for k in ['bytes','sha256']},(row,actual);receipt['dumps'].append(dict(file=row['file'],**actual,passed=True))
  for row in receipt['inputs']:assert fp(root/row['path'])=={k:row[k] for k in ['bytes','sha256']}
  for row in receipt['data']:assert fp(Path(row['path']))=={k:row[k] for k in ['bytes','sha256']}
  receipt['native_AF_passed']=True;receipt['status']='PASS_W5_G1_NATIVE_AF_NOT_TRAINED_QUALITY_OR_PHYSICAL'
 except Exception as e:receipt['status']='FAIL';receipt['failure']=repr(e)
 finally:
  receipt['ended_utc']=now();receipt['text_outputs']=[dict(path=str(p.relative_to(out)),**fp(p)) for d in ['tables','logs'] for p in sorted((out/d).rglob('*')) if p.is_file()];save()
 print(json.dumps(dict(status=receipt['status'],failure=receipt.get('failure'),receipt=str(out/'results/run-receipt.json'),cases=len(receipt.get('observed_case_ids',[])),dumps=len(receipt['dumps']))))
 return 0 if receipt['status'].startswith('PASS_') else 1
if __name__=='__main__':sys.exit(main())
