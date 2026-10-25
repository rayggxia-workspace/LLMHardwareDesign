"""Persisted rehashed corruptions must fail independent routed-RC reception."""
import argparse,copy,os,shutil
from common import *
from route_audit import route_audit
from receive_physical import library
p=argparse.ArgumentParser();p.add_argument('--stage',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(exist_ok=False);sm=artifacts(a.stage);previous=Path(sm['previous_directory']);net=load(a.stage/'final.json')['modules']['chain93'];lib=library(LIB);baseline=route_audit(a.stage,previous,net,lib);records=[]
def missing_pin(s):
 start=s.index('*CONN\n');end=s.index('\n',start+6);return s[:start+6]+s[end+1:]
def cap_negative(s):
 start=s.index('*CAP\n')+5;end=s.index('\n',start);tok=s[start:end].split();tok[-1]='-1';return s[:start]+' '.join(tok)+s[end:]
def segment_change(s):
 pos=s.index('\n(\n')+3;end=s.index('\n',pos);tok=s[pos:end].split();tok[0]='99999999';return s[:pos]+' '.join(tok)+s[end:]
def missing_rc_net(s):
 start=s.index('*D_NET');end=s.index('*END',start)+4;return s[:start]+s[end:]
def wrong_wire(s):
 lines=s.splitlines();t=lines[1].split();t[2]=str(float(t[2])+1);lines[1]=' '.join(t);return '\n'.join(lines)+'\n'
def missing_unannotated(s):return s.replace('Found 3580 unannotated drivers.','Found 0 unannotated drivers.',1)
for tag,file,change in [('missing_spef_pin','route.spef',missing_pin),('negative_cap','route.spef',cap_negative),('segment_outside_die','route.segments',segment_change),('missing_rc_net','route.spef',missing_rc_net),('wrong_wire_length','wirelength.csv',wrong_wire),('unannotated_count','flow.log',missing_unannotated)]:
 out=a.out/tag;out.mkdir();meta=copy.deepcopy(sm)
 for q in a.stage.iterdir():
  if q.is_file()and q.name!='manifest.json':
   if q.name==file:shutil.copyfile(q,out/q.name)
   else:os.link(q,out/q.name)
 f=out/file;old=f.read_text();new=change(old);need(old!=new,'negative mutation changes actual evidence');f.write_text(new);manifest(out,meta)
 try:route_audit(out,previous,net,lib)
 except ValueError as e:records.append({'case':tag,'changed_file':file,'changed_sha256':sha(f),'rehashed_manifest_sha256':sha(out/'manifest.json'),'rejected_by':str(e)})
 else:raise ValueError('bad actual route evidence accepted '+tag)
put(a.out/'receipt.json',{'status':'PASS_SIX_ACTUAL_REHASHED_ROUTE_CORRUPTIONS_REJECTED','source':sources(),'resources':resource_snapshot(),'stage_manifest_sha256':sha(a.stage/'manifest.json'),'baseline':{k:v for k,v in baseline.items()if k not in ['unannotated_unused_driver_names']},'negative_records':records});print('PASS_SIX_ACTUAL_REHASHED_ROUTE_CORRUPTIONS_REJECTED')
