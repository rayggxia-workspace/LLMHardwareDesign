"""Collect Issue66 fixed server evidence and small actual coded samples; no weights download or PPA claim."""
import argparse,hashlib,io,json,os,re,zipfile
from pathlib import Path
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb')as f:
  for b in iter(lambda:f.read(8<<20),b''):h.update(b)
 return h.hexdigest()
def load(p):return json.loads(Path(p).read_text())
def save(p,x):Path(p).write_text(json.dumps(x,indent=2,allow_nan=False)+'\n',newline='\n')
def desc(p):return {'bytes':p.stat().st_size,'sha256':sha(p)}
def checked_manifest(folder):
 m=load(folder/'manifest.json')
 if m['status']!='PASS':raise ValueError('source stage not PASS '+str(folder))
 for name,r in m['artifacts'].items():
  f=folder/name
  if desc(f)!={'bytes':r['bytes'],'sha256':r['sha256']}:raise ValueError('artifact '+str(f))
 return m
def subset(source,dest,keys):
 dest.parent.mkdir(parents=True,exist_ok=True);members={}
 with zipfile.ZipFile(source)as src,zipfile.ZipFile(dest,'x',compression=zipfile.ZIP_DEFLATED)as z:
  for key in keys:
   name=key+'.npy';raw=src.read(name);info=zipfile.ZipInfo(name,(2026,10,24,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;z.writestr(info,raw)
   members[name]={'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
 return members
def archive(dest,files):
 index={}
 with zipfile.ZipFile(dest,'x',compression=zipfile.ZIP_STORED,allowZip64=True)as z:
  for name,source in sorted(files.items()):
   index[name]=desc(source);z.write(source,name)
  z.writestr('artifact-index.json',json.dumps({'files':index},indent=2)+'\n')
 return {**desc(dest),'path':str(dest),'members':len(index)+1}
def main():
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--binding',type=Path,required=True);a=p.parse_args()
 if a.out.exists():raise ValueError('refuse overwrite')
 root=a.root.resolve()
 if not str(root).startswith('/public/home/yuzelu/RuizhiLiang/issue66-')or a.out.resolve().parent!=root:raise ValueError('authorized root/output')
 bind=load(a.binding)
 if sha(__file__)!=bind['collect_sha256']:raise ValueError('collector source binding')
 names=['legacy01','capture01','conv01','conv02','consumer01','consumer02','state01','state02','legacy-state01','legacy-state02','coupled01','coupled02','long-state01','long-state02','norm01','norm02','norm03','norm04']
 manifests={name:checked_manifest(root/name)for name in names}
 for first,second in [('conv01','conv02'),('consumer01','consumer02'),('state01','state02'),('legacy-state01','legacy-state02'),('coupled01','coupled02'),('long-state01','long-state02'),('norm01','norm02'),('norm03','norm04')]:
  one,two=manifests[first]['artifacts'],manifests[second]['artifacts']
  if one!=two:raise ValueError('science round difference '+first)
 # New finite-buffer ledger does not retroactively modify old runs; every NPZ remains equal.
 for name,r in manifests['norm01']['artifacts'].items():
  if name.endswith('.npz')and r!=manifests['norm03']['artifacts'][name]:raise ValueError('norm numeric change '+name)
 audits={'conv':root/'receive-conv01/receipt.json','state':root/'receive-state01/audit.json','consumer':root/'receive-consumer01.json','extra':root/'receive-extra01/audit-extra.json','norm':root/'receive-norm01.json'}
 for name,path in audits.items():
  if load(path).get('status') not in ('PASS','PASS_INDEPENDENT_ARITHMETIC','PASS_INDEPENDENT_ACCEPTANCE'):raise ValueError('independent audit '+name)
 a.out.mkdir();selection=a.out/'selection';selection.mkdir()
 rows=load(root/'state01/state-results.json');smeta={'schema':'issue66-selected/1','state_capture_manifest_sha256':manifests['state01']['source']['input_manifest_sha256'],'states':[],'consumer':{},'scope':'actual original coded arrays/selected outcomes; no native compiler/full upstream or all conditions accepted by this selected archive alone; complete audits/data remain server'}
 skeys=['q','k','v','beta','decay','state_initial','state_trace','output_codes','state_units','value_units']
 for label in ['evaluation.S16.D15','evaluation.S32.D31']:
  row=next(r for r in rows if r['id']==label);name=label+'.npz';relative='selected/states/'+name
  members=subset(root/'state01'/name,selection/relative,skeys)
  smeta['states'].append({'path':relative,'artifact':desc(selection/relative),'record':row,'original_artifact':manifests['state01']['artifacts'][name],'members':members})
 auxkeys=['down.Ybase','next.W8','next.We','next.Ybase','next.raw_norm_weight','decode.down.acc','decode.down.e0']+['decode.reference.'+k for k in ['down','residual','sum','norm','projection','rows']]
 relative='selected/consumer-aux.npz';members=subset(root/'consumer01/common.npz',selection/relative,auxkeys)
 smeta['consumer']['auxiliary']={'path':relative,'artifact':desc(selection/relative),'original_common':manifests['consumer01']['artifacts']['common.npz'],'members':members}
 smeta['consumer']['samples']=[]
 for label in ['decode.tile16_delta_ACT8','decode.delta_to_K128_ACT8']:
  name=label+'.npz';relative='selected/consumer/'+name;(selection/relative).parent.mkdir(parents=True,exist_ok=True);(selection/relative).write_bytes((root/'consumer01'/name).read_bytes())
  case,profile=label.split('.',1);row=next(r for r in load(root/'consumer01/consumer.json')if r['case']==case and r['profile']==profile)
  smeta['consumer']['samples'].append({'path':relative,'record':row,'original_artifact':manifests['consumer01']['artifacts'][name]})
 smeta['sources']={k:v for k,v in bind['sources'].items()if k.endswith(('receive_state.py','consumer_receive.py'))}
 save(selection/'selected.json',smeta)
 full={};selected={}
 def add(target,p,name=None):target[name or str(p.relative_to(root))]=p
 for name in names:
  for f in (root/name).iterdir():
   if f.is_file():add(full,f)
   if f.suffix=='.json':add(selected,f)
 for folder in root.iterdir():
  if folder.is_dir()and re.fullmatch(r'phase\d+[a-z]?',folder.name):
   for f in folder.rglob('*'):
    if f.is_file():add(full,f);add(selected,f)
 for p in root.glob('*.log'):add(full,p);add(selected,p)
 for name,path in audits.items():add(full,path);add(selected,path)
 for p in root.rglob('*'):
  if p.is_file()and any(parent.name.startswith(('receive-','rehashed-'))for parent in p.parents if parent!=root)and p.suffix=='.json':
   add(full,p);add(selected,p)
 for p in selection.rglob('*'):
  if p.is_file():add(selected,p,str(p.relative_to(selection)))
 fullmeta=archive(a.out/'full-results01.zip',full);selectedmeta=archive(a.out/'selected-evidence01.zip',selected)
 save(a.out/'delivery.json',{'status':'PASS','collector_commit':bind['commit'],'root':str(root),'full':fullmeta,'selected':selectedmeta,'scope':'two scientific rounds, capture, source snapshots, independent receipts; original complete weights excluded; negative numeric payloads stay in their indexed server paths, not duplicated all in archive','selected_scope':smeta['scope'],'sources':{k:v.get('source_commit',v.get('source',{}).get('commit'))for k,v in manifests.items()},'not_accepted':['complete model integer quality','target hardware speed/RTL/PPA','all48 legacy integer independent replay (only3 full256 witnesses)']})
 print(json.dumps({'status':'PASS','full':fullmeta,'selected':selectedmeta}),flush=True)
if __name__=='__main__':main()
