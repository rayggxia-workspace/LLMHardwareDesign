"""Strict zero-delay gate reception; exact row equality, independent real input oracle."""
import argparse,json,shutil
from pathlib import Path
from reference import bound,sha,require,reference,check
ROOT=Path(__file__).resolve().parents[3]
def typed_pilot(p):
 require(set(p)=={'schema','accepted','same_core_no_per_case_reset','held_done','latched_parameters','fabric_high_water'},'exact gate protocol keys');require(p['schema']=='v97-protocol-pilot-v1','protocol schema')
 for k in ('same_core_no_per_case_reset','held_done','latched_parameters'):require(type(p[k])is bool and p[k],'typed pilot flag')
 require(type(p['accepted'])is int and p['accepted']==2 and type(p['fabric_high_water'])is int and p['fabric_high_water']==1,'gate actual two commands one response slot used')
def rows(folder,status):
 m=bound(folder);require(m['status']==status,'artifact status');p=json.loads((folder/'actual.jsonl.protocol.json').read_text());typed_pilot(p);rr=[json.loads(x)for x in(folder/'actual.jsonl').read_text().splitlines()];require(len(rr)==2 and [(x['role'],x['prep_only'],x['epoch'])for x in rr]==[('prep-pilot',True,1),('chain-pilot',False,2)],'selected mapped replay cardinality');return m,rr

def main():
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(exist_ok=False);binding=json.loads((ROOT/'binding.json').read_text())
 for n,h in binding['sources'].items():require(sha(ROOT/n)==h,'gate receiver source')
 gr=a.root/'gateprep01';gb=a.root/'gatebuild01';mr=a.root/'map01';im=a.root/'input02';rb=a.root/'build04p';gm=bound(gr);bm=bound(gb);mm=bound(mr);rbuild=bound(rb);bound(im)
 require(gm['status']=='EXACT_MAPPED97_LOGIC_EXPORTED'and bm['status']=='GATE97_BUILT_NOT_EXECUTED'and mm['status']=='LOGIC_ONLY_MAPPED_NOT_PPA','exact prepare/build/map status');require(gm['mapping_manifest_sha256']==sha(mr/'manifest.json')and bm['prepared_manifest_sha256']==sha(gr/'manifest.json'),'map→prepared→binary binding');require(sha(gb/'obj/Vchain97')==bm['binary_sha256']and sha(rb/'obj/Vchain97')==rbuild['binary_sha256'],'binary SHA');require(sha(gr/'mapped.json')==sha(mr/'mapped.json'),'unchanged mapped cells')
 for n,h in mm['source']['sources'].items():
  if n.startswith('project/rtl/'):require(gm['source']['sources'].get(n)==h and bm['source']['sources'].get(n)==h and rbuild['source']['sources'].get(n)==h,'same RTL between gate and reference')
 cs=json.loads((im/'cases.json').read_text());refs={};summary=[];neg=[]
 for stall in (0,1):
  for pilot,ci in ((1,0),(2,5)):
   g=a.root/f'gatep{pilot}s{stall}';r=a.root/f'rtlp{pilot}s{stall}';gmeta,grows=rows(g,'GATE97_EXECUTED_NOT_RECEIVED');rmeta,rrows=rows(r,'RTL_EXECUTED_NOT_RECEIVED');require(gmeta['build_manifest_sha256']==sha(gb/'manifest.json'),'actual gate build link');require(gmeta['pilot']==rmeta['pilot']==pilot and gmeta['stall']==rmeta['stall']==stall,'exact variant');require(gmeta['input_manifest_sha256']==rmeta['input_manifest_sha256']==sha(im/'manifest.json'),'same original input');require(bm['source']['sources']['project/experiments/v_consumer/sim.cpp']==rbuild['source']['sources']['project/experiments/v_consumer/sim.cpp'],'same passive driver');require(grows==rrows,'all observable fields gate equals RTL')
   c=cs[ci]
   if c['name']not in refs:refs[c['name']]=reference(im,c)
   for row in grows:require(row['name']==c['name'],'fixed representative case');summary.append(dict(check(row,refs[c['name']]),stall=stall,pilot=pilot,gate_manifest_sha256=sha(g/'manifest.json'),RTL_manifest_sha256=sha(r/'manifest.json')))
   dst=a.out/f'negative-p{pilot}s{stall}';shutil.copytree(g,dst);f=dst/'actual.jsonl';bad=[json.loads(x)for x in f.read_text().splitlines()];bad[1]['out'][0]^=1;f.write_text(''.join(json.dumps(x)+'\n'for x in bad));m=json.loads((dst/'manifest.json').read_text())
   for e in m['artifacts']:e['bytes']=(dst/e['path']).stat().st_size;e['sha256']=sha(dst/e['path'])
   (dst/'manifest.json').write_text(json.dumps(m,indent=2)+'\n');_,rr=rows(dst,'GATE97_EXECUTED_NOT_RECEIVED')
   try:require(rr==rrows,'rehashed actual gate result differs')
   except ValueError:neg.append({'manifest_sha256':sha(dst/'manifest.json'),'status':'REJECTED_REHASHED_GATE_RESULT'})
   else:raise ValueError('mutant accepted')
 result={'status':'PASS97_EXACT_MAPPED_GATE_AND_ORIGINAL_ORACLE','receiver_source':binding,'mapping_manifest_sha256':sha(mr/'manifest.json'),'gate_prepared_manifest_sha256':sha(gr/'manifest.json'),'build_manifest_sha256':sha(gb/'manifest.json'),'rows':summary,'rehashed_negatives':neg,'limits':['Zero-delay actual mapped logic with behavioral store82. No timing/SRAM macro equivalence/signoff.','Only two original cases, prep-only plus full consumer each, two deterministic stall modes. No gate epoch/metadata Q injection, errors/abort qualification or universal proof.Those50-command cases are RTL-only.']};(a.out/'receipt.json').write_text(json.dumps(result,indent=2)+'\n');print(result['status'])
if __name__=='__main__':main()
