"""Numerical interpreter for the selected, finite M.S read-cache windows.

Simulator arrays representing whole external tensors are not private SRAM.
Only packed[rows,stripe,components] is a retained local allocation. The exact
S64 product bound in wide_program makes partitioning the sum lossless; the
same final rounding is performed once, after prefix and streamed suffix.
"""
from copy import deepcopy
import numpy as np


def order_program(program,plan):
    """Execute each kernel in DP decision order, resolving address metadata.

    An arithmetic dependency absent from the kernel DAG is an error, rather
    than silently executing an extra kernel ahead of the selected schedule.
    """
    nodes={n['id']:n for n in program['instructions']};groups={};done=set();ordered=[]
    for n in program['instructions']:groups.setdefault(n['kernel'],[]).append(n)
    def emit(n,kernel=None):
        if n['id'] in done:return
        if n['op'] not in ('Constant','View','Mask') and n['kernel']!=kernel:
            raise ValueError('selected kernel order lacks primitive dependency '+n['id'])
        for name in n['inputs']:
            if name in nodes:emit(nodes[name],kernel)
        done.add(n['id']);ordered.append(n)
    for row in plan['tasks']:
        for n in groups[row['id']]:emit(n,row['id'])
    for name in program['outputs'].values():
        if name in nodes:emit(nodes[name])
    result=deepcopy(program);result['instructions']=ordered
    return result


class DotCache:
    def __init__(self,ir,plan):
        tasks={t['id']:t for t in ir['tasks']};self.selected={};self.resident={};self.events=[]
        self.capacity={s:v['words'] for s,v in ir['hardware']['sites'].items()}
        for row in plan['tasks']:
            b=next(b for b in tasks[row['id']]['bindings'] if b['id']==row['binding'])
            self.selected[row['id']]=(b,row)

    def dot(self,node,a,b):
        binding,row=self.selected[node['kernel']];c=binding.get('read_cache')
        if not c:return np.matmul(a,b)
        if c['primitive']!=node['id']:raise ValueError('cache points at a different Dot')
        site=c['site'];t=c['stripe'];ca=c['components'][0];shape=node['shape'];k=c['K']
        if 9+c['cache_words']>self.capacity[site]:raise ValueError('numeric SRAM capacity exceeded')
        source=np.broadcast_to(a,tuple(shape[:-2])+(shape[-2],k)).reshape(c['rows'],k)
        old=self.resident.get(site)
        if row['cache_hit']:
            if not old or old['tag']!=c['tag'] or old['stripe']<t:raise ValueError('uninitialized SRAM cache read')
            packed=old['packed'][:,:t,:].copy()
        else:
            x=source[:,:t];low=((x+32768)%65536-32768).astype(np.int64)
            packed=np.stack([low,x>>16,(low<0).astype(np.int64)],axis=-1) if ca==3 else low[...,None].copy()
        if packed.size!=c['cache_words'] or (packed.size and (packed.min()<-32768 or packed.max()>32767)):
            raise ValueError('SRAM scalar component encoding differs')
        restored=packed[...,0] if ca==1 else packed[...,0]+65536*(packed[...,1]+packed[...,2])
        # This assertion verifies immutable SSA identity and stale-data safety;
        # the actual arithmetic below consumes restored SRAM data.
        if not np.array_equal(restored,source[:,:t]):raise ValueError('cached SRAM value differs from immutable source')
        if t:self.resident[site]={'tag':c['tag'],'stripe':t,'packed':packed}
        else:self.resident.pop(site,None)
        left=restored.reshape(tuple(shape[:-2])+(shape[-2],t))
        broadcast_b=np.broadcast_to(b,tuple(shape[:-2])+(k,shape[-1]))
        out=np.matmul(left,broadcast_b[...,:t,:]) if t else np.zeros(shape,dtype=np.int64)
        if t<k:out+=np.matmul(np.broadcast_to(a,tuple(shape[:-2])+(shape[-2],k))[...,t:],broadcast_b[...,t:,:])
        self.events.append({'primitive':node['id'],'kernel':node['kernel'],'site':site,
            'stripe':t,'words':c['cache_words'],'cache_hit':row['cache_hit'],
            'partial_external_reads':c['warm_partial_external_reads'] if row['cache_hit'] else c['cold_partial_external_reads']})
        return out

    def report(self):
        expected=sum('read_cache' in b for b,_ in self.selected.values())
        if len(self.events)!=expected:raise ValueError('cache execution coverage differs')
        return {'passed':True,'calls':len(self.events),'hits':sum(e['cache_hit'] for e in self.events),
            'peak_retained_words':max((e['words'] for e in self.events),default=0),'events':self.events,
            'scope':'actual integer SRAM stripe contents used in Dot replay; symbolic traffic independently checked; no RTL timing claim'}
