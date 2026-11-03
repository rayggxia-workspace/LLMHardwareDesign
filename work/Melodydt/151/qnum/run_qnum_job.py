"""Immutable numerical diagnostic wrapper, executed only in an own Slurm job."""
from pathlib import Path
import argparse,datetime,hashlib,json,os,platform,subprocess,sys
ALLOWED=Path('/public/home/yuzelu/Melodydt').resolve()
def sha(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);ap.add_argument('--dataset',type=Path,required=True)
 ap.add_argument('--output',type=Path,required=True);ap.add_argument('--source-commit',required=True);ap.add_argument('--container-sha256',required=True);a=ap.parse_args()
 root=a.root.resolve();data=a.dataset.resolve();out=a.output.resolve()
 assert all(ALLOWED in p.parents for p in [root,data,out]) and not out.exists()
 assert os.environ.get('SLURM_JOB_ID','').isdigit() and os.environ.get('SLURM_JOB_NAME')=='zenanyan-qnum' and int(os.environ.get('SLURM_CPUS_PER_TASK','0'))>=8
 out.mkdir(parents=True);(out/'logs').mkdir()
 r={'status':'RUNNING_NUMERICAL_NOT_RTL','source_commit':a.source_commit,'started_utc':now(),'node':platform.node(),
  'input_root':str(root),'dataset':str(data),'output_root':str(out),'container_sha256':a.container_sha256,
  'slurm':{k:v for k,v in os.environ.items() if k in ['SLURM_JOB_ID','SLURM_JOB_NAME','SLURM_CPUS_PER_TASK','SLURM_JOB_PARTITION','SLURM_JOB_NODELIST']},
  'commands':[],'inputs':[],'trained_full_model_quality_accepted':False,'RTL_executed':False}
 def save():(out/'job-receipt.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 try:
  m=json.loads((root/'source-manifest.json').read_text());assert m['source_commit']==a.source_commit
  for x in m['files']:
   p=(root/x['path']).resolve();assert root in p.parents and p.stat().st_size==x['bytes'] and sha(p)==x['sha256'],x['path'];r['inputs'].append(x)
  d=json.loads((data/'manifest.json').read_text());assert d['status']=='COMPLETE_SELECTED_TENSORS_AND_ROWS'
  assert d['source_commit']=='929895827c84861aa68b59a4690b3fbf35084b0d'
  r['dataset_manifest_sha256']=sha(data/'manifest.json');r['acquisition_source_commit']=d['source_commit'];save()
  script=root/'work/Melodydt/151/qnum/run_qwen_layer0.py';cpp=root/'work/Melodydt/151/qnum/qwen_layer0_numeric.cpp'
  argv=['python3',str(script),'--data-dir',str(data),'--output',str(out/'results'),'--engine-source',str(cpp),'--threads','8']
  log=out/'logs/run-numeric.log';start=now()
  with log.open('wb') as f:p=subprocess.run(argv,stdout=f,stderr=subprocess.STDOUT,cwd=str(root))
  r['commands'].append({'argv':argv,'exit_code':p.returncode,'started_utc':start,'ended_utc':now(),'log':str(log),'sha256':sha(log)})
  assert p.returncode==0,'numeric process failed'
  numeric=json.loads((out/'results/numeric-run-receipt.json').read_text())
  assert numeric['status']=='PASS_SELECTED_LAYER0_NUMERICAL_DIAGNOSTIC_NOT_RTL_OR_FULL_MODEL_QUALITY'
  assert all(c['exit_code']==0 for c in numeric['commands'])
  r['numeric_receipt_sha256']=sha(out/'results/numeric-run-receipt.json');r['selected_candidate']=numeric['selected_candidate']
  r['status']='PASS_NUMERICAL_DIAGNOSTIC_NOT_RTL_OR_MODEL_QUALITY'
 except Exception as error:r['status']='FAIL';r['failure']=repr(error)
 finally:r['ended_utc']=now();save()
 print(json.dumps({'status':r['status'],'receipt':str(out/'job-receipt.json'),'failure':r.get('failure'),'selected_candidate':r.get('selected_candidate')}))
 return 0 if r['status'].startswith('PASS_') else 1
if __name__=='__main__':sys.exit(main())
