"""Real file mutations, rehashed manifests, full independent boundaries; plus invalid-domain SAT counterexample."""
import argparse,json,shutil,subprocess,importlib.util
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
def mod(name,path):
 s=importlib.util.spec_from_file_location(name,ROOT/path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
V=mod('variant_receiver','project/experiments/attention_width/receive.py');P=mod('proof_receiver','project/experiments/attention_width/proof_receive.py')
def rehash(d):
 m=json.loads((d/'manifest.json').read_text())
 for e in m['artifacts']:e.update(bytes=(d/e['path']).stat().st_size,sha256=V.sha(d/e['path']))
 V.put(d/'manifest.json',m)
def main():
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(exist_ok=False,parents=True);records=[]
 for case in['style','family-bool','adapter-SHA']:
  d=a.out/case;shutil.copytree(a.root/'r106s2p0',d);m=json.loads((d/'manifest.json').read_text())
  if case=='style':m['style']=1
  elif case=='family-bool':m['family']=True
  else:m['adapter_sha256']='0'*64
  V.put(d/'manifest.json',m);rehash(d)
  try:V.binding(d)
  except ValueError as e:records.append({'case':case,'rejected':True,'reason':str(e),'manifest_sha256':V.sha(d/'manifest.json')})
  else:raise ValueError('variant mutation accepted')
 for case in['cone-cell','cone-output','FF-next','prefix-cell']:
  d=a.out/case;shutil.copytree(a.root/'proof01',d)
  if case in['cone-cell','cone-output']:
   f=d/'math-cones.json';j=json.loads(f.read_text());m=j['modules']['math_v2']
   if case=='cone-cell':key=next(iter(m['cells']));m['cells'][key]['attributes']['bad_mutation']='1'
   else:m['ports']['dotnext']['bits'][0]='0'
  elif case=='FF-next':
   f=d/'v2-inv.json';j=json.loads(f.read_text());j['modules']['inv_v2']['ports']['next_limb']['bits'][0]='0'
  else:
   f=d/'extraction.json';j=json.loads(f.read_text());j['v2']['math']['prefixes'][0]['bits'][0]='0'
  V.put(f,j);rehash(d)
  # Copies retain exact original executed .ys/command paths; production audit defaults to itself.
  try:P.audit(d,execution_root=a.root/'proof01')
  except ValueError as e:
   reason=str(e);V.need('exact synthesis command'not in reason and 'actual proc execution'not in reason,'negative rejected by relocated path before semantic check');records.append({'case':case,'rejected':True,'reason':reason,'manifest_sha256':V.sha(d/'manifest.json')})
  else:raise ValueError('proof mutation accepted')
 # No reachability assumption: actual narrowed QK limb3 should be a real counterexample.
 d=a.out/'unreachable-limb3';d.mkdir();math=json.loads((a.root/'proof01/math-cones.json').read_text());V.put(d/'cones.json',math)
 text=P.check_text(math['modules'],'math');needle='((limb>2)||(';V.need(text.count(needle)==1,'exact independent domain predicate');text=text.replace(needle,'((1\'b0)||(')
 (d/'monitor.sv').write_text(text,newline='\n');ys=d/'check.ys';ys.write_text(f'read_json {d}/cones.json\nread_verilog {d}/monitor.sv\nprep -top independent\nflatten\nopt_clean\nsat -verify -prove ok 1 -show-inputs -show-outputs -dump_json {d}/counterexample.json\n',newline='\n');argv=[*P.BASE,'--pwd',str(d),P.SIF,'yosys','-s',str(ys)]
 with(d/'check.log').open('w')as f:r=subprocess.run(argv,stdout=f,stderr=subprocess.STDOUT,timeout=600)
 V.need(r.returncode!=0 and 'proof did fail'in(d/'check.log').read_text()and(d/'counterexample.json').exists(),'unrestricted real cone must produce witness')
 V.put(d/'command.json',{'argv':argv,'exit':r.returncode,'expected':'SAT proof fails for unreachable limb3; real FF invariant separately proven'})
 records.append({'case':'unreachable-limb3','rejected':True,'reason':'actual SAT counterexample without proven reachable-domain assumption','counterexample_sha256':V.sha(d/'counterexample.json')})
 V.put(a.out/'receipt.json',{'status':'PASS110_REHASHED_VARIANT_PROOF_NEGATIVES_AND_DOMAIN_COUNTEREXAMPLE','source':json.loads((ROOT/'binding.json').read_text()),'cases':records});print('PASS110_REHASHED_VARIANT_PROOF_NEGATIVES_AND_DOMAIN_COUNTEREXAMPLE')
if __name__=='__main__':main()
