"""Independent array-index oracle for every lowered native operand requirement."""
from math import prod
import numpy as np

def verify(graph, recipes):
    source={t['id']:t for t in graph['tasks']}
    if [t['id'] for t in recipes['tasks']]!=list(source):raise ValueError('source task coverage')
    producers={v:t for t in graph['tasks'] for v in t['outputs']}
    arrays={};roots={}
    def array(v):
        if v in arrays:return arrays[v]
        task=producers.get(v);dims=graph['values'][v]['shape']
        if not task or task['kind']!='View':
            arrays[v]=np.arange(prod(dims),dtype=np.int64).reshape(dims);roots[v]=v
        else:
            op=task['details']['operation'];x=array(op['inputs'][0]);kind=op['op']
            if kind=='Transpose':y=x.transpose(op.get('attributes',{}).get('perm'))
            elif kind in ('Reshape','Squeeze','Unsqueeze'):y=x.reshape(dims)
            elif kind=='Expand':y=np.broadcast_to(x,dims)
            elif kind=='Identity':y=x
            else:raise ValueError('independent oracle missing '+kind)
            arrays[v]=y;roots[v]=roots[op['inputs'][0]]
        return arrays[v]
    access_count=0;element_count=0
    def check(access,expected,v):
        nonlocal access_count,element_count
        array(v)
        if access['value']!=v or access['root']!=roots[v]:raise ValueError('wrong operand identity')
        wanted=np.asarray(expected).reshape(-1)
        pos=0
        for segment in access['segments']:
            n=segment['elements'];start=segment['source_element']
            if segment['destination_element']!=pos or n<=0:raise ValueError('non-covering transfer')
            np.testing.assert_array_equal(wanted[pos:pos+n],np.arange(start,start+n),err_msg=v)
            pos+=n
        if pos!=wanted.size or pos!=access['elements']:raise ValueError('operand length mismatch')
        access_count+=1;element_count+=pos
    kinds={}
    for task in recipes['tasks']:
        t=source[task['id']];kind=t['kind'];d=t['details'];tiles=task['tiles']
        if task['after']!=t['after'] or task['kind']!=kind:raise ValueError('source dependencies changed')
        if kind=='View':
            if tiles:raise ValueError('view should only prescribe addresses')
            continue
        out,=t['outputs'];dims=graph['values'][out]['shape'];covered=0
        for tile in tiles:
            write=tile['write']
            if write['value']!=out or write['element_offset']!=covered or write['elements']<=0:
                raise ValueError('output has gap/overlap/wrong owner')
            covered+=write['elements']
        if covered!=prod(dims):raise ValueError('incomplete operator output')
        if kind=='Attention':
            q=d['query']['tensor'];k=d['transposed_key']['tensor'];v=d['value']['tensor']
            qa,ka,va=map(array,(q,k,v));batch,heads,tokens,width=qa.shape;index=0
            mask=d.get('mask')
            masks=np.zeros((batch,heads,tokens,ka.shape[-1])) if not mask else np.broadcast_to(
                np.asarray(graph['values'][mask['tensor']]['constant']),(batch,heads,tokens,ka.shape[-1]))
            for b in range(batch):
                for h in range(heads):
                    for token in range(tokens):
                        tile=tiles[index];index+=1
                        visible=np.flatnonzero(masks[b,h,token]==0).tolist()
                        if visible!=list(range(len(visible))) or tile['context']!=len(visible) or tile['position']!=len(visible)-1:
                            raise ValueError('wrong source-mask prefix')
                        check(tile['read'][0],qa[b,h,token,:],q)
                        if len(tile['key_rows'])!=len(visible) or len(tile['value_rows'])!=len(visible):raise ValueError('KV prefix coverage')
                        for j in visible:
                            check(tile['key_rows'][j],ka[b,h,:,j],k);check(tile['value_rows'][j],va[b,h,j,:],v)
        elif kind=='Concat':
            names=d['operation']['inputs'];axis=d['operation'].get('attributes',{}).get('axis',0)
            indices=np.concatenate([array(v) for v in names],axis=axis).reshape(-1)
            owners=np.concatenate([np.full(array(v).shape,i) for i,v in enumerate(names)],axis=axis).reshape(-1)
            for tile in tiles:
                start=tile['write']['element_offset'];end=start+tile['write']['elements']
                ids=np.unique(owners[start:end])
                if len(ids)!=1:raise ValueError('Concat tile crosses source boundary')
                check(tile['read'][0],indices[start:end],names[int(ids[0])])
        elif kind=='RoPE':
            names=[d['input']['tensor'],d['cosine']['tensor'],d['sine']['tensor']]
            tensors=[np.broadcast_to(array(v),dims).reshape(-1,dims[-1]) for v in names]
            for i,tile in enumerate(tiles):
                for operand,v,rows in zip(tile['read'],names,tensors):check(operand,rows[i],v)
        elif kind=='Add':
            names=d['operation']['inputs']
            tensors=[np.broadcast_to(array(v),dims).reshape(-1,dims[-1]) for v in names]
            for i,tile in enumerate(tiles):
                for operand,v,rows in zip(tile['read'],names,tensors):check(operand,rows[i],v)
        elif kind=='RMSNorm':
            x,gamma,_=d['operation']['inputs'];rows=array(x).reshape(-1,dims[-1])
            for i,tile in enumerate(tiles):
                check(tile['read'][0],rows[i],x);check(tile['read'][1],array(gamma),gamma)
        elif kind=='MatMul':
            x,w=d['operation']['inputs'];k,n=graph['values'][w]['shape'];rows=array(x).reshape(-1,k)
            for tile in tiles:
                row_index=tile['write']['element_offset']//n
                check(tile['read'][0],rows[row_index],x)
                m=tile['weight']
                if m['value']!=w or m['k']!=k or m['columns']!=tile['write']['elements'] or m['first_column']!=tile['write']['element_offset']%n:
                    raise ValueError('projection weight/output tile mismatch')
        elif kind=='SwiGLUFFN':
            x=d['activation'];rows=array(x).reshape(-1,dims[-1])
            for i,tile in enumerate(tiles):
                check(tile['read'][0],rows[i],x)
                if tile['weights']!=d['weights']:raise ValueError('wrong FFN weights')
        elif kind=='Gather':
            w,index=d['operation']['inputs'];indices=array(index).reshape(-1)
            for i,tile in enumerate(tiles):
                check(tile['read'][0],indices[i:i+1],index)
                if tile['indexed_table']!=w:raise ValueError('wrong gather table')
        else:raise ValueError('oracle missing operator '+kind)
        kinds[kind]=kinds.get(kind,0)+len(tiles)
    return {'passed':True,'tasks':len(recipes['tasks']),'operand_accesses':access_count,
            'element_addresses_checked':element_count,'tiles_by_kind':kinds,
            'scope':'independent full-graph source-address, output-coverage and dependency validation; not instruction or runtime acceptance'}
