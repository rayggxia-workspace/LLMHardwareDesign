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
 a=p.parse_args();manifest=json.loads((a.candidate_directory/'manifest.json').read_text())
 data=[json.loads((a.graph_directory/n).read_text()) for n in [
 'native-recipe-graph.json','native-operand-recipes.json','native-value-layout.json']]
 hardware=json.loads(a.hardware.read_text());services=json.loads(a.services.read_text())['services']
 frontend=Frontend(*data,hardware,services,manifest['hardware']['native_dispatch_overlay']['topology_id'])
 plan=select(frontend,a.candidate_directory,width=a.width,progress=lambda s:print(s,flush=True))
 a.output.mkdir(parents=True,exist_ok=True)
 (a.output/'plan.json').write_text(json.dumps(plan,separators=(',',':'))+'\n')
 sources=[ROOT/'compiler'/n for n in ['native_macro_graph.py','native_macro_select.py','native_macro_work.py','run_macro_selection.py']]
 receipt={'plan_sha256':plan['plan_sha256'],'delivery_accepted':False,
  'sources':{str(p):sha256(p.read_bytes()).hexdigest() for p in sources}}
 (a.output/'source-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
if __name__=='__main__':main()
