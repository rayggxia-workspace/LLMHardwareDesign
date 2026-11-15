"""Compile a source-bound operator graph bundle against a block resource input.

The graph bundle contains the ONNX and its typed arithmetic IR, never a selected
schedule, archived native pages, or predetermined stage order.
"""
import argparse
from hashlib import sha256
import json
from pathlib import Path
from collections import Counter

from frontend import import_onnx
from event_loop_graph import lower
from event_native_dispatch import qualify_native_dispatch
from dispatch_responsibility import responsibilities
from run import compile_event_ir
from recipe_graph import build as build_recipe_graph
from value_layout import build as build_value_layout
from operand_recipes import lower as lower_operand_recipes
from verify_operand_recipes import verify as verify_operand_recipes
from verify_recipe_graph import verify as verify_recipe_graph

def read(path): return json.loads(path.read_text())

def source(bundle, key):
    row=bundle[key]
    path=Path(row['path'])
    if sha256(path.read_bytes()).hexdigest()!=row['sha256']:
        raise ValueError('graph source changed: '+key)
    return path

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('graph',type=Path)
    parser.add_argument('hardware',type=Path)
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--legacy-diagnostic',action='store_true',help='run the retired scalar-loop diagnostic explicitly')
    parser.add_argument('--width',type=int,default=8)
    args=parser.parse_args()
    graph_input=read(args.graph)
    if graph_input['schema']!='algo1-operator-graph-input/1':
        raise ValueError('unsupported graph input')
    hardware=read(args.hardware)
    profile=hardware.pop('native_dispatch_overlay')
    inventory=hardware['leaf_inventory']
    if not inventory or len({row['site'] for row in inventory.values()})!=len(inventory):
        raise ValueError('block instances require distinct SRAM resource namespaces')
    root=Path(__file__).resolve().parent
    for name,expected in profile['rtl_sources_sha256'].items():
        path=(root/'rtl'/name).resolve()
        if not path.is_relative_to(root/'rtl') or sha256(path.read_bytes()).hexdigest()!=expected:
            raise ValueError('RTL profile source mismatch: '+name)
    model=import_onnx(source(graph_input,'onnx'))
    recipe_graph=build_recipe_graph(model)
    recipe_proof=verify_recipe_graph(model,recipe_graph)
    value_layout=build_value_layout(recipe_graph)
    operand_recipes=lower_operand_recipes(recipe_graph,value_layout)
    operand_proof=verify_operand_recipes(recipe_graph,operand_recipes)
    if not args.legacy_diagnostic:
        from native_graph_pipeline import compile as compile_native
        native_hardware=read(args.hardware)
        result=compile_native(recipe_graph,operand_recipes,value_layout,native_hardware,
                              width=args.width,progress=lambda row:print(json.dumps(row),flush=True))
        args.output.mkdir(parents=True,exist_ok=False)
        for name,data in [('native-plan.json',result),('native-recipe-graph.json',recipe_graph),
                          ('native-operand-recipes.json',operand_recipes),('native-value-layout.json',value_layout)]:
            (args.output/name).write_text(json.dumps(data,indent=2)+'\n')
        from native_machine_package import package
        package_result=package(result,args.output/'machine-package',result['search_hardware']['topology_id'])
        receipt={'status':'native_machine_package_generated','delivery_accepted':False,
                 'plan_sha256':result['plan_sha256'],'hardware_instances':result['hardware_instances'],
                 'source_tasks':len(recipe_graph['tasks']),'selected_tasks':len(result['selection']),
                 'view_aliases':len(result['view_aliases']),'native_calls':len(result['calls']),
                 'search_verification':result['search_verification'],
                 'machine_instruction_package':'machine-package/manifest.json','machine_packaging':package_result,'timing_scope':result['timing_scope'],
                 'pending':['runtime assets or explicit timing-only scenario','joined execution and fast TLM']}
        (args.output/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
        print(json.dumps(receipt),flush=True)
        return
    program=read(source(graph_input,'typed_arithmetic_ir'))
    event_ir,hardware,proof=lower(model,hardware,program,hardware['native_leaf_profiles'])
    hardware=qualify_native_dispatch(hardware,rtl_profile=profile)
    result=compile_event_ir(event_ir,hardware,emit_outputs=True)
    gaps=responsibilities(hardware)
    args.output.mkdir(parents=True,exist_ok=False)
    receipt={
        'status':result['status'],'delivery_accepted':False,
        'input_sha256':{str(p):sha256(p.read_bytes()).hexdigest() for p in (args.graph,args.hardware)},
        'model_sha256':model['sha256'],'whole_graph_tasks':len(event_ir['tasks']),
        'hardware_instances':list(hardware['leaf_inventory']),
        'candidate_count':sum(len(t['bindings']) for t in event_ir['tasks']),
        'responsibility_counts':dict(Counter(g['owner'] for g in gaps)),
        'machine_instruction_package':None,
        'lowering_audit':proof,
        'native_recipe_coverage':recipe_proof,
        'native_backend_status':'source-indexed operand recipes lowered; native candidate admission, global selection and complete encoding pending',
        'operand_recipe_tasks':len(operand_recipes['tasks']),
        'operand_recipe_verification':operand_proof,
    }
    for name,data in [('algo1-result.json',result),('implementation-gaps.json',gaps),('receipt.json',receipt),('native-recipe-graph.json',recipe_graph),('native-value-layout.json',value_layout),('native-operand-recipes.json',operand_recipes)]:
        (args.output/name).write_text(json.dumps(data,indent=2)+'\n')
    print(json.dumps(receipt),flush=True)
    # There is intentionally no archive fallback. The native backend must produce
    # and validate a same-plan instruction package before this can succeed.
    raise SystemExit(2 if result['status']!='planned' else 3)

if __name__=='__main__':main()
