"""Real rehashed detailed RC and geometry corruptions must fail independently."""
import argparse,os,shutil,copy,re
from decimal import Decimal
from common import *
from detail_spef import audit_spef
from detail_ledger import audit_ledger
p=argparse.ArgumentParser();p.add_argument('--stage',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(exist_ok=False);sm=artifacts(a.stage);net=load(a.stage/'final.json')['modules']['chain93'];audit_spef(a.stage,net);audit_ledger(a.stage,net);records=[]
for tag in('positive_ground_cap','missing_mirrored_coupling','unknown_actual_via','missing_physical_terminal'):
 stage=a.out/tag;stage.mkdir();name='route.spef'if tag in('positive_ground_cap','missing_mirrored_coupling')else'placed.def'
 for q in a.stage.iterdir():
  if q.is_file()and q.name!='manifest.json':
   if q.name==name:shutil.copyfile(q,stage/q.name)
   else:os.link(q,stage/q.name)
 f=stage/name;s=f.read_text()
 if tag=='positive_ground_cap':
  m=re.search(r'(?m)^\d+ \*\S+ [0-9.eE+-]+$',s[s.index('*CAP\n')+5:]);need(m,'actual ground cap');start=s.index('*CAP\n')+5+m.start();end=s.index('*CAP\n')+5+m.end();t=m[0].split();t[-1]=str(Decimal(t[-1])+Decimal('.01'));new=s[:start]+' '.join(t)+s[end:]
 elif tag=='missing_mirrored_coupling':
  m=re.search(r'(?m)^\d+ \*\S+ \*\S+ [0-9.eE+-]+\n',s);need(m,'actual coupling record');new=s[:m.start()]+s[m.end():]
 elif tag=='unknown_actual_via':need(' via1_4'in s,'actual via present');new=s.replace(' via1_4',' invalid_via98',1)
 else:
  start=s.index('\nNETS ');m=re.search(r'\( _\d+_ D \)',s[start:]);need(m,'actual FF D terminal');st=start+m.start();en=start+m.end();new=s[:st]+s[en:]
 need(new!=s,'actual mutation');f.write_text(new);manifest(stage,copy.deepcopy(sm));artifacts(stage)
 try:(audit_spef if name=='route.spef'else audit_ledger)(stage,net)
 except ValueError as e:records.append({'case':tag,'rejected_by':str(e),'changed_sha256':sha(f),'rehashed_manifest_sha256':sha(stage/'manifest.json')})
 else:raise ValueError('actual detailed corruption accepted '+tag)
put(a.out/'receipt.json',{'status':'PASS_FOUR_ACTUAL_REHASHED_DETAILED_RC_AND_GEOMETRY_CORRUPTIONS_REJECTED','source':sources(),'records':records});print('PASS_FOUR_ACTUAL_REHASHED_DETAILED_RC_AND_GEOMETRY_CORRUPTIONS_REJECTED')
