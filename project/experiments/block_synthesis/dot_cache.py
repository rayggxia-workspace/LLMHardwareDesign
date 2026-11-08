"""Finite, read-only M.S stripes; arithmetic templates remain unchanged.

Borrowed loop/data reuse idea: Timeloop (ISPASS 2019), not its cost model.
Every output still finishes its whole K reduction before the next output.
No S64 accumulator spill, extra context, packed storage or DMA overlap.
"""
from copy import deepcopy
import json
import math

from memory import descriptor_ticks


def variants(ir, *, state_cost=False):
    """Extend the existing candidate pool; no additional user input file."""
    h=ir['hardware'];by_kernel={}
    for node in ir['primitive_program']['instructions']:
        if node['op']=='Dot':by_kernel.setdefault(node['kernel'],[]).append(node)
    total=0
    for task in ir['tasks']:
        dots=by_kernel.get(task['id'],[])
        # A kernel with multiple reductions needs a separate lifetime proof.
        if len(dots)!=1:continue
        node=dots[0];ca,cb=ir['native_operand_components'][node['id']]
        columns=node['shape'][-1];rows=math.prod(node['shape'])//columns;k=node['attributes']['length']
        tag=json.dumps([node['inputs'][0],node['shape'][:-1],k,ca],separators=(',',':'))
        for original in list(task['bindings']):
            group=original['macro_binding']['M'];meta=h['leaf_inventory'][group];site=meta['site']
            if h['resources'][meta['io_resource']]!=1:continue
            maximum=min(k,(h['sites'][site]['words']-9)//(rows*ca))
            if maximum<0:continue
            ext=descriptor_ticks(h['virtual_memory'],1,'load',meta['io_write_ticks'])
            choices={0,maximum};power=1
            while power<=maximum:choices.add(power);power*=2
            for stripe in sorted(choices):
                b=deepcopy(original);n=rows*columns
                # Partial's three operand loads are A, B, and the high-half
                # zero packet. B components live in staging[4:7] for one K.
                # A stripes live at S[9:], zero at S[8]; original slots[0:8]
                # and all split32/core commands are retained.
                old=3*n*ca*cb*k
                a_reads=rows*ca*stripe+n*ca*cb*(k-stripe)
                b_reads=n*cb*k
                new=a_reads+b_reads+1
                saved=old-new
                # For a one-term dot, zero is still a real initial read.
                if saved<0:continue
                warm_saved=rows*ca*stripe
                b['id']+=';M-read-cache='+str(stripe)
                b['ticks']-=saved*ext;b['external_read_words']-=saved
                b['warm_ticks']=b['ticks']-warm_saved*ext
                b['warm_read_words']=b['external_read_words']-warm_saved
                b['scratch_by_site'][site]=9+rows*ca*stripe
                b['scratch_words']=max(b['scratch_by_site'].values())
                b['read_cache']={'kind':'M-dot-read-stripe-v1','primitive':node['id'],
                    'site':site,'tag':tag,'stripe':stripe,'rows':rows,'columns':columns,'K':k,
                    'components':[ca,cb],'cache_words':rows*ca*stripe,
                    'layout':{'scratch':[0,8],'zero':8,'A_start':9,'B_staging':[4,4+cb]},
                    'cold_partial_external_reads':new,'warm_partial_external_reads':new-warm_saved,
                    'baseline_partial_external_reads':old,
                    'protocol':'LOAD completes S commit before read; all original STORE ACKs retained',
                    'loop_order':'output row, output column, K, A component, B component',
                    'arithmetic':'unchanged split32, partial and final rounding; one live M context'}
                if state_cost:
                    b['read_cache'].update(cost_model='dot-prefix-state-v2',load_ticks=ext)
                task['bindings'].append(b);total+=1
    ir['read_cache_scope']={'added_bindings':total,
        'scope':'read-only M Dot stripes and within-K B/zero reuse; persistent across matching SSA inputs',
        'excluded':'cross-kernel dirty result retention, other primitive caches, arithmetic/reduction rewrites'}
    return ir
