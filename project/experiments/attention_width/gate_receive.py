"""Exact actual cell graph export -> binary -> selected gate vs same RTL and math."""
import argparse,json,shutil,importlib.util
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
spec=importlib.util.spec_from_file_location('independent_original106',ROOT/'project/experiments/shared_services/receive.py');R=importlib.util.module_from_spec(spec);spec.loader.exec_module(R)
Oracle,inspect,sha,need,bound,put=R.Oracle,R.inspect,R.sha,R.need,R.bound,R.put
spec=importlib.util.spec_from_file_location('variant110',ROOT/'project/experiments/attention_width/receive.py');V=importlib.util.module_from_spec(spec);spec.loader.exec_module(V)
def main():
 p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--gate',type=Path,required=True);p.add_argument('--rtl',type=Path,required=True);p.add_argument('--map',type=Path,required=True);p.add_argument('--prepared',type=Path,required=True);p.add_argument('--build',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(exist_ok=False);bd=json.loads((ROOT/'binding.json').read_text())
 for n,h in bd['sources'].items():need(sha(ROOT/n)==h,'receiver source')
 mm=bound(a.map);pm=bound(a.prepared);bm=bound(a.build);need(mm['status']=='LOGIC_ONLY_MAPPED_NOT_PPA'and pm['status']=='EXACT_MAPPED106_LOGIC_EXPORTED'and bm['status']=='GATE106_BUILT_NOT_EXECUTED','full prepared status')
 need(pm['mapping_manifest_sha256']==sha(a.map/'manifest.json')and bm['prepared_manifest_sha256']==sha(a.prepared/'manifest.json'),'exact map/build SHA chain');need(sha(a.prepared/'mapped.json')==sha(a.map/'mapped.json'),'actual mapped cells unchanged');need(sha(a.build/'obj/Vshared106')==bm['binary_sha256'],'gate binary actual')
 for n,h in mm['source']['sources'].items():
  if n.startswith('project/rtl/'):need(bd['sources'].get(n)==h and bm['source']['sources'].get(n)==h and pm['source']['sources'].get(n)==h,'same actual RTL provenance')
 oracle=Oracle(a.input);runs=[]
 for g,r in [(a.gate,a.rtl)]:
  vr,_=V.binding(r);need(mm['family']==vr['family']==106 and mm['style']==vr['style'] and mm['adapter_sha256']==vr['adapter_sha256']==sha(a.map/'attention106.sv'),'exact mapped variant adapter');stall=vr['stall'];gm=bound(g);rm=bound(r);need(gm['build_manifest_sha256']==sha(a.build/'manifest.json'),'run gate binary binding');need(gm['stall']==rm['stall']==stall and gm['pilot']==rm['pilot']==1,'same normal selected commands')
  gr=[json.loads(l)for l in(g/'actual.jsonl').read_text().splitlines()];rr=[json.loads(l)for l in(r/'actual.jsonl').read_text().splitlines()];need(gr==rr,'all row fields including full32768state and cycle counts mapped vs RTL');need(json.loads((g/'actual.jsonl.protocol.json').read_text())==json.loads((r/'actual.jsonl.protocol.json').read_text()),'protocol exactly equal')
  rec=inspect(a.input,g,oracle);runs.append({'stall':stall,'gate_manifest_sha256':sha(g/'manifest.json'),'rtl_manifest_sha256':sha(r/'manifest.json'),**rec})
 put(a.out/'receipt.json',{'status':'PASS110_EXACT_RAW_GATE_AND_INDEPENDENT_ALL_VALUES','source':bd,'style':mm['style'],'stall':stall,'mapping_manifest_sha256':sha(a.map/'manifest.json'),'prepared_manifest_sha256':sha(a.prepared/'manifest.json'),'build_manifest_sha256':sha(a.build/'manifest.json'),'runs':runs,'limits':['INIT,M0,complete8head A fullprefix1,R complete singlehead step0 only; unchanged finite source contract.','No top Q injection in this gate driver, no claim of universal equivalence or gate abort/terminal coverage.','Zero-delay library functions and common behavioral SRAM; no macros/STA/physical/customization qualification.']});print('PASS110_EXACT_RAW_GATE_AND_INDEPENDENT_ALL_VALUES')
if __name__=='__main__':main()
