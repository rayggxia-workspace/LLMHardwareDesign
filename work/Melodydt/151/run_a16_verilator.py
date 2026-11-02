"""Run frozen A16 inputs inside one Slurm allocation; no SSH/install/submission."""
import argparse,collections,datetime,hashlib,json,os,platform,re,subprocess,sys
from pathlib import Path
ALLOWED=Path('/public/home/yuzelu/Melodydt').resolve()
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def fingerprint(p):
 raw=p.read_bytes();return {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
def inside(p):
 p=p.resolve();return p==ALLOWED or ALLOWED in p.parents
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);ap.add_argument('--output',type=Path,required=True)
 ap.add_argument('--source-commit',required=True);ap.add_argument('--container-sha256',required=True);a=ap.parse_args()
 root=a.root.resolve();out=a.output.resolve();assert inside(root) and inside(out) and not out.exists()
 assert os.environ.get('SLURM_JOB_ID','').isdigit() and int(os.environ.get('SLURM_CPUS_PER_TASK','0'))>=8
 assert os.environ.get('SLURM_JOB_NAME','')=='zenanyan-a16'
 assert re.fullmatch('[0-9a-f]{40}',a.source_commit) and re.fullmatch('[0-9a-f]{64}',a.container_sha256)
 out.mkdir(parents=True);logs=out/'logs';results=out/'results';logs.mkdir();results.mkdir()
 receipt={'status':'RUNNING','started_utc':now(),'source_commit':a.source_commit,'node':platform.node(),
  'input_root':str(root),'output_root':str(out),'python_version':sys.version,'container_sha256':a.container_sha256,
  'slurm':{k:v for k,v in os.environ.items() if k in ['SLURM_JOB_ID','SLURM_JOB_NAME','SLURM_CPUS_PER_TASK','SLURM_JOB_PARTITION','SLURM_JOB_NODELIST']},
  'commands':[],'inputs':[],'physical_qualification':False,'full_model_quality':False}
 def save():
  (results/'run-receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 def run(label,argv):
  log=logs/(label+'.log');start=now()
  with log.open('wb') as f:r=subprocess.run(argv,cwd=str(root),stdout=f,stderr=subprocess.STDOUT)
  row={'label':label,'argv':argv,'exit_code':r.returncode,'started_utc':start,'ended_utc':now(),'log':str(log),'fingerprint':fingerprint(log)}
  receipt['commands'].append(row);save()
  if r.returncode:raise RuntimeError(label+' exit '+str(r.returncode))
  return log.read_text(encoding='utf8',errors='replace')
 try:
  manifest=json.loads((root/'source-manifest.json').read_text(encoding='utf8'))
  assert manifest['source_commit']==a.source_commit
  for x in manifest['files']:
   rel=Path(x['path']);p=(root/rel).resolve();assert not rel.is_absolute() and root in p.parents and p.is_file()
   actual=fingerprint(p);assert actual=={'bytes':x['bytes'],'sha256':x['sha256']},x['path']
   receipt['inputs'].append({'path':x['path'],**actual})
  contract=json.loads((root/'work/Melodydt/151/a16-tb-contract.json').read_text(encoding='utf8'))
  ids=contract['expected_case_ids'];assert ids and len(ids)==len(set(ids))
  exe='/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator'
  run('verilator-version',[exe,'--version']);run('compiler-version',['g++','--version']);run('make-version',['make','--version'])
  include_dirs=[]
  for name in contract['include_dirs']:
   p=(root/name).resolve();assert root in p.parents and p.is_dir();include_dirs.append('-I'+str(p))
  for name in contract['compile_sources']:assert any(x['path']==name for x in receipt['inputs']),name
  obj=out/'obj_a16';cmd=[exe,'--binary','--timing','--threads','1','-j','8','-Wno-fatal','--top-module','block_w4_a16_tb','--Mdir',str(obj)]+include_dirs+contract['compile_sources']
  build=run('build-a16',cmd)
  receipt['warnings']=re.findall(r'^%Warning[^\n]*',build,re.M)
  text=run('simulate-a16',[str(obj/'Vblock_w4_a16_tb')])
  got=re.findall(r'^CASE_PASS ([A-Z][A-Z0-9_]+)\s*$',text,re.M)
  marker=re.findall(r'^PASS_W4_A16 cases=(\d+)\s*$',text,re.M)
  failed=bool(re.search(r'FAIL_|%Error|%Fatal|Assertion failed|Aborting',text))
  check={'expected_count':len(ids),'observed_case_ids':got,'missing':sorted(set(ids)-set(got)),'unexpected':sorted(set(got)-set(ids)),
   'duplicates':sorted(k for k,v in collections.Counter(got).items() if v!=1),'summary_counts':marker,'failure_text':failed}
  check['passed']=not failed and set(got)==set(ids) and len(got)==len(ids) and marker==[str(len(ids))]
  receipt['output_check']=check
  if not check['passed']:raise RuntimeError('complete CASE/summary set mismatch')
  receipt['status']='PASS'
 except Exception as e:receipt['status']='FAIL';receipt['failure']=repr(e)
 finally:
  receipt['ended_utc']=now();receipt['output_files']=[{'path':str(p.relative_to(out)),**fingerprint(p)} for p in sorted(logs.glob('*.log'))];save()
 print(json.dumps({'status':receipt['status'],'receipt':str(results/'run-receipt.json'),'failure':receipt.get('failure'),'output_check':receipt.get('output_check')},ensure_ascii=False))
 return 0 if receipt['status']=='PASS' else 1
if __name__=='__main__':sys.exit(main())
