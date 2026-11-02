"""Run immutable N-long and F1024 suites in one authorized Slurm allocation."""
import argparse,collections,datetime,hashlib,json,os,platform,re,subprocess,sys
from pathlib import Path
ALLOWED=Path('/public/home/yuzelu/Melodydt').resolve()
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def fingerprint(path):
 digest=hashlib.sha256();size=0
 with path.open('rb') as stream:
  for block in iter(lambda:stream.read(1048576),b''):digest.update(block);size+=len(block)
 return {'bytes':size,'sha256':digest.hexdigest()}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);ap.add_argument('--output',type=Path,required=True)
 ap.add_argument('--source-commit',required=True);ap.add_argument('--container-sha256',required=True);a=ap.parse_args()
 root=a.root.resolve();out=a.output.resolve()
 assert ALLOWED in root.parents and ALLOWED in out.parents and not out.exists()
 assert os.environ.get('SLURM_JOB_ID','').isdigit() and int(os.environ.get('SLURM_CPUS_PER_TASK','0'))>=8
 assert os.environ.get('SLURM_JOB_NAME')=='zenanyan-f1024'
 assert re.fullmatch('[0-9a-f]{40}',a.source_commit) and re.fullmatch('[0-9a-f]{64}',a.container_sha256)
 out.mkdir(parents=True);logs=out/'logs';results=out/'results';generated=out/'generated'
 logs.mkdir();results.mkdir();generated.mkdir()
 receipt={'status':'RUNNING','started_utc':now(),'source_commit':a.source_commit,'node':platform.node(),
  'input_root':str(root),'output_root':str(out),'python_version':sys.version,'container_sha256':a.container_sha256,
  'slurm':{k:v for k,v in os.environ.items() if k in ['SLURM_JOB_ID','SLURM_JOB_NAME','SLURM_CPUS_PER_TASK','SLURM_JOB_PARTITION','SLURM_JOB_NODELIST']},
  'commands':[],'inputs':[],'suite_checks':{},'physical_qualification':False,'trained_model_quality':False}
 def save():(results/'run-receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 def run(label,argv):
  log=logs/(label+'.log');start=now()
  with log.open('wb') as stream:ret=subprocess.run(argv,cwd=str(root),stdout=stream,stderr=subprocess.STDOUT)
  receipt['commands'].append({'label':label,'argv':argv,'exit_code':ret.returncode,'started_utc':start,'ended_utc':now(),'log':str(log),**fingerprint(log)});save()
  if ret.returncode:raise RuntimeError(label+' exit '+str(ret.returncode))
  return log.read_text(encoding='utf8',errors='replace')
 try:
  manifest=json.loads((root/'source-manifest.json').read_text())
  assert manifest['source_commit']==a.source_commit
  for item in manifest['files']:
   rel=Path(item['path']);path=(root/rel).resolve();assert not rel.is_absolute() and root in path.parents
   actual=fingerprint(path);assert actual=={k:item[k] for k in ['bytes','sha256']},item['path']
   receipt['inputs'].append(dict(actual,path=item['path']))
  exe='/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator'
  run('verilator-version',[exe,'--version']);run('compiler-version',['g++','--version']);run('make-version',['make','--version'])
  helper=root/'work/Melodydt/151'
  run('regenerate-f1024-vectors',['python3',str(helper/'build_f1024_vectors.py'),'--root',str(root),'--directory',str(generated),'--weight-directory',str(results/'canonical')])
  regenerated=[]
  for name in ['f1024-contract-vectors.json','f1024-weight-stream-index.json']:
   assert (generated/name).read_bytes()==(helper/name).read_bytes(),name
   regenerated.append(dict(fingerprint(generated/name),path=str(generated/name)))
  receipt['regenerated_vectors']=regenerated;save()
  for suite in ['nlong','f1024']:
   contract=json.loads((helper/(suite+'-tb-contract.json')).read_text())
   top=contract['top_module'];marker=contract['pass_marker']
   ids=contract['expected_case_ids'];assert ids and len(ids)==len(set(ids))
   sources=contract['compile_sources'];locked={x['path'] for x in receipt['inputs']}
   assert all(x in locked for x in sources)
   includes=[]
   for name in contract['include_dirs']:
    path=(root/name).resolve();assert root in path.parents and path.is_dir();includes.append('-I'+str(path))
   obj=out/('obj_'+suite)
   text=run('build-'+suite,[exe,'--binary','--timing','--threads','1','-j','8','-Wno-fatal','--top-module',top,'--Mdir',str(obj)]+includes+sources)
   receipt.setdefault('warnings',{})[suite]=re.findall(r'^%Warning[^\n]*',text,re.M);save()
   text=run('simulate-'+suite,[str(obj/('V'+top)),'+out_dir='+str(results)])
   got=re.findall(r'^CASE_PASS ([A-Z][A-Z0-9_]+)\s*$',text,re.M)
   count=re.findall(r'^'+marker+r' cases=(\d+)\s*$',text,re.M)
   check={'expected_case_ids':ids,'observed_case_ids':got,'missing':sorted(set(ids)-set(got)),
    'unexpected':sorted(set(got)-set(ids)),'duplicates':sorted(k for k,v in collections.Counter(got).items() if v!=1),
    'summary_counts':count,'failure_text':bool(re.search(r'FAIL_|%Error|%Fatal|Assertion failed|Aborting',text))}
   check['passed']=not check['failure_text'] and got==ids and count==[str(len(ids))]
   receipt['suite_checks'][suite]=check;save()
   if not check['passed']:raise RuntimeError(suite+' CASE/summary mismatch')
  streams=[];expected=json.loads((helper/'f1024-weight-stream-index.json').read_text())['streams']
  for item in expected:
   filename=item['binary_filename'];canonical=results/'canonical'/filename;observed=results/filename
   actual=fingerprint(observed);want={'bytes':item['bytes'],'sha256':item['sha256']}
   assert fingerprint(canonical)==want and actual==want,filename
   streams.append({'fixture':item['fixture'],'canonical_path':str(canonical),'observed_accepted_path':str(observed),**actual})
  receipt['accepted_stream_checks']=streams
  (results/'accepted-stream-checks.json').write_text(json.dumps(streams,indent=2)+'\n')
  receipt['status']='PASS'
 except Exception as error:receipt['status']='FAIL';receipt['failure']=repr(error)
 finally:
  receipt['ended_utc']=now();receipt['output_files']=[dict(fingerprint(path),path=str(path.relative_to(out))) for path in sorted(logs.glob('*.log'))];save()
 print(json.dumps({'status':receipt['status'],'receipt':str(results/'run-receipt.json'),'failure':receipt.get('failure'),
  'case_counts':{key:len(value['observed_case_ids']) for key,value in receipt['suite_checks'].items()}},ensure_ascii=False))
 return 0 if receipt['status']=='PASS' else 1
if __name__=='__main__':sys.exit(main())
