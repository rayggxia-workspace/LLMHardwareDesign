"""Revalidate the full source, then lower a source-closed real diagnostic cut.

Native SSA preserves original command/operand work. It is not yet a resident
schedule or a numerical/RTL qualification of the fused region.
"""
import argparse
from collections import Counter
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path

from native_pointwise import bind_external,counts,lower,regions
from primitive_slice import select
from verify_primitive_cost import verify
from verify_loop_dp import verify as verify_plan


def cut(source,prefix,source_sha):
    from streaming_ir import compile_graph
    from preparation_reuse import lower as prepare
    from primitive_stages import lower as stages
    from dot_cache import variants as cache
    from column_shards import variants_for as columns
    from phased_compounds import variants_for as phases
    from tile_bindings import variants_for as tiles
    from tile_partitions import variants_for as partitions
    names=[n['id'] for n in source['primitive_program']['instructions'] if n['kernel'].startswith(prefix)]
    m,p,scope=select(source['model'],source['primitive_program'],names,source_sha)
    last={n['kernel']:n for n in p['instructions']}
    trace=[{'id':t['id'],'shape':m['values'][t['outputs'][0]]['shape'],
            'exponent':last[t['id']]['exponent']} for t in m['tasks']]
    h=deepcopy(source['hardware'])
    ir=cache(stages(prepare(compile_graph(m,h,trace,h['native_leaf_profiles'],p))),state_cost=True)
    columns(ir);phases(ir)
    tiles(ir,h['tile_service_profiles'],service_bindings=h['tile_service_bindings'])
    partitions(ir,phased=True)
    ir['diagnostic_cut_scope']=scope
    return ir


def survey(ir):
    from streaming_ir import primitive_body,counts as original_counts
    result=[];p=ir['primitive_program'];nodes={n['id']:n for n in p['instructions']}
    for names in regions(p):
        size=math.prod(nodes[names[0]]['shape']);original=Counter();graphs=[]
        for name in names:
            body,_=primitive_body(nodes[name],ir['native_operand_components'][name])
            work=original_counts(body,ir['native_templates'])
            for key,value in work.items():
                if key.endswith((':read',':write',':commands')) and value:
                    if value%size:raise ValueError('nonuniform pointwise work')
                    original[key]+=value//size
        for at in sorted({0,size//2,size-1}):
            g=bind_external(lower(p,names,at),ir)
            if counts(g)!=dict(original):raise ValueError('native SSA changed original command/operand work')
            graphs.append(g)
        result.append({'primitives':names,'elements':size,'operations':len(graphs[0]['operations']),
            'objects':len(graphs[0]['objects']),'live_out':list(graphs[0]['live_out']),
            'native_work_per_element':dict(original),'graphs':graphs})
    return result


def main():
    p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('plan',type=Path)
    p.add_argument('output',type=Path);p.add_argument('--kernel-prefix',required=True)
    p.add_argument('--wire-budget',type=int,required=True);a=p.parse_args();a.output.mkdir(exist_ok=False)
    source=json.loads(a.source.read_text());sha=hashlib.sha256(a.source.read_bytes()).hexdigest()
    full=verify(source);plan=verify_plan(source['tasks'],source['hardware'],json.loads(a.plan.read_text()),a.wire_budget)
    print(json.dumps({'phase':'full-source-and-plan-audit-passed','native':full,'plan':plan}),flush=True)
    ir=cut(source,a.kernel_prefix,sha);audit=verify(ir);rows=survey(ir)
    def write(name,value):
        with (a.output/(name+'.json')).open('w',encoding='utf-8') as f:json.dump(value,f,separators=(',',':'))
    write('ir',ir);write('native-regions',rows)
    summary={'passed':True,'source_sha256':sha,'plan_sha256':hashlib.sha256(a.plan.read_bytes()).hexdigest(),
        'full_source_audit':full,'full_plan_audit':plan,'cut_native_audit':audit,
        'cut_scope':ir['diagnostic_cut_scope'],'regions':len(rows),
        'eligible_primitives':sum(len(r['primitives']) for r in rows),
        'max_region_primitives':max((len(r['primitives']) for r in rows),default=0),
        'native_operations_per_sample':sum(r['operations'] for r in rows),
        'boundary_address_samples':sum(len(r['graphs']) for r in rows),
        'scope':'real source-closed cut, reserved external addresses and conserved native work; not a fused schedule, SRAM residency, numeric/RTL/physical/system or energy qualification'}
    write('summary',summary);print(json.dumps(summary),flush=True)


if __name__=='__main__':main()
