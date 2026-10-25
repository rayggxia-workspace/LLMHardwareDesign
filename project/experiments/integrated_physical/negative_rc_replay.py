"""Positive CAP and erased-report corruptions rejected beyond caller metadata."""
import argparse,copy,os,shutil,re
from decimal import Decimal
from common import *
from rc_replay_audit import audit_replay
p=argparse.ArgumentParser();p.add_argument('--stage',type=Path,required=True);p.add_argument('--replay',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(exist_ok=False);base=a.out/'baseline';base.mkdir();audit_replay(a.stage,a.replay,base);records=[]
for tag in('positive_CAP_changed','nonzero_cap_section_erased','whole_electrical_report_erased'):
 out=a.out/tag;out.mkdir();stage=out/'stage';stage.mkdir();rep=out/'replay';rep.mkdir();sm=copy.deepcopy(artifacts(a.stage));rm=copy.deepcopy(artifacts(a.replay));changed='route.spef'if tag=='positive_CAP_changed'else'flow.log'
 for folder,new,modify in [(a.stage,stage,changed),(a.replay,rep,None)]:
  for q in folder.iterdir():
   if q.is_file()and q.name!='manifest.json':
    if q.name==modify:shutil.copyfile(q,new/q.name)
    else:os.link(q,new/q.name)
 f=stage/changed;s=f.read_text()
 if tag=='positive_CAP_changed':
  st=s.index('*CAP\n')+5;en=s.index('\n',st);t=s[st:en].split();t[-1]=str(Decimal(t[-1])+Decimal('0.1'));new=s[:st]+' '.join(t)+s[en:]
 else:
  st=s.index('BEGIN_ELECTRICAL_REPORT')+len('BEGIN_ELECTRICAL_REPORT');en=s.index('END_ELECTRICAL_REPORT',st);part=s[st:en]
  if tag=='whole_electrical_report_erased':part='\n'
  else:need('max capacitance'in part and'(VIOLATED)'in part,'baseline actual cap violations');part=part.split('max capacitance',1)[0]
  new=s[:st]+part+s[en:]
 need(new!=s,'actual mutation');f.write_text(new);manifest(stage,sm)
 # Deliberately update caller-level hashes too; unchanged actual replay must still reject payload/count.
 rm.update(stage_directory=str(stage),stage_manifest_sha256=sha(stage/'manifest.json'),inputs={n:sha(stage/n)for n in rm['inputs']},original_spef_sha256=sha(stage/'route.spef'));manifest(rep,rm);reception=out/'receive';reception.mkdir()
 try:audit_replay(stage,rep,reception)
 except ValueError as e:records.append({'case':tag,'rejected_by':str(e),'changed_sha256':sha(f),'rehashed_stage_manifest_sha256':sha(stage/'manifest.json'),'rehashed_replay_manifest_sha256':sha(rep/'manifest.json')})
 else:raise ValueError('corrupted actual evidence accepted '+tag)
put(a.out/'receipt.json',{'status':'PASS_THREE_ACTUAL_REHASHED_RC_AND_REPORT_CORRUPTIONS_REJECTED','source':sources(),'resources':resource_snapshot(),'records':records});print('PASS_THREE_ACTUAL_REHASHED_RC_AND_REPORT_CORRUPTIONS_REJECTED')
