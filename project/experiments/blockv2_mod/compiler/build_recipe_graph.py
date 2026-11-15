import argparse,json
from collections import Counter
from pathlib import Path
from frontend import import_onnx
from recipe_graph import build
from verify_recipe_graph import verify
p=argparse.ArgumentParser()
p.add_argument('model',type=Path);p.add_argument('output',type=Path)
a=p.parse_args()
original=import_onnx(a.model)
graph=build(original)
proof=verify(original,graph)
a.output.mkdir(parents=True,exist_ok=False)
(a.output/'recipe-graph.json').write_text(json.dumps(graph,separators=(',',':'))+'\n')
summary={**graph['coverage'],'recipe_kinds':dict(Counter(t['kind'] for t in graph['tasks'])),
         'source_coverage_proof':proof, 'unmatched':graph['recognition_notes'],'status':'semantic_recognition_only'}
(a.output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary),flush=True)
