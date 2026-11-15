from pathlib import Path
from hashlib import sha256
import argparse,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'hardware'),str(ROOT/'compiler')]
from native_macro_graph import Frontend
from native_macro_select import select
def main():
 p=argparse.ArgumentParser()
 p.add_argument('--graph-directory',type=Path,required=True)
 p.add_argument('--candidate-directory',type=Path,required=True)
 p.add_argument('--hardware',type=Path,required=True)
 p.add_argument('--services',type=Path,required=True)
 p.add_argument('--output',type=Path,required=True)
 p.add_argument('--width',type=int,default=8)
 p.add_argument('--depth',type=int,default=2)
 p.add_argument('--incumbent-plan',type=Path)
 p.add_argument('--export-value',action='append',default=[],help='persistent state root that must commit to DDR')
 a=p.parse_args();manifest=json.loads((a.candidate_directory/'manifest.json').read_text())
 data=[json.loads((a.graph_directory/n).read_text()) for n in [
 'native-recipe-graph.json','native-operand-recipes.json','native-value-layout.json']]
 hardware=json.loads(a.hardware.read_text());services=json.loads(a.services.read_text())['services']
 frontend=Frontend(*data,hardware,services,manifest['hardware']['native_dispatch_overlay']['topology_id'],range_tiles=manifest.get('range_tiles',0),joint=manifest.get('joint',False))
 if frontend.joint:
  from native_joint_search import select as joint_select,digest
  exports=sorted(set(data[0]['outputs'])|set(a.export_value))
  plan=joint_select(frontend,a.candidate_directory,width=a.width,depth=a.depth,exports=exports,progress=lambda s:print(s,flush=True))
  plan['exported_values']=exports;plan.pop('plan_sha256');plan['plan_sha256']=digest(plan)
 else:plan=select(frontend,a.candidate_directory,width=a.width,progress=lambda s:print(s,flush=True))
 a.output.mkdir(parents=True,exist_ok=True)
 if a.incumbent_plan:
  from native_plan_incumbent import choose
  (a.output/'joint-candidate-plan.json').write_text(json.dumps(plan,separators=(',',':'))+'\n')
  plan=choose(plan,json.loads(a.incumbent_plan.read_text()))
 (a.output/'plan.json').write_text(json.dumps(plan,separators=(',',':'))+'\n')
 sources=list((ROOT/'compiler').glob('native_*.py'))+[Path(__file__)]
 receipt={'plan_sha256':plan['plan_sha256'],'delivery_accepted':False,
  'sources':{str(p):sha256(p.read_bytes()).hexdigest() for p in sources}}
 (a.output/'source-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
if __name__=='__main__':main()
