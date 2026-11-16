"""Rebuild saved vector arithmetic with the current native compiler.

Never patch costs in an old schedule after fixing a command recipe. Recreate
all services/addresses and the same registered action families, then audit.
Weights, numerics, physical resources and qualification inputs stay fixed.
"""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path

from streaming_ir import compile_graph
from verify_primitive_cost import verify


def recompile(source):
    program=source['primitive_program'];model=source['model']
    nodes={node['id']:node for node in program['instructions']}
    metadata={**program.get('initial_formats',{}),**nodes}
    trace=[]
    for task in model['tasks']:
        output=task['outputs'][0];binding=program['value_bindings'][output]
        if binding not in metadata or 'exponent' not in metadata[binding]:
            raise ValueError('saved vector output lacks typed format '+output)
        trace.append({'id':task['id'],'shape':model['values'][output]['shape'],
            'exponent':metadata[binding]['exponent']})
    hardware=deepcopy(source['hardware'])
    # These are backend libraries/qualification bindings, not physical cells.
    for name in ('phase_native_templates','tile_service_profiles','tile_service_bindings'):
        hardware.pop(name,None)
    ir=compile_graph(model,hardware,trace,hardware['native_leaf_profiles'],deepcopy(program))
    if 'preparation_reuse_scope' in source:
        from preparation_reuse import lower
        lower(ir)
    if 'primitive_stages' in source:
        from primitive_stages import lower
        lower(ir)
    if 'read_cache_scope' in source:
        from dot_cache import variants
        variants(ir,state_cost=True)
    if 'column_shard_scope' in source:
        from column_shards import variants_for
        scope=source['column_shard_scope']
        limits={scope[key] for key in ('max_static_bindings_per_task','max_bindings_per_task') if key in scope}
        if len(limits)!=1:raise ValueError('saved column family lacks an unambiguous binding bound')
        variants_for(ir,max_shards=scope['max_shards'],max_bindings=limits.pop(),
            dynamic=bool(scope.get('frontier_partition_bindings',0)))
    if 'phased_compound_scope' in source:
        from phased_compounds import variants_for
        variants_for(ir)
    if 'tile_scope' in source:
        from tile_bindings import variants_for
        variants_for(ir,deepcopy(source['hardware']['tile_service_profiles']),
            service_bindings=deepcopy(source['hardware']['tile_service_bindings']))
    if ir['primitive_program']!=program:raise ValueError('saved vector arithmetic changed')
    for key in ('sites','resources','leaf_inventory','virtual_memory'):
        if ir['hardware'][key]!=source['hardware'][key]:
            raise ValueError('recompilation changed hardware '+key)
    verify(ir)
    return ir


def main():
    parser=argparse.ArgumentParser();parser.add_argument('source',type=Path);parser.add_argument('output',type=Path)
    args=parser.parse_args();args.output.mkdir(exist_ok=False)
    ir=recompile(json.loads(args.source.read_text(encoding='utf-8')))
    with (args.output/'ir.json').open('w',encoding='utf-8',newline='\n') as stream:
        json.dump(ir,stream,separators=(',',':'));stream.write('\n')
    report={'passed':True,'source':str(args.source),'source_sha256':hashlib.sha256(args.source.read_bytes()).hexdigest(),
        'ir_sha256':hashlib.sha256((args.output/'ir.json').read_bytes()).hexdigest(),
        'services':len(ir['tasks']),'bindings':sum(len(t['bindings']) for t in ir['tasks']),
        'nexp_primitives':sum(n['op']=='NExp' for n in ir['primitive_program']['instructions']),
        'scope':'same vector arithmetic/hardware, current native lowering; old schedules deliberately not reused'}
    (args.output/'report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report),flush=True)


if __name__=='__main__':main()
