"""Full-group mixed-domain supplement; archive separately from frozen main delivery."""
import argparse,hashlib,json,zipfile
from pathlib import Path
import numpy as np
from reference import step,Refusal
from verify import check_artifacts,SNAP
from inputs import put,sha
ROOT=Path(__file__).resolve().parents[3]
NAMES=('mixed_shift_high_low','mixed_shift_low_high')
def main():
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--fixtures',type=Path,required=True);p.add_argument('--runs',nargs=2,type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--git-proof',type=Path,required=True);a=p.parse_args();assert a.root.resolve()==Path('/public/home/yuzelu/RuizhiLiang/issue104-gdn-state-20261025');a.out.mkdir(parents=True,exist_ok=False);bd=json.loads((ROOT/'binding.json').read_text())
 for n,h in bd['sources'].items():assert sha(ROOT/n)==h,n
 proof=json.loads(a.git_proof.read_text());assert proof['commit']==bd['commit']and proof['source_zip_sha256']==sha(ROOT/'source.zip')
 for n,e in proof['files'].items():assert sha(ROOT/n)==e['sha256']and(ROOT/n).stat().st_size==e['bytes']
 mainindex=a.root/'delivery01/index.json';mainbytes=json.loads((a.root/'delivery01/full-byte-receipt.json').read_text());assert mainbytes['status']=='PASS_ARCHIVE_AND_ORIGINAL_GIT_BYTES'and mainbytes['index_sha256']==sha(mainindex)
 seen=set();results=[]
 for runroot in a.runs:
  br=json.loads((runroot/'receipt.json').read_text());assert br['status']=='PASS_ALL_FULL_GROUP_BOUNDARIES'and {x['name']for x in br['cases']}==set(NAMES)
  stall=br['stall'];assert stall in(0,1)and stall not in seen;seen.add(stall)
  for name in NAMES:
   inp=a.fixtures/name;im=json.loads((inp/'manifest.json').read_text());check_artifacts(inp,im)
   with np.load(inp/'coefficients.npz',allow_pickle=False)as z:
    assert np.any(z['state_initial']!=0)and np.any(z['initial_output']!=0),'nonzero publication witness'
    shifts=(z['state_units'].astype(int)-z['value_units'].astype(int)).tolist();assert shifts==([63,-33]if name==NAMES[0]else[-33,63])
    try:step(z['state_initial'],z['q'][0],z['k'][0],z['v'][0],z['decay'][0],z['beta'][0],z['state_units'],z['value_units'],im['epoch'])
    except Refusal as e:assert e.code==12 and e.attempts==[],'independent E_FORMAT before any retry'
    else:raise AssertionError('missing refusal')
   folder=runroot/(name+'-run');rm=json.loads((folder/'manifest.json').read_text());check_artifacts(folder,rm);receipt=json.loads((runroot/(name+'-recv')/'receipt.json').read_text());assert receipt['status']=='PASS_COMPLETE_INTEGER_RTL_NOT_PPA'and receipt['run_manifest_sha256']==sha(folder/'manifest.json')and receipt['input_manifest_sha256']==sha(inp/'manifest.json')
   rows=[json.loads(x)for x in(folder/'actual.jsonl').read_text().splitlines()];raw=(folder/'actual.bin').read_bytes();assert len(rows)==2 and len(raw)==2*SNAP and raw[:SNAP]==raw[SNAP:],'published root/meta/fullstate/fullY unchanged'
   assert rows[0]['status']==0 and rows[1]['status']==12 and rows[1]['state_validated']==1
   for key in('retries','mul','wide_calls','offer_hold'):assert rows[1][key]==0,(name,key)
   assert(folder/'stages.bin').stat().st_size==0,'no arithmetic stages or output work'
   for n,h in bd['sources'].items():
    if n.startswith('project/rtl/')or n.endswith('/gdn_sim.cpp'):assert rm['source']['sources'].get(n)==h,'same old hardware and driver'
   results.append({'case':name,'stall':stall,'shifts':shifts,'status':12,'retries':0,'new_epoch_waves':0,'full_published_bytes_unchanged':SNAP,'state_codes_checked':32768,'Y_codes_checked':256,'cycles':rows[1]['cycles'],'run_manifest_sha256':sha(folder/'manifest.json'),'receiver_receipt_sha256':sha(runroot/(name+'-recv')/'receipt.json')})
 assert seen=={0,1}
 result={'schema':'gdn104-format-priority-v1','status':'PASS_MIXED_DOMAIN_PRIORITY_FULL_GROUP_UNCHANGED','source':bd,'main_index_sha256':sha(mainindex),'main_hardware_unchanged':True,'reference_change':'whole-group aligned shift>62 E_FORMAT before any per-head fmt/WIDTH retry, at every attempt','cases':results,'limits':['no new RTL/map/gate','does not turn original main archive reference into corrected version; supplement is explicit','new contract priority, not original68 exception ordering']};put(a.out/'receipt.json',result)
 items=[]
 for directory in[ROOT,a.fixtures,*a.runs]:
  for file in sorted(directory.rglob('*')):
   if file.is_file():items.append((file,file.relative_to(a.root).as_posix()))
 items.extend([(a.git_proof,'original-git-source.json'),(a.out/'receipt.json','receipt.json')])
 names=[name for _,name in items];assert len(names)==len(set(names))
 entries=[];selected=[]
 with zipfile.ZipFile(a.out/'full.zip','x',compression=zipfile.ZIP_DEFLATED,compresslevel=4)as z,zipfile.ZipFile(a.out/'selected.zip','x',compression=zipfile.ZIP_DEFLATED,compresslevel=6)as q:
  for file,name in items:
   data=file.read_bytes();e={'path':name,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()};z.writestr(name,data);entries.append(e)
   if file.suffix in('.json','.jsonl','.py','.sv','.cpp','.md','.log')and file.name not in('sim.log',):q.writestr(name,data);selected.append(e)
  for archive,arr,kind in[(z,entries,'full'),(q,selected,'selected')]:archive.writestr('MANIFEST.json',json.dumps({'schema':'gdn104-format-priority-archive-v1','kind':kind,'source':bd,'files':arr},indent=2,sort_keys=True)+'\n')
 ix={'schema':'gdn104-format-priority-index-v1','status':'ARCHIVED_FOR_BYTE_CHECK','source':bd,'receipt_sha256':sha(a.out/'receipt.json'),'main_index_sha256':sha(mainindex),'full':{'bytes':(a.out/'full.zip').stat().st_size,'sha256':sha(a.out/'full.zip'),'path':str(a.out/'full.zip'),'entries':len(entries)},'selected':{'bytes':(a.out/'selected.zip').stat().st_size,'sha256':sha(a.out/'selected.zip'),'path':str(a.out/'selected.zip'),'entries':len(selected)}};put(a.out/'index.json',ix);print(json.dumps(result))
if __name__=='__main__':main()
