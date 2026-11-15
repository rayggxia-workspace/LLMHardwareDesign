"""Recover the standard two-step quick scenario from sealed 512/513 source graphs."""
import sys,json,hashlib
from pathlib import Path
from frontend import import_onnx
from recipe_graph import build
from value_layout import build as layout
from operand_recipes import lower
from verify_recipe_graph import verify
from verify_operand_recipes import verify as verify_operands
history=int(sys.argv[1]);out=Path(sys.argv[2])
if history not in (512,513):raise ValueError('standard quick scenario requires 512/513')
source=Path('evidence')/('cached-decode-graph-114372' if history==512 else 'cached-decode-graph-114373')
receipt=json.loads((source/'receipt.json').read_text());path=source/'decode.onnx'
if receipt['history_positions']!=history or not receipt['frozen_zero_kv']:raise ValueError('scenario mismatch')
if hashlib.sha256(path.read_bytes()).hexdigest()!=receipt['onnx_sha256']:raise ValueError('graph seal')
model=import_onnx(path);graph=build(model);proof=verify(model,graph)
views=layout(graph);recipes=lower(graph,views);operand_proof=verify_operands(graph,recipes)
out.mkdir(parents=True,exist_ok=False)
for name,data in [('native-recipe-graph.json',graph),('native-value-layout.json',views),('native-operand-recipes.json',recipes)]:
 (out/name).write_text(json.dumps(data,separators=(',',':'))+'\n')
(out/'scenario.json').write_text(json.dumps({'history_positions':history,'decode_steps_total':2,'source_graph':str(path),'onnx_sha256':receipt['onnx_sha256'],'first_token':840,'initial_KV':'frozen_zero','second_step_requires_previous_KV_and_token':True,'recipe_proof':proof,'operand_proof':operand_proof},indent=2)+'\n')
print(json.dumps({'history':history,'tasks':len(recipes['tasks']),'output':str(out)}))
