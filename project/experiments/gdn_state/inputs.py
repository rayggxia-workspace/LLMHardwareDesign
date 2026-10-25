"""Server-only fixed source verification, original integer checkpoint encoding."""
import argparse,hashlib,io,json,struct,zipfile
from pathlib import Path
import numpy as np
from contracts import CONTRACT
from reference import step
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def put(p,x):Path(p).write_text(json.dumps(x,indent=2,sort_keys=True)+'\n',encoding='utf8',newline='\n')
def image(s,units,vu,ep,pos,ver,z,owner=182389313,context=104):
 a=bytearray(1<<20);a[:131072]=np.asarray(s,dtype='<i4').tobytes()
 w0=0x47444e31|(1<<32)|(owner<<48)|(1<<85)|((int(units[0])&255)<<96)|((int(units[1])&255)<<104)|((int(vu[0])&255)<<112)|((int(vu[1])&255)<<120)
 meta=w0.to_bytes(16,'little')+struct.pack('<QQ',pos,ver)+(int(ep)|(context<<32)).to_bytes(16,'little')+struct.pack('<IIII',0x040b0000,32,0x04000000,0x040a0000)
 a[0xa1000:0xa1040]=meta;a[0xa1080:0xa1090]=(0x47445231|(1<<33)|(ver<<64)).to_bytes(16,'little')
 for t in range(len(z['q'])):
  slot=struct.pack('<IIQ',0x47444331,t,pos+t)+struct.pack('<IIHHI',*map(int,z['decay'][t]),*map(int,z['beta'][t]),0)
  slot+=b''.join(np.asarray(z[k][t],dtype='<i2').tobytes()for k in('q','k','v'));assert len(slot)==1568
  a[0xb0000+t*1568:0xb0000+(t+1)*1568]=slot
 return a

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--profile',choices=['native32','portable12'],required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
 if a.profile=='native32':
  src=Path('/public/home/yuzelu/RuizhiLiang/issue66-scale-state-20261024/state01/evaluation.S32.D31.npz');assert sha(src)=='a590053c5ff559d8d73c501bc5362216d1b79fc7b8d9b5209603adac67cb9b1d'and src.stat().st_size==15926068
  with np.load(src,allow_pickle=False)as n:z={k:n[k].copy()for k in('q','k','v','decay','beta','state_initial','state_units','value_units')}
  pos,ver,ep=128,0,0;s=z['state_initial'];un=z['state_units'];source={'path':str(src),'sha256':sha(src),'bytes':src.stat().st_size};expected=None
 else:
  src=Path('/public/home/yuzelu/RuizhiLiang/issue68-range-service-20261024/portable-r01/portable-r.zip');assert sha(src)=='9c9fda0bb30f0d514a4679353852df9f4d109063c4e3bc9c9c04fc38f24a32f5'and src.stat().st_size==2424317
  with zipfile.ZipFile(src)as bundle:
   selected=json.loads(bundle.read('selected.json'));row=next(x for x in selected['cases']if x['format']['state_bits']==32);raw=bundle.read('selected/S32.npz');assert hashlib.sha256(raw).hexdigest()==row['artifact']['sha256']and len(raw)==row['artifact']['bytes']
   with np.load(io.BytesIO(raw),allow_pickle=False)as n:expected={k:n[k].copy()for k in n.files}
  z={k:expected[k]for k in('q','k','v','decay','beta','value_units')};s=expected['state_trace'][0];un=expected['state_units_trace'][0];pos=row['initial_snapshot']['position'];ver=row['initial_snapshot']['version'];ep=row['initial_snapshot']['epoch'];z.update(state_initial=s,state_units=un);source={'path':str(src),'sha256':sha(src),'bytes':src.stat().st_size,'selected':row['artifact'],'initial_snapshot':row['initial_snapshot']}
 vu=z['value_units'];assert len(z['q'])<=32;(a.out/'image.bin').write_bytes(image(s,un,vu,ep,pos,ver,z));np.savez_compressed(a.out/'coefficients.npz',**z)
 states=[s.copy()];units=[list(map(int,un))];epochs=[ep];outs=[];events=[]
 for t in range(len(z['q'])):
  s,y,un,ep,attempts=step(s,z['q'][t],z['k'][t],z['v'][t],z['decay'][t],z['beta'][t],un,vu,ep)
  states.append(s);outs.append(y);units.append(un.copy());epochs.append(ep);events.append({'slot':t,'retries':len(attempts)-1,'bad':[x['bad']for x in attempts],'maxima':[{k:max(abs(int(v))for v in x.flat)for k,x in att['stages'].items()}for att in attempts]})
  if expected is not None:
   for key,actual in [('state_trace',s),('output_codes',y),('state_units_trace',un),('epoch_trace',ep)]:assert np.array_equal(actual,expected[key][t+(key!='output_codes')]),(t,key)
 np.savez_compressed(a.out/'reference.npz',state_trace=np.array(states),output_codes=np.array(outs),state_units_trace=np.array(units,dtype=np.int8),epoch_trace=np.array(epochs,dtype=np.uint32))
 put(a.out/'reference-events.json',events)
 manifest={'schema':'gdn104-input-v1','contract':CONTRACT,'status':'VERIFIED_COEFFICIENTS_NOT_RTL','profile':a.profile,'position':pos,'version':ver,'epoch':epochs[0],'units':units[0],'value_units':list(map(int,vu)),'steps':len(outs),'source':source,'initial_output':'zero placeholder unused by recurrence; not previous captured Y','independent_integer_reference':True,'portable_original_trace_equal':expected is not None}
 manifest['artifacts']=[{'path':p.name,'sha256':sha(p),'bytes':p.stat().st_size}for p in sorted(a.out.iterdir())if p.is_file()];put(a.out/'manifest.json',manifest);print('VERIFIED_COEFFICIENTS_NOT_RTL',a.profile,len(outs),events)
if __name__=='__main__':main()
