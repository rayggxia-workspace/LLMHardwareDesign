"""Compose independently addressed elements into an explicit finite row tile.

No runtime arithmetic or gather is hidden here. Scalar input words may share
identity; all produced scratch words receive a declared, bounded backing slot.
The allocator must still perform every required transfer and layout change.
"""
from copy import deepcopy
import hashlib
import json


def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def build(graphs,*,scratch_start,external_capacity_words,max_rows):
    if (not graphs or type(max_rows)!=int or not 1<=len(graphs)<=max_rows or
        type(scratch_start)!=int or type(external_capacity_words)!=int or
        not 0<=scratch_start<external_capacity_words):raise ValueError('bounded explicit row tile required')
    first=graphs[0]
    if any(g.get('kind')!='native-pointwise-ssa-v1' or g['primitives']!=first['primitives'] or
           g['shape']!=first['shape'] or len(g['operations'])!=len(first['operations']) for g in graphs):
        raise ValueError('same original scalar recipe required for each row')
    if len({g['index'] for g in graphs})!=len(graphs):raise ValueError('row elements repeat')
    if any(type(o.get('external_address'))!=int or not 0<=o['external_address']<scratch_start
           for g in graphs for o in g['objects'].values()):raise ValueError('scratch overlaps the original address extent')
    objects={};maps=[];initial={};next_scratch=scratch_start;outputs={};live={};primitives=[]
    for row,g in enumerate(graphs):
        mapping={};final=set(g['primitive_outputs'].values())
        for key,o in g['objects'].items():
            if o['kind']=='produced':
                name=f'{row}:{key}';obj=deepcopy(o)
                obj['producer']=f'{row}:'+o['producer'];obj['primitive']=f'{row}:'+o['primitive']
                if key not in final:obj['external_address']=next_scratch;next_scratch+=1
            else:
                # Include the physical backing address and original metadata;
                # equal runtime numbers alone never justify identity sharing.
                identity=digest(o);name=initial.setdefault(identity,'input:'+str(len(initial)));obj=deepcopy(o)
            if name in objects and objects[name]!=obj:raise ValueError('row object identity collision')
            objects[name]=obj;mapping[key]=name
        maps.append(mapping)
        for primitive,key in g['primitive_outputs'].items():outputs[f'{row}:{primitive}']=mapping[key]
        for primitive,key in g['live_out'].items():live[f'{row}:{primitive}']=mapping[key]
        primitives.extend(f'{row}:{name}' for name in g['primitives'])
    if next_scratch>external_capacity_words:raise ValueError('finite row scratch exceeds external capacity')
    operations=[];groups=[]
    for at in range(len(first['operations'])):
        members=[]
        for row,g in enumerate(graphs):
            n=deepcopy(g['operations'][at]);mapping=maps[row]
            n.update(id=f'{row}:'+n['id'],primitive=f'{row}:'+n['primitive'],
                     inputs=[mapping[x] for x in n['inputs']],output=mapping[n['output']])
            if n['kind']=='M':n['terms']=[{**t,'a':mapping[t['a']],'b':mapping[t['b']]} for t in n['terms']]
            operations.append(n);members.append(n['id'])
        groups.append(members)
    source={'kind':'native-pointwise-ssa-v1','shape':[len(graphs)],'index':0,'primitives':primitives,
        'objects':objects,'operations':operations,'primitive_outputs':outputs,'live_out':live}
    from native_reuse import rewrite
    rewritten=rewrite(source)
    result={'kind':'native-pointwise-row-tile-v1','rows':len(graphs),'graphs':deepcopy(graphs),
        'maps':maps,'groups':groups,'graph':rewritten,'scratch_start':scratch_start,
        'scratch_words':next_scratch-scratch_start,'external_capacity_words':external_capacity_words,
        'source_sha256':[digest(g) for g in graphs],
        'scope':'original scalar native work in operation-major row order; no implicit runtime packing, transfer or service timing'}
    verify(result);return result


