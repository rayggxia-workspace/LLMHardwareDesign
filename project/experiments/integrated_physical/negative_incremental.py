"""Rehashed actual dirty-log and recipe corruption must fail semantic audit."""
import argparse,copy,os,shutil,re
from common import *
from incremental_audit import audit_incremental
p=argparse.ArgumentParser();p.add_argument('--stage',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(exist_ok=False);sm=artifacts(a.stage);prev=Path(sm['previous_directory']);base=a.out/'baseline';base.mkdir();audit_incremental(a.stage,prev,base);ledger=load(base/'incremental-change-ledger.json');newnet=ledger['created_nets'][0];records=[]
for tag in('erase_new_net_all_dirty_batches','add_full_reroute_tail','boolean_incremental_flag','erase_changed_pin_RC'):
 out=a.out/tag;out.mkdir();stage=out/'stage';stage.mkdir();m=copy.deepcopy(sm);changed={'erase_new_net_all_dirty_batches':'flow.log','add_full_reroute_tail':'flow.tcl','erase_changed_pin_RC':'route.spef'}.get(tag)
 for q in a.stage.iterdir():
  if q.is_file()and q.name!='manifest.json':
   if q.name==changed:shutil.copyfile(q,stage/q.name)
   else:os.link(q,stage/q.name)
 if tag=='erase_new_net_all_dirty_batches':
  f=stage/changed;s=f.read_text();new='\n'.join(x for x in s.split('\n')if not re.fullmatch(r'\[DEBUG GRT-incr\]  '+re.escape(newnet),x));need(new!=s,'actual all-batch new-net deletion');f.write_text(new)
 elif tag=='add_full_reroute_tail':
  f=stage/changed;f.write_text(f.read_text()+'\nglobal_route -congestion_iterations 50\n')
 elif tag=='boolean_incremental_flag':m['incremental_only']=1
 else:
  q=ledger['unlogged_reconnected_same_segments_regenerated_RC'][0];n=q['net'];f=stage/changed;s=f.read_text();pattern=r'(?ms)^\*D_NET '+re.escape(n)+r' (\S+)\n(.*?)^\*END\s*$';before=re.search(pattern,(prev/'route.spef').read_text());after=re.search(pattern,s);need(before and after,'actual explicit RC section');f.write_text(s[:after.start()]+before[0]+s[after.end():])
 manifest(stage,m);recv=out/'receive';recv.mkdir()
 try:audit_incremental(stage,prev,recv)
 except ValueError as e:records.append({'case':tag,'rejected_by':str(e),'rehashed_manifest_sha256':sha(stage/'manifest.json')})
 else:raise ValueError('corrupted incremental payload accepted '+tag)
put(a.out/'receipt.json',{'status':'PASS_FOUR_ACTUAL_REHASHED_INCREMENTAL_CORRUPTIONS_REJECTED','source':sources(),'records':records});print('PASS_FOUR_ACTUAL_REHASHED_INCREMENTAL_CORRUPTIONS_REJECTED')
