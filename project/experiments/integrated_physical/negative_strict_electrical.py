"""Full electrical report errors reject after real payload and manifest changes."""
import argparse,os,shutil,copy,re
from common import *
from strict_electrical_audit import receive_strict
p=argparse.ArgumentParser();p.add_argument('--stage',type=Path,required=True);p.add_argument('--strict',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(exist_ok=False);baseline=receive_strict(a.stage,a.strict);need(not baseline['all_electrical_maxima_met'],'actual failure baseline');records=[]
for tag in('erase_small_cap_exceedance','raise_one_actual_cap_limit','boolean_closure_as_integer'):
 out=a.out/tag;out.mkdir();m=copy.deepcopy(artifacts(a.strict));changed='receipt.json'if tag=='boolean_closure_as_integer'else'probe.log'
 for q in a.strict.iterdir():
  if q.is_file()and q.name!='manifest.json':
   if q.name==changed:shutil.copyfile(q,out/q.name)
   else:os.link(q,out/q.name)
 f=out/changed
 if tag=='boolean_closure_as_integer':d=load(f);d['all_electrical_maxima_met']=0;put(f,d)
 else:
  s=f.read_text();start=s.index('BEGIN_FULL_max_capacitance_1');end=s.index('END_FULL_max_capacitance_1');part=s[start:end];lines=part.splitlines(keepends=True);idx=next(i for i,l in enumerate(lines)if'(VIOLATED)'in l and abs(float(l.split()[-2]))<1);old=lines[idx]
  if tag=='erase_small_cap_exceedance':lines[idx]=''
  else:t=old.split();t[1]=str(float(t[1])+10);lines[idx]=' '.join(t)+'\n'
  f.write_text(s[:start]+''.join(lines)+s[end:]);need(f.read_text()!=s,'actual full report mutation')
 manifest(out,m)
 try:receive_strict(a.stage,out)
 except ValueError as e:records.append({'case':tag,'rejected_by':str(e),'changed_sha256':sha(f),'rehashed_manifest_sha256':sha(out/'manifest.json')})
 else:raise ValueError('invalid actual full electrical evidence accepted '+tag)
put(a.out/'receipt.json',{'status':'PASS_THREE_ACTUAL_REHASHED_FULL_ELECTRICAL_CORRUPTIONS_REJECTED','source':sources(),'records':records});print('PASS_THREE_ACTUAL_REHASHED_FULL_ELECTRICAL_CORRUPTIONS_REJECTED')