def verify(tile):
    """Reconstruct each row independently; does not call the merger/rewrite."""
    if tile.get('kind')!='native-pointwise-row-tile-v1':raise ValueError('wrong row tile graph kind')
    graphs=tile['graphs'];maps=tile['maps'];batch=tile['graph'];source=batch['reuse_proof']['source_graph']
    from native_reuse import verify as verify_reuse
    verify_reuse(batch,source)
    if (len(graphs)!=tile['rows'] or len(maps)!=len(graphs) or
        tile['source_sha256']!=[digest(g) for g in graphs] or
        len({g['index'] for g in graphs})!=len(graphs)):raise ValueError('row source binding differs')
    expected_ops=[];expected_groups=[];out={};live={};expected_objects={};scratch=[];initial_addresses={}
    for row,(g,mapping) in enumerate(zip(graphs,maps)):
        if g.get('kind')!='native-pointwise-ssa-v1' or set(mapping)!=set(g['objects']):raise ValueError('row mapping is incomplete')
        if (g['primitives'],g['shape'],len(g['operations']))!=(graphs[0]['primitives'],graphs[0]['shape'],len(graphs[0]['operations'])):
            raise ValueError('row recipes differ')
        final=set(g['primitive_outputs'].values())
        for key,o in g['objects'].items():
            actual=source['objects'][mapping[key]];expected=deepcopy(o)
            if o['kind']=='produced':
                expected['producer']=f'{row}:'+o['producer'];expected['primitive']=f'{row}:'+o['primitive']
                if key not in final:
                    expected['external_address']=actual['external_address'];scratch.append(actual['external_address'])
            else:
                addr=o['external_address']
                # Different opaque inputs must not alias the same external word.
                old=initial_addresses.get(addr)
                if old is not None and old!=o:raise ValueError('row source words alias')
                initial_addresses[addr]=o
            if actual!=expected:raise ValueError('row source object changed')
            old=expected_objects.get(mapping[key])
            if old is not None and old!=expected:raise ValueError('different row objects share identity')
            expected_objects[mapping[key]]=expected
        for name,key in g['primitive_outputs'].items():out[f'{row}:{name}']=mapping[key]
        for name,key in g['live_out'].items():live[f'{row}:{name}']=mapping[key]
    if (expected_objects!=source['objects'] or source['primitive_outputs']!=out or source['live_out']!=live or
        len(scratch)!=len(set(scratch)) or sorted(scratch)!=list(range(tile['scratch_start'],tile['scratch_start']+tile['scratch_words'])) or
        tile['scratch_start']+tile['scratch_words']>tile['external_capacity_words']):raise ValueError('row output or finite scratch differs')
    all_original=[o['external_address'] for g in graphs for o in g['objects'].values()]
    if any(type(a)!=int or not 0<=a<tile['scratch_start'] for a in all_original):raise ValueError('row original/scratch addresses overlap')
    # Every original produced word has one real backing slot after relocation.
    writes=[o['external_address'] for o in source['objects'].values() if o['kind']=='produced']
    if len(writes)!=len(set(writes)) or set(writes)&initial_addresses.keys():raise ValueError('row outputs alias live external data')
    for at in range(len(graphs[0]['operations'])):
        group=[]
        for row,g in enumerate(graphs):
            n=deepcopy(g['operations'][at]);mapping=maps[row]
            n['id']=f'{row}:'+n['id'];n['primitive']=f'{row}:'+n['primitive']
            n['inputs']=[mapping[x] for x in n['inputs']];n['output']=mapping[n['output']]
            if n['kind']=='M':
                for t in n['terms']:t['a']=mapping[t['a']];t['b']=mapping[t['b']]
            expected_ops.append(n);group.append(n['id'])
        expected_groups.append(group)
    if source['operations']!=expected_ops or tile['groups']!=expected_groups:raise ValueError('row native operations changed or reordered')
    return {'passed':True,'rows':len(graphs),'original_native_operations':len(expected_ops),
            'scratch_words':len(scratch),'live_out_commits':len(live)}


def units(tile):
    """Keep actual B identity; differing element values cannot share a B bank."""
    verify(tile);nodes={n['id']:n for n in tile['graph']['operations']};result=[]
    for members in tile['groups']:
        live=[nodes[name] for name in members if 'reuse_of' not in nodes[name]]
        if not live:continue
        first=live[0];batchable=first['kind']=='M'
        for n in live[1:]:
            if n['kind']!='M' or (n['k'],n['width'],n['shift'],len(n['terms']))!=(first['k'],first['width'],first['shift'],len(first['terms'])):
                batchable=False;break
            if any((t['b'],t['coefficient'],t['scale_shift'])!=(u['b'],u['coefficient'],u['scale_shift']) for t,u in zip(n['terms'],first['terms'])):
                batchable=False;break
        result.append({'id':first['id'],'members':[n['id'] for n in live],'batchable':batchable})
    return result
