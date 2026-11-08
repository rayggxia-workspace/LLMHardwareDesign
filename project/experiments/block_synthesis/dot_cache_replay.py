"""Numerical interpreter for the selected, finite M.S read-cache windows.

Simulator arrays representing whole external tensors are not private SRAM.
Only packed[rows,stripe,components] is a retained local allocation. The exact
S64 product bound in wide_program makes partitioning the sum lossless; the
same final rounding is performed once, after prefix and streamed suffix.
"""
from copy import deepcopy
import numpy as np
from preparation_reuse import PreparedOperands
from column_shards import leaves
from dynamic_columns import resized


def order_program(program,plan,stage_map=None):
    """Execute each kernel in DP decision order, resolving address metadata.

    An arithmetic dependency absent from the kernel DAG is an error, rather
    than silently executing an extra kernel ahead of the selected schedule.
    """
    nodes={n['id']:n for n in program['instructions']};groups={};done=set();ordered=[]
    stage_for={}
    for n in program['instructions']:
        owner=stage_map[n['id']]['execute'] if stage_map is not None and n['id'] in stage_map else n['kernel']
        stage_for[n['id']]=owner;groups.setdefault(owner,[]).append(n)
    def emit(n,kernel=None):
        if n['id'] in done:return
        if n['op'] not in ('Constant','View','Mask') and stage_for[n['id']]!=kernel:
            raise ValueError('selected kernel order lacks primitive dependency '+n['id'])
        for name in n['inputs']:
            if name in nodes:emit(nodes[name],kernel)
        done.add(n['id']);ordered.append(n)
    prepare={v['prepare']:k for k,v in (stage_map or {}).items() if 'prepare' in v}
    completed=set()
    for row in plan['tasks']:
        if row['id'] in prepare:
            n=nodes[prepare[row['id']]]
            if n['inputs'][0] in nodes:emit(nodes[n['inputs'][0]])
        else:
            for n in groups[row['id']]:
                if stage_map is not None and n['id'] in stage_map:
                    p=stage_map[n['id']].get('prepare')
                    if p is not None and p not in completed:raise ValueError('selected order omits operand preparation')
                emit(n,row['id'])
        completed.add(row['id'])
    for name in program['outputs'].values():
        if name in nodes:emit(nodes[name])
    result=deepcopy(program);result['instructions']=ordered
    return result


class DotCache:
    def __init__(self,ir,plan):
        tasks={t['id']:t for t in ir['tasks']};self.selected={};self.resident={};self.events=[]
        self.capacity={s:v['words'] for s,v in ir['hardware']['sites'].items()}
        self.prepared=PreparedOperands(ir)
        self.stage_map=ir.get('primitive_stages')
        for row in plan['tasks']:
            b=next(b for b in tasks[row['id']]['bindings'] if b['id']==row['binding'])
            self.selected[row['id']]=(b,row)

    def dot(self,node,a,b):
        a=self.prepared.prepare(node,a)
        task_id=self.stage_map[node['id']]['execute'] if self.stage_map is not None else node['kernel']
        binding,row=self.selected[task_id];c=binding.get('read_cache')
        if 'parallel_shards' in binding:
            shape=node['shape'];columns=shape[-1];covered=np.zeros(columns,dtype=bool)
            broadcast_b=np.broadcast_to(b,tuple(shape[:-2])+(node['attributes']['length'],columns))
            result=np.empty(shape,dtype=np.int64)
            services=row['evaluation']['services'];children=binding['parallel_shards']['children']
            if 'frontier_partition' in binding:
                children=[resized(c,*r) for c,r in zip(children,row['evaluation']['resolved_columns'])]
            if len(services)!=len(children):raise ValueError('numeric column service coverage differs')
            for child,service in zip(children,services):
                lo,hi=child['columns']
                if not 0<=lo<hi<=columns or covered[lo:hi].any():raise ValueError('numeric column overlap/range')
                covered[lo:hi]=True
                view={**node,'shape':shape[:-1]+[hi-lo]}
                result[...,lo:hi]=self._dot(view,a,broadcast_b[...,lo:hi],child['binding'],service)
            if not covered.all():raise ValueError('numeric missing output columns')
            return result
        return self._dot(node,a,b,binding,row)

    def _dot(self,node,a,b,binding,row):
        c=binding.get('read_cache')
        if not c:return np.matmul(a,b)
        if c['primitive']!=node['id']:raise ValueError('cache points at a different Dot')
        site=c['site'];t=c['stripe'];ca=c['components'][0];shape=node['shape'];k=c['K']
        if 9+c['cache_words']>self.capacity[site]:raise ValueError('numeric SRAM capacity exceeded')
        source=np.broadcast_to(a,tuple(shape[:-2])+(shape[-2],k)).reshape(c['rows'],k)
        old=self.resident.get(site)
        state_cost=c.get('cost_model')=='dot-prefix-state-v2'
        if state_cost:
            e=row['evaluation'];h=min(old['stripe'],t) if old and old['tag']==c['tag'] else 0
            if h!=e['reused_prefix']:raise ValueError('uninitialized SRAM cache prefix')
            x=source[:,h:t];low=((x+32768)%65536-32768).astype(np.int64)
            fresh=np.stack([low,x>>16,(low<0).astype(np.int64)],axis=-1) if ca==3 else low[...,None].copy()
            packed=np.concatenate([old['packed'][:,:h,:],fresh],axis=1) if h else fresh
        elif row['cache_hit']:
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
        if state_cost:
            retain=e['retained_prefix']
            if e['retention']=='discard':self.resident.pop(site,None)
            elif t:
                retained=np.concatenate([packed,old['packed'][:,t:retain,:]],axis=1) if retain>t else packed.copy()
                if 9+retained.size>self.capacity[site]:raise ValueError('retained SRAM capacity exceeded')
                self.resident[site]={'tag':c['tag'],'stripe':retain,'packed':retained}
            # t=0/preserve leaves a non-overwritten old cache intact.
        else:
            if t:self.resident[site]={'tag':c['tag'],'stripe':t,'packed':packed}
            else:self.resident.pop(site,None)
        left=restored.reshape(tuple(shape[:-2])+(shape[-2],t))
        broadcast_b=np.broadcast_to(b,tuple(shape[:-2])+(k,shape[-1]))
        out=np.matmul(left,broadcast_b[...,:t,:]) if t else np.zeros(shape,dtype=np.int64)
        if t<k:out+=np.matmul(np.broadcast_to(a,tuple(shape[:-2])+(shape[-2],k))[...,t:],broadcast_b[...,t:,:])
        self.events.append({'primitive':node['id'],'kernel':node['kernel'],'site':site,
            'stripe':t,'words':max(c['cache_words'],self.resident.get(site,{}).get('packed',np.empty(0)).size),'cache_hit':row['cache_hit'],
            'partial_external_reads':(c['cold_partial_external_reads']-c['rows']*ca*h) if state_cost else (c['warm_partial_external_reads'] if row['cache_hit'] else c['cold_partial_external_reads'])})
        return out

    def report(self):
        expected=sum('read_cache' in child for b,_ in self.selected.values() for child in leaves(b))
        if len(self.events)!=expected:raise ValueError('cache execution coverage differs')
        return {'passed':True,'calls':len(self.events),'hits':sum(e['cache_hit'] for e in self.events),
            'preparation':self.prepared.report(),
            'peak_retained_words':max((e['words'] for e in self.events),default=0),'events':self.events,
            'scope':'actual integer SRAM stripe contents used in Dot replay; symbolic traffic independently checked; no RTL timing claim'}
