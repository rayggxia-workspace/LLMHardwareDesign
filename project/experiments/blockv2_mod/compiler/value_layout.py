"""Exact index views for native candidate operand addressing.

A view is not an executable copy and does not assert hardware supports striding.
Consumers obtain source-contiguous runs and must encode their transfers or reject
the candidate. Non-view outputs define new allocations only after plan selection.
"""
from math import prod

def strides(shape):
    result=[];step=1
    for dim in reversed(shape):
        result.append(step);step*=dim
    return list(reversed(result))

def coordinates(index, shape):
    if not 0 <= index < prod(shape):raise ValueError('view index outside tensor')
    result=[]
    for step in strides(shape):
        result.append(index//step);index%=step
    return result

def shape_of(values,name):
    shape=values[name]['shape']
    if any(type(d) is not int or d<=0 for d in shape):
        raise ValueError('bind positive runtime dimensions before layout')
    return list(shape)

def build(graph):
    values=graph['values']
    layouts={name:{'root':name,'shape':shape_of(values,name),'steps':[]}
             for name in values}
    seen=set()
    for task in graph['tasks']:
        if not set(task.get('after',[]))<=seen:raise ValueError('layout requires topological graph')
        seen.add(task['id'])
        if task['kind']!='View':continue
        op=task['details']['operation'];kind=op['op'];a=op.get('attributes',{})
        src=op['inputs'][0];dst,=op['outputs']
        ishape=shape_of(values,src);oshape=shape_of(values,dst)
        step={'kind':kind,'input_shape':ishape,'output_shape':oshape}
        def constant(index):
            try:value=values[op['inputs'][index]]['constant']
            except (KeyError,IndexError):raise ValueError('view parameters must be shape-bound constants')
            return value if isinstance(value,list) else [value]
        if kind=='Transpose':
            perm=a.get('perm',list(reversed(range(len(ishape)))))
            if sorted(perm)!=list(range(len(ishape))) or [ishape[i] for i in perm]!=oshape:
                raise ValueError('invalid transpose')
            step['perm']=perm
        elif kind=='Reshape':
            target=constant(1);allowzero=a.get('allowzero',0)
            if len(target)!=len(oshape) or target.count(-1)>1:raise ValueError('invalid reshape shape')
            for i,d in enumerate(target):
                expect=ishape[i] if d==0 and not allowzero else d
                if expect!=-1 and expect!=oshape[i]:raise ValueError('reshape output differs from declared target')
            if prod(ishape)!=prod(oshape):raise ValueError('reshape changes element count')
        elif kind in ('Unsqueeze','Squeeze'):
            axes=constant(1) if len(op['inputs'])>1 else a.get('axes')
            rank=len(oshape) if kind=='Unsqueeze' else len(ishape)
            if axes is None:axes=[i for i,d in enumerate(ishape) if d==1]
            if any(not -rank<=i<rank for i in axes):raise ValueError('view axis out of bounds')
            axes=[i%rank for i in axes]
            if len(set(axes))!=len(axes):raise ValueError('duplicate view axes')
            bigger,smaller=(oshape,ishape) if kind=='Unsqueeze' else (ishape,oshape)
            if any(bigger[i]!=1 for i in axes) or [d for i,d in enumerate(bigger) if i not in axes]!=smaller:
                raise ValueError('squeeze/unsqueeze shape mismatch')
        elif kind=='Identity':
            if ishape!=oshape:raise ValueError('identity shape mismatch')
        elif kind=='Expand':
            target=constant(1);rank=max(len(ishape),len(target))
            inp=[1]*(rank-len(ishape))+ishape;want=[1]*(rank-len(target))+target
            if any(x!=y and x!=1 and y!=1 for x,y in zip(inp,want)):
                raise ValueError('incompatible broadcast')
            if [max(x,y) for x,y in zip(inp,want)]!=oshape:raise ValueError('expand shape mismatch')
        elif kind=='Slice':
            starts=constant(1);ends=constant(2)
            axes=constant(3) if len(op['inputs'])>3 else list(range(len(starts)))
            steps=constant(4) if len(op['inputs'])>4 else [1]*len(starts)
            if not len(starts)==len(ends)==len(axes)==len(steps):raise ValueError('slice parameters')
            if any(not -len(ishape)<=i<len(ishape) for i in axes):raise ValueError('slice axis')
            axes=[i%len(ishape) for i in axes]
            if len(set(axes))!=len(axes) or any(s==0 for s in steps):raise ValueError('slice axis/step')
            normalized=[[0,1] for _ in ishape];expected=list(ishape)
            for axis,start,end,increment in zip(axes,starts,ends,steps):
                lo,hi,inc=slice(start,end,increment).indices(ishape[axis])
                normalized[axis]=[lo,inc];expected[axis]=len(range(lo,hi,inc))
            if expected!=oshape:raise ValueError('slice output shape')
            step['axes']=normalized
        else:raise ValueError('unsupported index view '+kind)
        parent=layouts[src]
        layouts[dst]={'root':parent['root'],'shape':oshape,
                      'steps':[step]+parent['steps'],'producer_view':task['id']}
    return {'schema':'native-value-layout/1','source_model_sha256':graph['source_model_sha256'],
            'values':layouts,'scope':'address transformations only; consumer transfer encoding required'}

def source_index(layout,index):
    shape=layout['shape']
    if not 0<=index<prod(shape):raise ValueError('logical offset out of bounds')
    for step in layout['steps']:
        kind=step['kind'];ishape=step['input_shape']
        if kind in ('Reshape','Unsqueeze','Squeeze','Identity'):continue
        coord=coordinates(index,step['output_shape'])
        if kind=='Transpose':
            mapped=[0]*len(ishape)
            for out_axis,in_axis in enumerate(step['perm']):mapped[in_axis]=coord[out_axis]
        elif kind=='Expand':
            mapped=[0 if dim==1 else c for dim,c in zip(ishape,coord[-len(ishape):])] if ishape else []
        elif kind=='Slice':mapped=[lo+c*inc for c,(lo,inc) in zip(coord,step['axes'])]
        else:raise ValueError('unknown view step')
        index=sum(c*s for c,s in zip(mapped,strides(ishape)))
    return index

def contiguous_runs(layout, start=0, count=None):
    """Yield (logical_offset, root_element_offset, elements), all in element units."""
    size=prod(layout['shape']);count=size-start if count is None else count
    if type(start) is not int or type(count) is not int or start<0 or count<0 or start+count>size:
        raise ValueError('operand tile out of bounds')
    run=None
    for index in range(start,start+count):
        physical=source_index(layout,index)
        if run and physical==run[1]+run[2]:run[2]+=1
        else:
            if run:yield tuple(run)
            run=[index,physical,1]
    if run:yield tuple(run)
