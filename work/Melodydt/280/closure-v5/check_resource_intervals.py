"""Exercise overlap and cross-window conservation without model dependencies."""
import ast
from pathlib import Path

tree=ast.parse(Path(__file__).with_name('deployment_observation.py').read_text())
node=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Intervals')
namespace={}
exec(compile(ast.Module(body=[node],type_ignores=[]),'<Intervals>','exec'),namespace)
Intervals=namespace['Intervals']
x=Intervals();x.add(2,10);x.add(5,12)
a=x.seal(8);b=x.seal(15)
assert a=={'busy_union_ps':6,'overlapping_request_ps':5,'calls':2}
assert b=={'busy_union_ps':4,'overlapping_request_ps':0,'calls':0}
x=Intervals();x.add(1,2);x.add(4,6)
assert x.seal(7)['busy_union_ps']==3
assert x.seal(8)['busy_union_ps']==0
print('RESOURCE_INTERVAL_CONSERVATION_PASS')
