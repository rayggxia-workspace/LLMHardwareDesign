"""Exact mapped102 cell logic vs actual RTL plus all-value independent GQA oracle."""
import argparse,json,shutil
from pathlib import Path
from receive import Oracle,receive,sha,need,artifacts,put
ROOT=Path(__file__).resolve().parents[3]
def bound(p,status):
 m=json.loads((p/'manifest.json').read_text());need(m['status']==status,'bound status');artifacts(p,m);return m
def compare(g,r,inp,oracle):
 gm=bound(g,'GATE102_EXECUTED_NOT_RECEIVED');rm=bound(r,'RTL_EXECUTED_NOT_RECEIVED');need(gm['stall']==rm['stall']and gm['pilot']==rm['pilot']and gm['input_manifest_sha256']==rm['input_manifest_sha256'],'same fixed replay inputs')
 gr=[json.loads(s)for s in(g/'actual.jsonl').read_text().splitlines()];rr=[json.loads(s)for s in(r/'actual.jsonl').read_text().splitlines()];need(gr==rr,'all numeric/cycle/protocol result fields gate equals RTL');need(json.loads((g/'actual.jsonl.protocol.json').read_text())==json.loads((r/'actual.jsonl.protocol.json').read_text()),'actual protocol gate equals RTL')
 return receive(g,inp,oracle,'GATE102_EXECUTED_NOT_RECEIVED')
def main():
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(exist_ok=False);b=json.loads((ROOT/'binding.json').read_text())
 for n,h in b['sources'].items():need(sha(ROOT/n)==h,'receiver frozen bytes')
 mr=a.root/'map02';pr=a.root/'gateprep01';br=a.root/'gatebuild01';rb=a.root/'build05p';inp=a.root/'input02'
 mm=bound(mr,'LOGIC_ONLY_MAPPED_NOT_PPA');pm=bound(pr,'EXACT_MAPPED102_LOGIC_EXPORTED');bm=bound(br,'GATE102_BUILT_NOT_EXECUTED');rbuild=bound(rb,'BUILT_NOT_EXECUTED')
 need(pm['mapping_manifest_sha256']==sha(mr/'manifest.json')and bm['prepared_manifest_sha256']==sha(pr/'manifest.json'),'map to build receipt binding');need(sha(pr/'mapped.json')==sha(mr/'mapped.json'),'original actual cell graph');need(sha(br/'obj/Vchain102')==bm['binary_sha256']and sha(rb/'obj/Vchain102')==rbuild['binary_sha256'],'both actual binaries')
 for n,h in mm['source']['sources'].items():
  if n.startswith('project/rtl/'):need(pm['source']['sources'].get(n)==h and bm['source']['sources'].get(n)==h and rbuild['source']['sources'].get(n)==h,'all same RTL bytes')
 key='project/experiments/attention_rtl/sim.cpp';need(bm['source']['sources'][key]==rbuild['source']['sources'][key]==b['sources'][key],'same passive driver without injection')
 oracle=Oracle(inp);rows=[];neg=[]
 for pilot in(1,2):
  for stall in(0,1):
   g=a.root/f'gatep{pilot}s{stall}';r=a.root/f'rtlp{pilot}s{stall}';gm=bound(g,'GATE102_EXECUTED_NOT_RECEIVED');need(gm['build_manifest_sha256']==sha(br/'manifest.json'),'gate run exact binary');rec=compare(g,r,inp,oracle);rows.append({'pilot':pilot,'stall':stall,'counts':rec['counts'],'gate_manifest_sha256':sha(g/'manifest.json'),'RTL_manifest_sha256':sha(r/'manifest.json')})
   dest=a.out/f'negative-p{pilot}s{stall}';dest.mkdir()
   for f in gm['artifacts']:shutil.copyfile(g/f['path'],dest/f['path'])
   bad=[json.loads(s)for s in(dest/'actual.jsonl').read_text().splitlines()];bad[0]['out'][0]^=1;(dest/'actual.jsonl').write_text(''.join(json.dumps(x)+'\n'for x in bad),newline='\n')
   for f in gm['artifacts']:f.update(bytes=(dest/f['path']).stat().st_size,sha256=sha(dest/f['path']))
   put(dest/'manifest.json',gm)
   try:compare(dest,r,inp,oracle)
   except ValueError as e:neg.append({'status':'REJECTED_ACTUAL_REHASHED_GATE_OUTPUT','reason':str(e),'manifest_sha256':sha(dest/'manifest.json')})
   else:raise ValueError('changed gate output accepted')
 put(a.out/'receipt.json',{'status':'PASS102_EXACT_RAW_GATE_AND_INDEPENDENT_GQA','source':b,'mapping_manifest_sha256':sha(mr/'manifest.json'),'prepared_manifest_sha256':sha(pr/'manifest.json'),'build_manifest_sha256':sha(br/'manifest.json'),'runs':rows,'negatives':neg,'limits':['Selected normal complete8head actual full/cached and synthetic queries only; zero-delay mapped cells with original behavioral store82.','No gate fault/epoch injection, abort/error qualification, universal equivalence, SRAM/ROM macro, STA or physical signoff.']});print('PASS102_EXACT_RAW_GATE_AND_INDEPENDENT_GQA')
if __name__=='__main__':main()
