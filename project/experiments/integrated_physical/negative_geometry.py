"""Persisted rehashed real DEF and tie corruption, rejected independently."""
import argparse,shutil,re
from common import *
from receive_physical import audit
p=argparse.ArgumentParser();p.add_argument('--prepared',type=Path,required=True);p.add_argument('--stage',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(exist_ok=False);b=a.out/'baseline';b.mkdir();audit(a.stage,a.prepared,b);cases=[]
for label,expected in [('pin_track','pin on actual routing track'),('cell_overlap','independent row overlap'),('net_connection','all cell and IO DEF connection coverage'),('tie_value','function')]:
 folder=a.out/label;shutil.copytree(a.stage,folder);m=load(folder/'manifest.json')
 if label=='tie_value':
  f=folder/'final.json';j=load(f);cells=j['modules']['chain93']['cells'];n=next(n for n,c in cells.items()if c['type']=='LOGIC0_X1');cells[n]['type']='LOGIC1_X1';put(f,j)
 else:
  f=folder/'placed.def';s=f.read_text()
  if label=='pin_track':
   start=s.index('\nPINS ');tail=s[start:];m0=re.search(r'\+ (?:PLACED|FIXED) \(\s*(\d+) (\d+) \) N',tail);need(m0 is not None,'baseline physical pin');prefix=tail[:m0.start()];layer=re.findall(r'\+ LAYER (metal[56])',prefix)[-1];coord=2 if layer=='metal5'else 1;i,j=m0.span(coord);tail=tail[:i]+str(int(m0[coord])+1)+tail[j:];s=s[:start]+tail
  elif label=='cell_overlap':
   start=s.index('\nCOMPONENTS ');end=s.index('END COMPONENTS',start);tail=s[start:end];matches=list(re.finditer(r'\+ PLACED \(\s*(-?\d+) (-?\d+) \) (N|FS|S|FN)',tail));need(len(matches)>2,'baseline placed cells');a0,a1=matches[:2];tail=tail[:a1.start()]+a0[0]+tail[a1.end():];s=s[:start]+tail+s[end:]
  else:
   start=s.index('\nNETS ');tail=s[start:];m0=re.search(r'\( (?!PIN )(\S+) (\S+) \)',tail);need(m0 is not None,'baseline connected cellpin');tail=tail[:m0.start()]+tail[m0.end():];s=s[:start]+tail
  f.write_text(s)
 manifest(folder,m);recv=a.out/(label+'-receive');recv.mkdir()
 try:audit(folder,a.prepared,recv)
 except ValueError as e:need(expected in str(e),'wrong negative reason '+label+': '+str(e));cases.append({'case':label,'expected':expected,'actual':str(e),'changed_file':f.name,'changed_sha256':sha(f),'manifest_sha256':sha(folder/'manifest.json')})
 else:raise ValueError('malformed actual geometry/tie accepted '+label)
put(a.out/'receipt.json',{'status':'PASS_PERSISTED_REHASHED_GEOMETRY_CONSTANT_NEGATIVES','source':sources(),'resources':resource_snapshot(),'baseline_stage_manifest_sha256':sha(a.stage/'manifest.json'),'cases':cases});print('PASS_PERSISTED_REHASHED_GEOMETRY_CONSTANT_NEGATIVES')
