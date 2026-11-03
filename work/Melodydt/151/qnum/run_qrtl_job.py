"""Frozen four-fixture real-data integer RTL validation in own Slurm allocation."""
import argparse,collections,datetime,hashlib,json,os,platform,re,subprocess,sys
from pathlib import Path
ALLOWED=Path('/public/home/yuzelu/Melodydt').resolve()
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def fp(p):
 h=hashlib.sha256();size=0
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):size+=len(b);h.update(b)
 return {'bytes':size,'sha256':h.hexdigest()}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);ap.add_argument('--output',type=Path,required=True)
 ap.add_argument('--source-commit',required=True);ap.add_argument('--container-sha256',required=True);a=ap.parse_args()
 root=a.root.resolve();out=a.output.resolve();assert all(ALLOWED in p.parents for p in [root,out]) and not out.exists()
 assert os.environ.get('SLURM_JOB_ID','').isdigit() and os.environ.get('SLURM_JOB_NAME')=='zenanyan-qrtl' and int(os.environ.get('SLURM_CPUS_PER_TASK','0'))>=8
 out.mkdir(parents=True);(out/'logs').mkdir();(out/'results').mkdir()
 receipt={'status':'RUNNING_RTL','source_commit':a.source_commit,'node':platform.node(),'started_utc':now(),
  'input_root':str(root),'output_root':str(out),'container_sha256':a.container_sha256,'python':sys.version,
  'slurm':{k:v for k,v in os.environ.items() if k in ['SLURM_JOB_ID','SLURM_JOB_NAME','SLURM_CPUS_PER_TASK','SLURM_JOB_PARTITION','SLURM_JOB_NODELIST']},
  'commands':[],'inputs':[],'data_inputs':[],'fixture_checks':[],'full_model_quality_accepted':False,'physical_qualification':False}
 def save():(out/'results/run-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
 def run(label,argv):
  log=out/'logs'/(label+'.log');start=now()
  with log.open('wb') as f:p=subprocess.run(argv,stdout=f,stderr=subprocess.STDOUT,cwd=str(root))
  receipt['commands'].append({'label':label,'argv':argv,'exit_code':p.returncode,'started_utc':start,'ended_utc':now(),**fp(log)});save()
  if p.returncode:raise RuntimeError(label+' exit '+str(p.returncode))
  return log.read_text(errors='replace')
 def lock(path,sha):
  p=path.resolve();assert ALLOWED in p.parents and p.is_file();x=fp(p);assert x['sha256']==sha,str(p)
  if not any(v['path']==str(p) for v in receipt['data_inputs']):receipt['data_inputs'].append(dict(x,path=str(p)))
 try:
  m=json.loads((root/'source-manifest.json').read_text());assert m['source_commit']==a.source_commit
  for x in m['files']:
   p=(root/x['path']).resolve();assert root in p.parents and fp(p)=={k:x[k] for k in ['bytes','sha256']},x['path'];receipt['inputs'].append(x)
  helper=root/'work/Melodydt/151/qnum';contract=json.loads((helper/'qnum-tb-contract.json').read_text());binding=json.loads((helper/'qnum-rtl-bindings.json').read_text())
  numeric=Path(binding['numeric_server_root']);assert ALLOWED in numeric.resolve().parents
  for n,k in [('numeric-summary.json','numeric_summary_sha256'),('numeric-run-receipt.json','numeric_receipt_sha256'),('rtl-fixture-index.json','fixture_index_sha256')]:lock(numeric/n,binding[k])
  run('check-independent-expectations',['python3',str(helper/'check_qnum_expectations.py'),'--root',str(root),'--numeric-dir',str(numeric),'--output',str(out/'results/independent-expectations.json')])
  exe='/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator';run('verilator-version',[exe,'--version']);run('compiler-version',['g++','--version'])
  built={};expected=contract['expected_case_ids'];assert len(expected)==len(set(expected))==7
  for item in binding['cases']:
   label=item['label'];profile=item['profile'];fixture=item['fixture'];pid=item['profile_id'];shifts=profile['M_READ_right_shift']
   assert 1<=profile['epsilon_code']<=0xffffffff and profile['M_factor']==1 and profile['M_left_shift']==0 and all(0<=v<=63 for v in shifts)
   for stage,value in fixture['stages'].items():lock(numeric/value['hex_file'],value['sha256'])
   lock(numeric/fixture['gamma_hex_file'],fixture['gamma_hex_sha256']);weights=numeric/profile['weights_stream_file'];lock(weights,profile['weights_stream_sha256']);assert fp(weights)['bytes']==9437184
   params={'N_EPSILON':profile['epsilon_code'],'M_GATE_SHIFT':shifts[0],'M_UP_SHIFT':shifts[1],'M_DOWN_SHIFT':shifts[2]}
   if pid not in built:
    obj=out/('obj_'+item['role']);top='block_w4_qnum_tb'
    argv=[exe,'--binary','--timing','--threads','1','-j','8','-Wno-fatal','--top-module',top,'--Mdir',str(obj)]+['-G'+k+'='+str(v) for k,v in params.items()]
    argv+=['-I'+str(root/p) for p in contract['include_dirs']]+contract['compile_sources']
    text=run('build-'+item['role'],argv);receipt.setdefault('warnings',{})[pid]=re.findall(r'^%Warning[^\n]*',text,re.M)
    built[pid]=str(obj/('V'+top))
   dump=out/'results'/('accepted-'+label+'.bin');args=[built[pid],'+dump='+str(dump),'+weights='+str(weights),'+gamma='+str(numeric/fixture['gamma_hex_file']),'+expected_sat='+str(int(fixture['expected_native_done_saturated']))]
   args+=['+'+stage+'='+str(numeric/value['hex_file']) for stage,value in fixture['stages'].items()]
   text=run('simulate-'+label,args);got=re.findall(r'^CASE_PASS ([A-Z][A-Z0-9_]+)\s*$',text,re.M);summary=re.findall(r'^PASS_QNUM cases=(\d+)\s*$',text,re.M)
   bad=bool(re.search(r'FAIL_|%Error|%Fatal|Assertion failed|Aborting',text));actual=fp(dump)
   passed=not bad and set(got)==set(expected) and len(got)==len(expected) and summary==['7'] and actual=={'bytes':9437184,'sha256':profile['weights_stream_sha256']}
   receipt['fixture_checks'].append({'label':label,'profile':pid,'fixture':fixture['id'],'params':params,'observed_case_ids':got,'expected_count':7,'summary':summary,'passed':passed,'accepted_dump':str(dump),**actual});save()
   if not passed:raise RuntimeError(label+' CASE/dump check')
  assert len(receipt['fixture_checks'])==4
  receipt['status']='PASS_REAL_DATA_INTEGER_RTL_NOT_MODEL_QUALITY'
 except Exception as error:receipt['status']='FAIL';receipt['failure']=repr(error)
 finally:receipt['ended_utc']=now();save()
 print(json.dumps({'status':receipt['status'],'receipt':str(out/'results/run-receipt.json'),'failure':receipt.get('failure'),'fixtures':len(receipt['fixture_checks'])}))
 return 0 if receipt['status'].startswith('PASS_') else 1
if __name__=='__main__':sys.exit(main())
