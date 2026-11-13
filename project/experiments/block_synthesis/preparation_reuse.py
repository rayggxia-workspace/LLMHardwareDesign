"""Column-invariant operand preparation recipe, independent of model names.

This describes existing split32 commands hoisted before the output-column
loop. Prepared records remain in explicitly allocated external memory, not an
unbounded private-S cache. Every multiply and full-K final rounding is retained.
"""
import math


def lower(ir):
    """Hoist column-invariant A preparation using existing native calls.

    Run before read-cache specialization. Extra storage is external, explicit,
    non-overlapping, address-width/capacity checked; no S or wire is invented.
    """
    from collections import Counter
    from streaming_ir import primitive_body, counts, seq
    from memory import descriptor_ticks
    if ir.get('operand_preparations'):
        raise ValueError('operand preparation already lowered')
    if any('read_cache' in b for t in ir['tasks'] for b in t['bindings']):
        raise ValueError('lower preparation before cache specialization')
    h=ir['hardware']; external=ir['required_external_bytes']//16
    limit=(1<<h['virtual_memory']['address_bits'])//16
    if h.get('external_capacity_words') is not None:
        limit=min(limit,h['external_capacity_words'])
    preparations={}; kernels={}
    for node in ir['primitive_program']['instructions']:
        c=ir['native_operand_components'][node['id']]
        p=recipe(node,c,external,limit)
        if p:
            preparations[node['id']]=p; external+=p['external_words']
        part,_=primitive_body(node,c,p)
        kernels.setdefault(node['kernel'],[]).append(part)
    tasks={t['id']:t for t in ir['tasks']}
    for row in ir['program']:
        if row['id'] not in tasks:continue
        body=seq(*kernels[row['id']]); stats=counts(body,ir['native_templates'])
        old=Counter(row['primitive_counts'])
        delta={key:stats[key]-old[key] for key in set(stats)|set(old)}
        for b in tasks[row['id']]['bindings']:
            ticks=reads=writes=0
            for macro,group in b['macro_binding'].items():
                meta=h['leaf_inventory'][group];r=delta.get(macro+':read',0);w=delta.get(macro+':write',0)
                reads+=r;writes+=w
                ticks+=delta.get(macro+':core',0)+r*meta['io_read_ticks']+w*meta['io_write_ticks']
                ticks+=r*descriptor_ticks(h['virtual_memory'],1,'load',meta['io_write_ticks'])
                ticks+=w*descriptor_ticks(h['virtual_memory'],1,'store',meta['io_read_ticks'])
            b['ticks']+=ticks;b['external_read_words']+=reads;b['external_write_words']+=writes
            if min(b['ticks'],b['external_read_words'],b['external_write_words'])<0:
                raise ValueError('negative prepared native work')
        row['body']=body;row['primitive_counts']=dict(stats)
    ir['operand_preparations']=preparations
    ir['required_external_bytes']=external*16
    ir['preparation_reuse_scope']={'prepared_dots':len(preparations),
        'scope':'A split32 hoisted out of output columns; explicit external components; same native arithmetic',
        'excluded':'cross-Dot preparation reuse, S64 accumulator spill, new arithmetic, unbounded SRAM or overlapped DMA'}
    return ir


class PreparedOperands:
    """Numeric external-memory records; never an unbounded private-S array.

    The native split32 call count/cost is checked separately from these values.
    A materialized one-dimensional external region supplies all column uses.
    """
    def __init__(self,ir):
        self.plans=ir.get('operand_preparations',{});self.events=[]
        self.current_records=None

    def prepare(self,node,a):
        import numpy as np
        p=self.plans.get(node['id'])
        if not p:return a
        if p['input']!=node['inputs'][0]:raise ValueError('prepared source identity differs')
        shape=tuple(node['shape'][:-1])+(p['K'],)
        source=np.broadcast_to(a,shape).reshape(p['rows'],p['K'])
        if source.size and (source.min()<-(1<<31) or source.max()>=(1<<31)):
            raise ValueError('prepared source not S32')
        external=np.empty(p['external_words'],dtype=np.int64)
        records=external.reshape(p['rows'],p['K'],3)
        records[:,:,0]=(source+32768)%65536-32768
        records[:,:,1]=source>>16
        records[:,:,2]=(records[:,:,0]<0).astype(np.int64)
        if external.min()<-32768 or external.max()>32767:raise ValueError('prepared component not S16')
        # Reconstructed operands are read from the new external records, rather
        # than silently using the original A in the transformed calculation.
        restored=(records[:,:,0]+65536*(records[:,:,1]+records[:,:,2])).reshape(shape)
        if not np.array_equal(restored.reshape(source.shape),source):raise ValueError('prepared component identity failed')
        self.current_records=(node['id'],records)
        self.events.append({'primitive':node['id'],'split_calls':source.size,
            'external_words':external.size,'base':p['external_base'],
            'last_address':address(p,p['rows']-1,p['K']-1,2)})
        return restored

    def report(self):
        if len(self.events)!=len(self.plans):raise ValueError('prepared execution coverage differs')
        return {'passed':True,'calls':len(self.events),'events':self.events,
            'scope':'explicit external component records consumed numerically; native commands/cost checked independently; not RTL'}


def recipe(node, components, external_base, external_limit_words):
    if node['op'] != 'Dot' or components[0] != 3:
        return None
    shape = node['shape']; k = node['attributes']['length']
    if len(shape)<2 or any(type(n)!=int or n<1 for n in shape) or type(k)!=int or k<1:
        raise ValueError('concrete positive Dot dimensions required')
    columns = shape[-1]; rows = math.prod(shape)//columns
    if columns == 1:
        return None
    words = rows*k*components[0]
    if external_base<0 or external_base+words>external_limit_words:
        return None
    return {'kind':'dot-A-prepare-once-v1', 'primitive':node['id'],
            'input':node['inputs'][0], 'rows':rows, 'columns':columns, 'K':k,
            'components':components[0], 'old_split_calls':rows*columns*k,
            'new_split_calls':rows*k, 'external_base':external_base,
            'external_words':words, 'layout':'row-k-component',
            'lifetime':'prepare ACK before first consume; retain through last output STORE ACK',
            'accumulator':'all preparation before live dot context; unchanged full-K accumulation and final rounding'}


def address(plan, row, k, component):
    if not (0<=row<plan['rows'] and 0<=k<plan['K'] and 0<=component<plan['components']):
        raise ValueError('prepared operand address outside extent')
    return plan['external_base']+((row*plan['K']+k)*plan['components']+component)


def unpack(raw):
    """Independent value identity for the already-qualified split32 recipe."""
    if not -(1<<31)<=raw<(1<<31):
        raise ValueError('S32 operand required')
    low=(raw+32768)%65536-32768
    return low, raw>>16, int(low<0)
