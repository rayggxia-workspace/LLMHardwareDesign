"""Real two-load same-pin deletion/substitution with matching receipt/hash updates."""
import argparse,copy,hashlib,os,re,shutil
from common import *
from strict_electrical_audit import receive_strict
p=argparse.ArgumentParser();p.add_argument('--stage',type=Path,required=True);p.add_argument('--strict',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(exist_ok=False);baseline=receive_strict(a.stage,a.strict);records=[]
for tag in('delete_same_real_driver_both_loads','substitute_same_fake_driver_both_loads'):
 out=a.out/tag;out.mkdir();m=copy.deepcopy(artifacts(a.strict))
 for f in a.strict.iterdir():
  if f.is_file()and f.name!='manifest.json':
   if f.name in('probe.log','receipt.json'):shutil.copyfile(f,out/f.name)
   else:os.link(f,out/f.name)
 s=(out/'probe.log').read_text();receipt=load(out/'receipt.json');pin=None
 for k,scenario in zip((1,10),receipt['scenarios']):
  begin=f'BEGIN_FULL_max_slew_{k}';end=f'END_FULL_max_slew_{k}';start=s.index(begin)+len(begin);stop=s.index(end,start);section=s[start:stop];lines=section.splitlines(keepends=True)
  if pin is None:pin=next(l.split()[0]for l in lines if re.match(r'^\S+\s+[-+0-9.eE]+\s+[-+0-9.eE]+\s+[-+0-9.eE]+\s+\((MET|VIOLATED)\)',l))
  indices=[i for i,l in enumerate(lines)if l.split()and l.split()[0]==pin];need(len(indices)==1,'same actual driver appears once per load');i=indices[0]
  if tag.startswith('delete'):lines[i]='';scenario['checks']['max_slew']['checked_pins']-=1
  else:lines[i]=lines[i].replace(pin,'nonexistent_slew_driver/Z',1)
  part=''.join(lines);s=s[:start]+part+s[stop:];scenario['checks']['max_slew']['report_sha256']=hashlib.sha256(part.encode()).hexdigest()
 (out/'probe.log').write_text(s);put(out/'receipt.json',receipt);manifest(out,m)
 try:receive_strict(a.stage,out)
 except ValueError as e:
  need('complete exact slew driver set'in str(e),'rejected by actual independent coverage check');records.append({'case':tag,'original_pin':pin,'rejected_by':str(e),'probe_sha256':sha(out/'probe.log'),'receipt_sha256':sha(out/'receipt.json'),'manifest_sha256':sha(out/'manifest.json')})
 else:raise ValueError('actual double-load corrupted coverage accepted')
put(a.out/'receipt.json',{'status':'PASS_REHASHED_TWO_LOAD_SAME_PIN_SLEW_CORRUPTIONS_REJECTED','source':sources(),'baseline':baseline,'records':records});print('PASS_REHASHED_TWO_LOAD_SAME_PIN_SLEW_CORRUPTIONS_REJECTED')
