"""Tensor address views: index transformations, never free data permutation.

The lowerer may alias an existing record only when the requested elements are
contiguous and aligned in that record. Otherwise it must select another layout
or an actual adapter recipe.
"""
import math
from solver import Unsupported


def coordinates(index,shape):
    if index<0 or index>=math.prod(shape):raise Unsupported('view index outside tensor')
    result=[]
    for extent in reversed(shape):result.append(index%extent);index//=extent
    return list(reversed(result))


def flat(coords,shape):
    result=0
    for i,extent in zip(coords,shape):
        if not 0<=i<extent:raise Unsupported('view coordinate outside source')
        result=result*extent+i
    return result


def broadcast_index(index,output_shape,input_shape):
    if len(input_shape)>len(output_shape):raise Unsupported('broadcast rank differs')
    padded=[1]*(len(output_shape)-len(input_shape))+input_shape
    if any(a not in (1,b) for a,b in zip(padded,output_shape)):raise Unsupported('invalid broadcast dimensions')
    coords=coordinates(index,output_shape)
    return flat([0 if d==1 else c for c,d in zip(coords,padded)],padded)


def view(node,values):
    op=node['op'];ins=node['inputs'];out=node['outputs'][0]
    target=values[out]['shape'];source=values[ins[0]]['shape'];attrs=node.get('attributes',{})
    allowed={'Reshape':{'allowzero'},'Transpose':{'perm'},'Concat':{'axis'},
             'Squeeze':{'axes'},'Unsqueeze':{'axes'},'Slice':set(),'Identity':set(),'Expand':set(),'Broadcast':set()}
    if set(attrs)-allowed.get(op,set()):raise Unsupported('unregistered view attribute')
    if any(not isinstance(x,int) or x<1 for dims in (source,target) for x in dims):
        raise Unsupported('view needs resolved positive shapes')
    if op in ('Reshape','Unsqueeze','Squeeze','Identity'):
        if math.prod(source)!=math.prod(target):raise Unsupported('view changes element count')
        if op=='Reshape' and attrs.get('allowzero',0):raise Unsupported('allowzero reshape needs explicit handling')
        if op=='Identity' and source!=target:raise Unsupported('identity shape differs')
        return lambda i:(ins[0],i)
    if op=='Transpose':
        perm=attrs.get('perm',list(reversed(range(len(source)))))
        if sorted(perm)!=list(range(len(source))) or target!=[source[p] for p in perm]:
            raise Unsupported('invalid transpose permutation')
        def locate(i):
            coords=coordinates(i,target);old=[0]*len(source)
            for j,p in enumerate(perm):old[p]=coords[j]
            return ins[0],flat(old,source)
        return locate
    if op in ('Expand','Broadcast'):
        return lambda i:(ins[0],broadcast_index(i,target,source))
    if op=='Concat':
        axis=attrs.get('axis',0)%len(target)
        shapes=[values[n]['shape'] for n in ins]
        if sum(s[axis] for s in shapes)!=target[axis] or any(len(s)!=len(target) or any(s[d]!=target[d] for d in range(len(target)) if d!=axis) for s in shapes):
            raise Unsupported('concat shapes differ')
        def locate(i):
            coords=coordinates(i,target);pos=coords[axis]
            for name,dims in zip(ins,shapes):
                if pos<dims[axis]:coords[axis]=pos;return name,flat(coords,dims)
                pos-=dims[axis]
            raise Unsupported('concat index outside sources')
        return locate
    if op=='Slice':
        params=[]
        for name in ins[1:]:
            if 'constant' not in values[name]:raise Unsupported('dynamic slice parameters need an address program')
            x=values[name]['constant'];params.append(x if isinstance(x,list) else [x])
        if len(params)<2:raise Unsupported('slice starts/ends missing')
        starts,ends=params[:2];axes=params[2] if len(params)>2 else list(range(len(starts)))
        steps=params[3] if len(params)>3 else [1]*len(starts)
        if not len(starts)==len(ends)==len(axes)==len(steps):raise Unsupported('slice parameter arity differs')
        slices={}
        for start,end,axis,step in zip(starts,ends,axes,steps):
            axis%=len(source)
            if axis in slices or not step:raise Unsupported('invalid slice axis/step')
            slices[axis]=range(*slice(start,end,step).indices(source[axis]))
        expected=[len(slices[d]) if d in slices else source[d] for d in range(len(source))]
        if expected!=target:raise Unsupported('slice shape differs')
        def locate(i):
            coords=coordinates(i,target)
            for axis,rng in slices.items():coords[axis]=rng[coords[axis]]
            return ins[0],flat(coords,source)
        return locate
    raise Unsupported('unknown address view '+op)
