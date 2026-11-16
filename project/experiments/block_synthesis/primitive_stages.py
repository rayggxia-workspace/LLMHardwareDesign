"""Expose acknowledged primitive boundaries to the common scheduler.

No native command, port, arithmetic, traffic or overlap inside a service is
added. Each service still reserves its resources until its final STORE ACK.
Only independent services can overlap. This lowering is a shared capability
for greedy and DP, not by itself evidence of a better search algorithm.
"""
from copy import deepcopy

from streaming_ir import primitive_body, counts, enumerate_bindings


def lower(ir):
    if 'primitive_stages' in ir:
        raise ValueError('primitive stages already lowered')
    if any('read_cache' in b for t in ir['tasks'] for b in t['bindings']):
        raise ValueError('lower primitive stages before cache specialization')
    hardware=deepcopy(ir['hardware']); tasks=[]; rows=[]; stage_map={}; producers={}
    instructions=ir['primitive_program']['instructions']
    ids=[n['id'] for n in instructions]
    if len(ids)!=len(set(ids)):
        raise ValueError('duplicate primitive identity')
    external=ir['required_external_bytes']//16
    # The old shared per-kernel scratch must not alias concurrent primitives.
    # Keep it reserved for provenance; each new stage has explicit private
    # external scratch. Reclaiming these old regions is a separate lowering.
    reserved=deepcopy(ir.get('native_scratch_regions',[]))
    reserved.extend(deepcopy(r['temporary_external_region']) for r in ir['program']
                    if 'temporary_external_region' in r)
    preparations=ir.get('operand_preparations',{})

    def dependencies(names):
        if any(name in ids and name not in producers for name in names):
            raise ValueError('primitive source is not defined before use')
        return set().union(*(producers.get(name,set()) for name in names))

    def emit(stage_id,node,phase,body,scratch,after):
        nonlocal external
        work=counts(body,ir['native_templates'])
        bindings=enumerate_bindings(work,hardware)
        if not bindings:
            raise ValueError('no native stage binding '+stage_id)
        tasks.append({'id':stage_id,'after':sorted(after),'bindings':bindings})
        rows.append({'id':stage_id,'op':node['op'],'source_primitive':node['id'],
            'source_kernel':node['kernel'],'phase':phase,'shape':node['shape'],
            'inputs':node['inputs'],'exponent':node['exponent'],
            'body':body,'primitive_counts':dict(work),
            'temporary_external_region':{'address_words':external,'words':scratch},
            'S_layout':{'input_words':[0,1,2],'output_word':3,'staging_words':[4,5,6,7]},
            'lifetime':'all input commits and final external STORE ACK precede stage completion',
            'accumulator':'whole native reduction held until final read; no live accumulator crosses a stage'})
        external+=scratch

    for node in instructions:
        name=node['id']; c=ir['native_operand_components'][name]
        p=preparations.get(name); body,scratch=primitive_body(node,c,p)
        work=counts(body,ir['native_templates']); after=dependencies(node['inputs'])
        if not any(work.values()):
            producers[name]=after
            continue
        stages={'execute':name}
        if p:
            prepare_id=name+'#prepare-A'
            if prepare_id in ids:
                raise ValueError('prepared stage identity collision')
            stages['prepare']=prepare_id
            prepare_body,body=body['sequence']
            emit(prepare_id,node,'prepare-A',prepare_body,64,dependencies(node['inputs'][:1]))
            after=dependencies(node['inputs'][1:])|{prepare_id}
        emit(name,node,'execute',body,scratch,after)
        stage_map[name]=stages;producers[name]={name}
    if external*16>1<<hardware['virtual_memory']['address_bits']:
        raise ValueError('external address space overflow')
    if hardware.get('external_capacity_words') is not None and external>hardware['external_capacity_words']:
        raise ValueError('declared external capacity exceeded')
    ir.update(tasks=tasks,program=rows,hardware=hardware,primitive_stages=stage_map,
        native_scratch_regions=reserved,required_external_bytes=external*16,
        primitive_stage_scope={
            'services':len(tasks),'arithmetic_primitives':len(stage_map),
            'extra_external_bytes':external*16-ir['required_external_bytes'],
            'scope':'acknowledged primitive boundaries and separate prepared-A service; same native work and transfers',
            'excluded':'within-service DMA overlap, column/K splitting, extra LC tokens, MC/LC encoding, system timing'})
    return ir
