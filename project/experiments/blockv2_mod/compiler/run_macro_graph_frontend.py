from pathlib import Path
from hashlib import sha256
import argparse,json,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'hardware'),str(ROOT/'compiler')]
from native_macro_graph import Frontend
def main():
 p=argparse.ArgumentParser()
 p.add_argument('--graph-directory',type=Path,required=True)
 p.add_argument('--hardware',type=Path,required=True)
 p.add_argument('--services',type=Path,required=True)
 p.add_argument('--output',type=Path,required=True)
 p.add_argument('--topology',type=int,default=18503)
 a=p.parse_args()
 names=['native-recipe-graph.json','native-operand-recipes.json','native-value-layout.json']
 data=[json.loads((a.graph_directory/n).read_text()) for n in names]
 hardware=json.loads(a.hardware.read_text());services=json.loads(a.services.read_text())['services']
 frontend=Frontend(*data,hardware,services,a.topology)
 frontend.export(a.output,progress=lambda line:print(line,flush=True))
 inputs=[a.graph_directory/n for n in names]+[a.hardware,a.services]
 sources=list((ROOT/'compiler').glob('native_macro_*.py'))+[Path(__file__),
  ROOT/'compiler/native_candidate_resources.py',ROOT/'compiler/native_local_projection_candidates.py',
  ROOT/'hardware/check_pr185_control_admission.py',ROOT/'hardware/check_parent_service_structure.py',
  ROOT/'hardware/native_resource_bindings.py',ROOT/'hardware/native_control_routes.py',ROOT/'hardware/service_resources.py']
 receipt={'inputs':{str(p):sha256(p.read_bytes()).hexdigest() for p in inputs},
  'sources':{str(p):sha256(p.read_bytes()).hexdigest() for p in sources},
  'control_admission':frontend.control_admission,'whole_plan_accepted':False}
 (a.output/'source-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
if __name__=='__main__':main()
