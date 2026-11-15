"""Graph-derived operand tiles before hardware candidate admission.

These are data requirements, not chosen mappings or an instruction plan.
Every access resolves through exact view indices to a source allocation.
"""
from itertools import product
from math import prod
from value_layout import build,source_index,strides

def lower(graph, layouts=None):
    layouts=build(graph) if layouts is None else layouts
    values=graph['values'];maps=layouts['values']
    def shape(v):return values[v]['shape']
    def flat(coord, dims):return sum(a*b for a,b in zip(coord,strides(dims)))
    def access(v, indices):
        segments=[]
        for offset,index in enumerate(indices):
            physical=source_index(maps[v],index)
            if segments and physical==segments[-1]['source_element']+segments[-1]['elements']:
                segments[-1]['elements']+=1
            else:segments.append({'destination_element':offset,'source_element':physical,'elements':1})
        return {'value':v,'root':maps[v]['root'],'elements':sum(s['elements'] for s in segments),
                'segments':segments}
    def row(v,i,width):return access(v,range(i*width,(i+1)*width))
    def output(v,i,width):return {'value':v,'element_offset':i*width,'elements':width}
    def constant(v):
        if 'constant' not in values[v]:raise ValueError('constant required: '+v)
        return values[v]['constant']
    def scalar(v):
        x=constant(v)
        while isinstance(x,list):
            if len(x)!=1:raise ValueError('scalar required')
            x=x[0]
        return x
    tasks=[]
    for t in graph['tasks']:
        kind=t['kind'];d=t['details'];tiles=[]
        if kind=='View':
            dst=t['outputs'][0]
            tasks.append({'id':t['id'],'kind':kind,'after':t['after'],'alias':maps[dst],'tiles':[]})
            continue
        out,=t['outputs'];oshape=shape(out)
        if kind=='RMSNorm':
            x,gamma,epsilon=d['operation']['inputs'];width=shape(x)[-1]
            if shape(gamma)!=[width]:raise ValueError('RMS gamma shape')
            for i in range(prod(oshape[:-1])):
                tiles.append({'read':[row(x,i,width),row(gamma,0,width)],
                              'write':output(out,i,width),'epsilon':scalar(epsilon),'reduction_elements':width})
        elif kind=='Add':
            op=d['operation'];width=oshape[-1]
            for prefix in product(*(range(x) for x in oshape[:-1])):
                reads=[]
                for v in op['inputs']:
                    dims=shape(v);aligned=[1]*(len(oshape)-len(dims))+dims
                    if any(a!=1 and a!=b for a,b in zip(aligned,oshape)):raise ValueError('ADD broadcast')
                    indexes=[]
                    for j in range(width):
                        coord=[0 if a==1 else b for a,b in zip(aligned,(*prefix,j))]
                        indexes.append(flat(coord[-len(dims):],dims) if dims else 0)
                    reads.append(access(v,indexes))
                i=flat(prefix,oshape[:-1]);tiles.append({'read':reads,'write':output(out,i,width)})
        elif kind=='MatMul':
            x,w=d['operation']['inputs'];k,n=shape(w)
            if shape(x)[-1]!=k or oshape!=shape(x)[:-1]+[n]:raise ValueError('MatMul shape')
            for i in range(prod(shape(x)[:-1])):
                for first in range(0,n,128):
                    count=min(128,n-first)
                    tiles.append({'read':[row(x,i,k)],
                        'weight':{'value':w,'input_axis':0,'output_axis':1,'first_column':first,'columns':count,'k':k},
                        'write':{'value':out,'element_offset':i*n+first,'elements':count}})
        elif kind=='SwiGLUFFN':
            x=d['activation'];w0,w1,w2=d['weights'];k,mid=shape(w0)
            if shape(w1)!=[k,mid] or shape(w2)!=[mid,k] or shape(x)[-1]!=k or oshape!=shape(x):
                raise ValueError('FFN dimensions')
            for i in range(prod(oshape[:-1])):
                tiles.append({'read':[row(x,i,k)],'weights':[w0,w1,w2],
                              'hidden':k,'intermediate':mid,'write':output(out,i,k)})
        elif kind=='Gather':
            w,index=d['operation']['inputs'];axis=d['operation'].get('attributes',{}).get('axis',0)
            if axis!=0 or len(shape(w))!=2 or oshape!=shape(index)+[shape(w)[1]]:
                raise ValueError('native row gather shape')
            width=shape(w)[1]
            for i in range(prod(shape(index))):
                tiles.append({'read':[row(index,i,1)],'indexed_table':w,'table_rows':shape(w)[0],
                              'index_dtype':values[index]['dtype'],'write':output(out,i,width)})
        elif kind=='RoPE':
            x=d['input']['tensor'];cos=d['cosine']['tensor'];sin=d['sine']['tensor'];dims=shape(x)
            if len(dims)!=4 or d['normalized_axis']!=3:raise ValueError('RoPE rank/axis')
            width=dims[-1]
            for prefix in product(*(range(a) for a in dims[:-1])):
                reads=[]
                for v in (x,cos,sin):
                    vdims=shape(v);aligned=[1]*(len(dims)-len(vdims))+vdims
                    if any(a!=1 and a!=b for a,b in zip(aligned,dims)):raise ValueError('RoPE broadcast')
                    inds=[]
                    for j in range(width):
                        c=[0 if a==1 else b for a,b in zip(aligned,(*prefix,j))]
                        inds.append(flat(c[-len(vdims):],vdims))
                    reads.append(access(v,inds))
                tiles.append({'read':reads,'write':output(out,flat(prefix,dims[:-1]),width),
                              'rotation':'half-split','elements':width})
        elif kind=='Concat':
            op=d['operation'];names=op['inputs'];rank=len(oshape)
            axis=op.get('attributes',{}).get('axis',0)
            if not -rank<=axis<rank:raise ValueError('Concat axis')
            axis%=rank
            if any(len(shape(v))!=rank or any(shape(v)[j]!=oshape[j] for j in range(rank) if j!=axis) for v in names):
                raise ValueError('Concat non-axis shape')
            if sum(shape(v)[axis] for v in names)!=oshape[axis]:raise ValueError('Concat extent')
            outer=prod(oshape[:axis]);inner=prod(oshape[axis+1:])
            for i in range(outer):
                destination=i*oshape[axis]*inner
                for v in names:
                    width=shape(v)[axis]*inner
                    for first in range(0,width,2048):
                        count=min(2048,width-first)
                        tiles.append({'read':[access(v,range(i*width+first,i*width+first+count))],
                                      'write':{'value':out,'element_offset':destination+first,'elements':count}})
                    destination+=width
        elif kind=='Attention':
            q=d['query']['tensor'];k=d['transposed_key']['tensor'];v=d['value']['tensor']
            b,h,tokens,width=shape(q);kdims=shape(k);vdims=shape(v)
            kv_tokens=kdims[-1]
            if kdims!=[b,h,width,kv_tokens] or vdims!=[b,h,kv_tokens,width] or oshape!=[b,h,tokens,width]:
                raise ValueError('Attention Q/K/V dimensions')
            import numpy as np
            mask=d.get('mask')
            m=np.zeros((b,h,tokens,kv_tokens)) if not mask else np.broadcast_to(
                np.asarray(constant(mask['tensor'])),(b,h,tokens,kv_tokens))
            for bi in range(b):
                for hi in range(h):
                    for ti in range(tokens):
                        row_mask=m[bi,hi,ti]
                        visible=[j for j,z in enumerate(row_mask) if float(z)==0]
                        if not visible or visible!=list(range(len(visible))) or any(
                            not (float(z)<=-1e20) for z in row_mask[len(visible):]):
                            raise ValueError('mask cannot be represented by a native prefix')
                        context=len(visible)
                        qr=access(q,(flat((bi,hi,ti,j),shape(q)) for j in range(width)))
                        kr=[access(k,(flat((bi,hi,j,tj),kdims) for j in range(width))) for tj in visible]
                        vr=[access(v,(flat((bi,hi,tj,j),vdims) for j in range(width))) for tj in visible]
                        tiles.append({'read':[qr],'key_rows':kr,'value_rows':vr,
                          'context':context,'position':context-1,'scale':scalar(d['scale']['tensor']),
                          'kv_layout_requirement':'contiguous head-specific rows; encode packing transfers when source layout differs',
                          'write':output(out,(bi*h+hi)*tokens+ti,width)})
        else:raise ValueError('missing operand recipe: '+kind)
        tasks.append({'id':t['id'],'kind':kind,'after':t['after'],'tiles':tiles})
    return {'schema':'native-operand-recipes/1','source_model_sha256':graph['source_model_sha256'],
            'tasks':tasks,'scope':'source-indexed operand requirements; hardware mapping, transfers, numerical formats and instruction encoding are not yet selected'}
