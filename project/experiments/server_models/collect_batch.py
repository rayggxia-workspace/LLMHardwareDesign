"""Publish verified server artifacts, sealed holdout and compact review evidence."""
import argparse,hashlib,json,os,platform,subprocess,sys,zipfile
from pathlib import Path

def digest(p):
 h=hashlib.sha256()
 with p.open('rb')as f:
  for b in iter(lambda:f.read(8<<20),b''):h.update(b)
 return h.hexdigest()
def save(p,o):p.write_text(json.dumps(o,indent=2)+'\n',newline='\n')
def archive(root,dest,files,scope):
 if dest.exists():raise ValueError('refuse overwrite '+str(dest))
 index={}
 with zipfile.ZipFile(dest,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6)as z:
  for p in sorted(set(files)):
   name=p.relative_to(root).as_posix();index[name]={'bytes':p.stat().st_size,'sha256':digest(p)}
   z.write(p,name,compress_type=zipfile.ZIP_STORED if p.suffix in ['.npz','.zip']else zipfile.ZIP_DEFLATED)
  z.writestr('artifact-index.json',json.dumps({'scope':scope,'files':index},indent=2)+'\n')
 return {'path':str(dest),'bytes':dest.stat().st_size,'sha256':digest(dest),'members':len(index)+1}
def main():
 p=argparse.ArgumentParser();p.add_argument('--root',required=True,type=Path);p.add_argument('--binding',required=True,type=Path);a=p.parse_args();source=Path(__file__).parent;b=json.loads(a.binding.read_text())
 for name,want in b['sources'].items():
  if digest(source/name)!=want:raise ValueError('collection source SHA '+name)
 root=a.root
 for phase in ['phase5','phase8','phase9','phase13']:
  binding=json.loads((root/phase/'binding.json').read_text())
  for name,want in binding['sources'].items():
   if digest(root/phase/name)!=want:raise ValueError('original stage source SHA '+phase+'/'+name)
 if not os.environ.get('SLURM_JOB_ID'):raise ValueError('Slurm required')
 subprocess.run([sys.executable,'-B',str(root/'phase13/summarize.py'),'--root',str(root),'--out',str(root/'batch-summary-final.json')],check=True)
 subprocess.run([sys.executable,'-B',str(source/'negative_real.py'),'--root',str(root),'--out',str(root/'negative-real01')],check=True)
 subprocess.run([sys.executable,'-B',str(source/'review_samples.py'),'--root',str(root),'--archive',str(root/'review-samples01.zip'),'--out',str(root/'review-readback01.json')],check=True)
 jobs='89992,89993,89995,90002,90016,90017,90026,90028,90029,90030,90031,90032,90033,90034,90035,90036,90037,90038,90039,90040,90041,90042,90043'
 r=subprocess.run(['sacct','-j',jobs,'--parsable2','--format=JobID,JobName,State,ExitCode,Elapsed,AllocCPUS,NodeList'],capture_output=True,check=True);(root/'execution-ledger.tsv').write_bytes(r.stdout)
 r=subprocess.run([sys.executable,'-m','pip','freeze'],capture_output=True,check=True);(root/'modern-freeze-final.txt').write_bytes(r.stdout)
 primary=[];holdout=[];metadata=[]
 for model,folder in [('gemma','gemma-capture01'),('qwen25','qwen25-gqa01'),('qwen35','qwen35-gqa01'),('phi','phi-reserved01')]:
  cap=root/folder;m=json.loads((cap/'manifest.json').read_text())
  for name,row in m['artifacts'].items():
   f=cap/name
   if f.stat().st_size!=row['bytes']or digest(f)!=row['sha256']:raise ValueError('raw capture artifact SHA')
  target=holdout if model=='phi'else primary;target.extend(p for p in cap.rglob('*')if p.is_file());target.extend(p for p in (root/(model+'-strict02')).rglob('*')if p.is_file())
  metadata.append(cap/'manifest.json');metadata.extend([root/(model+'-strict02')/'index.json',root/(model+'-export-source02.json')])
  target.append(root/(model+'-export-source02.json'))
  if model!='phi':
   q=root/(model+'-integer01');qm=json.loads((q/'manifest.json').read_text())
   for name,row in qm['artifacts'].items():
    f=q/name
    if f.stat().st_size!=row['bytes']or digest(f)!=row['sha256']:raise ValueError('integer artifact SHA')
   target.extend(p for p in q.rglob('*')if p.is_file());target.append(root/(model+'-independent01.json'));metadata.extend(p for p in q.iterdir()if p.suffix=='.json');metadata.append(root/(model+'-independent01.json'))
 for phase in ['phase5','phase8','phase9','phase13','phase14']:
  files=[p for p in (root/phase).rglob('*')if p.is_file()and p.suffix in ['.py','.json','.sh']and'wheels'not in p.parts]
  primary.extend(files);holdout.extend(files);metadata.extend(files)
 for run in ['run01','run02']:metadata.extend(p for p in (root/run).rglob('*')if p.is_file())
 metadata.extend(p for p in root.glob('*.log')if p.is_file());metadata.extend([root/'batch-summary-final.json',root/'execution-ledger.tsv',root/'modern-freeze-final.txt',root/'review-samples01.zip',root/'review-readback01.json',root/'phi-sealed-receipt.json',root/'negative-real01/negative-receipt.json',root/'negative-real01/integer-rejected.log',root/'negative-real01/export-rejected.log'])
 primary.extend([root/'batch-summary-final.json',root/'review-samples01.zip',root/'review-readback01.json'])
 large=archive(root,root/'primary-model-data01.zip',primary,'Original BF16-derived FP32 actual captures, software integer probes and strict v1 exports for3primary models. No full weights, no Phi. Scope/float fallbacks remain in manifests.')
 sealed=archive(root,root/'phi-reserved02-sealed.zip',holdout,'Reserved Phi reference capture and full-call strict export. No quantization quality/tuning. Original raw capture unchanged from sealed01.')
 receipt={'status':'PASS','source_commit':b['commit'],'source_binding_sha256':digest(a.binding),'collection_job':os.environ['SLURM_JOB_ID'],'host':platform.node(),'primary_data':large,'reserved_holdout':sealed,'review':{'path':str(root/'review-samples01.zip'),'bytes':(root/'review-samples01.zip').stat().st_size,'sha256':digest(root/'review-samples01.zip')},'full_model_quality_accepted':False,'target_hardware_validated':False,'scope':'all planned CPU capture, selected integer/reference readback and strict source exports executed; errors/remaining physical/application validation explicit'}
 save(root/'batch-data-receipt.json',receipt);metadata.append(root/'batch-data-receipt.json');small=archive(root,root/'batch-metadata01.zip',metadata,'Metadata+compact actual samples only. Large exact raw/integer/strict payloads in primary_data/reserved_holdout archives indexed by batch-data-receipt.json.')
 save(root/'batch-return-receipt.json',{'status':'PASS','source_commit':b['commit'],'metadata_archive':small,'data_receipt_sha256':digest(root/'batch-data-receipt.json')});print(json.dumps({'status':'PASS','metadata':small,'data':receipt}))
if __name__=='__main__':main()
