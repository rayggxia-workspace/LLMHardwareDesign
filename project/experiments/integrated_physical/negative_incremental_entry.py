"""Real receive_route entry rejects rehashed flag/source substitutions before audit."""
import argparse,copy,os,sys,subprocess
from common import *
p=argparse.ArgumentParser();p.add_argument('--stage',type=Path,required=True);p.add_argument('--prepared',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(exist_ok=False);sm=artifacts(a.stage);previous=Path(sm['previous_directory']);old=artifacts(previous);records=[]
def clone(src,dst,m):
 dst.mkdir()
 for f in src.iterdir():
  if f.is_file() and f.name!='manifest.json':os.link(f,dst/f.name)
 manifest(dst,m)
for tag in ('flag_integer','flag_false','flag_missing','rehashed_alternate_source'):
 d=a.out/tag;d.mkdir();m=copy.deepcopy(sm)
 if tag=='flag_integer':m['incremental_only']=1
 elif tag=='flag_false':m['incremental_only']=False
 elif tag=='flag_missing':del m['incremental_only']
 else:
  om=copy.deepcopy(old);om['negative_added_source_metadata']='different candidate4 source despite intact payload'
  clone(previous,d/'previous',om);m['previous_directory']=str(d/'previous');m['previous_manifest_sha256']=sha(d/'previous/manifest.json')
 clone(a.stage,d/'stage',m)
 cmd=[sys.executable,'-B',str(HERE/'receive_route.py'),'--target','97','--prepared',str(a.prepared),'--stage',str(d/'stage'),'--out',str(d/'receiver')]
 r=subprocess.run(cmd,capture_output=True,text=True,timeout=120);(d/'stdout.log').write_text(r.stdout);(d/'stderr.log').write_text(r.stderr)
 expected='exact frozen incremental source SHA' if tag=='rehashed_alternate_source' else 'known incremental candidate requires strict true flag'
 need(r.returncode!=0 and expected in r.stderr and not(d/'receiver/receipt.json').exists(),'actual entry rejects the intended semantic corruption '+tag)
 records.append({'case':tag,'argv':cmd,'exit':r.returncode,'rejected_by':expected,'stage_manifest_sha256':sha(d/'stage/manifest.json'),'stderr_sha256':sha(d/'stderr.log')})
put(a.out/'receipt.json',{'status':'PASS_FOUR_REHASHED_ENTRY_FLAG_AND_SOURCE_SUBSTITUTIONS_REJECTED','source':sources(),'baseline_stage_manifest_sha256':sha(a.stage/'manifest.json'),'records':records});print('PASS_FOUR_REHASHED_ENTRY_FLAG_AND_SOURCE_SUBSTITUTIONS_REJECTED')
