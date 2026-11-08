"""Quick real-graph subgraph diagnostic; explicitly not full-model evidence."""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import gc

from column_shards import variants_for
from dot_cache import variants
from full_plan import replicated_inventory
from loop_dp import optimize,search
from preparation_reuse import lower as prepare
from primitive_stages import lower
from streaming_ir import compile_graph
from verify_loop_dp import verify
from verify_primitive_cost import verify as verify_cost


def main():
    p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('output',type=Path)
    mode=p.add_mutually_exclusive_group(required=True)
    mode.add_argument('--kernel-prefix');mode.add_argument('--full-graph',action='store_true')
    p.add_argument('--wire-budget',type=int,required=True);p.add_argument('--before-plan',type=Path)
    p.add_argument('--write-ir',action='store_true')
    p.add_argument('--nine-group-count-experiment',action='store_true');a=p.parse_args()
    a.output.mkdir(exist_ok=False)
    source_sha256=hashlib.sha256(a.source.read_bytes()).hexdigest()
    provenance={'source':str(a.source),'source_sha256':source_sha256,
                'module_sha256':{f.name:hashlib.sha256(f.read_bytes()).hexdigest()
                                 for f in Path(__file__).parent.glob('*.py')}}
    (a.output/'provenance.json').write_text(json.dumps(provenance,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'phase':'loading'}),flush=True)
    old=json.loads(a.source.read_text());primitive=deepcopy(old['primitive_program'])
    primitive['instructions']=[n for n in primitive['instructions'] if a.full_graph or n['kernel'].startswith(a.kernel_prefix)]
    if not primitive['instructions']:raise ValueError('empty diagnostic subgraph')
    kernels={n['kernel'] for n in primitive['instructions']}
    if not a.full_graph:primitive['outputs']={'last':primitive['instructions'][-1]['id']}
    model=deepcopy(old['model']);model['tasks']=[t for t in model['tasks'] if t['id'] in kernels]
    rows={r['id']:r for r in old['program']}
    trace=[{'id':t['id'],'shape':rows[t['id']].get('shape',model['values'][t['outputs'][0]]['shape']),
            'exponent':rows[t['id']].get('exponent',0)} for t in model['tasks']]
    h=replicated_inventory(old['hardware']) if a.nine_group_count_experiment else old['hardware']
    del old,rows;gc.collect()
    print(json.dumps({'phase':'lowering','instructions':len(primitive['instructions'])}),flush=True)
    ir=variants(lower(prepare(compile_graph(model,h,trace,h['native_leaf_profiles'],primitive))),state_cost=True)
    print(json.dumps({'phase':'old-native-audit','tasks':len(ir['tasks'])}),flush=True)
    cost_before=verify_cost(ir)
    before=(json.loads(a.before_plan.read_text()) if a.before_plan else
            optimize(ir['tasks'],ir['hardware'],width=8,wire_budget=a.wire_budget))
    verify(ir['tasks'],ir['hardware'],before,wire_budget=a.wire_budget)
    variants_for(ir);cost_after=verify_cost(ir)
    print(json.dumps({'phase':'new-native-audit-passed','bindings':cost_after['bindings']}),flush=True)
    if a.write_ir:
        with (a.output/'ir.json').open('w',encoding='utf-8') as stream:json.dump(ir,stream,separators=(',',':'))
    base=search(ir['tasks'],ir['hardware'],width=1,wire_budget=a.wire_budget)
    verify(ir['tasks'],ir['hardware'],base,wire_budget=a.wire_budget)
    (a.output/'greedy.json').write_text(json.dumps(base,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'phase':'greedy-passed','makespan':base['makespan']}),flush=True)
    strong=search(ir['tasks'],ir['hardware'],width=1,ready_limit=1,wire_budget=a.wire_budget,
                  priority='heft',rank_policy='earliest_finish')
    verify(ir['tasks'],ir['hardware'],strong,wire_budget=a.wire_budget)
    (a.output/'heft.json').write_text(json.dumps(strong,indent=2)+'\n',encoding='utf-8')
    selected=optimize(ir['tasks'],ir['hardware'],width=8,wire_budget=a.wire_budget,incumbents=[before,base,strong])
    audit=verify(ir['tasks'],ir['hardware'],selected,wire_budget=a.wire_budget)
    compound={t['id']:{b['id'] for b in t['bindings'] if 'parallel_shards' in b} for t in ir['tasks']}
    result={'source':str(a.source),'source_sha256':source_sha256,
        'kernel_prefix':a.kernel_prefix,'full_graph':a.full_graph,'primitive_count':len(primitive['instructions']),
        'stages':len(ir['tasks']),'wire_budget':a.wire_budget,'before':before['makespan'],
        'same_pool_greedy':base['makespan'],'selected':selected['makespan'],
        'same_pool_heft_append_only':strong['makespan'],
        'gain_against_stronger_baseline_fraction':1-selected['makespan']/min(before['makespan'],base['makespan'],strong['makespan']),
        'selected_compounds':[r['id'] for r in selected['tasks'] if r['binding'] in compound[r['id']]],
        'column_shard_scope':ir['column_shard_scope'],'cost_before':cost_before,'cost_after':cost_after,
        'audit':audit,'scope':'real source subgraph / native-profile model only; not full model, numeric replay, system timing or token/s'}
    for name,value in [('summary',result),('before',before),('greedy',base),('selected',selected)]:
        (a.output/(name+'.json')).write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result),flush=True)


if __name__=='__main__':main()
