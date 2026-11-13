"""Optional exact cover of a materialized high16 by a native K2 operand.

This uses the existing [0,1] basis word, not host extraction or a new mux.
Static literals are deliberately excluded from the algorithm experiment.
"""
from copy import deepcopy
from resident_batch_graph import digest

KIND='native-high16-basis-cover-v1'


def candidates(tile):
    from resident_batch_graph import verify
    verify(tile)
    if 'operand_cover' in tile:raise ValueError('nested covers are not supported')
    g=tile['graph'];objects=g['objects'];ops=[n for n in g['operations'] if 'reuse_of' not in n]
    public=set(g['primitive_outputs'].values())|set(g['live_out'].values());result={}
    for n in ops:
        if n['kind']!='M' or (n['width'],n['shift'],n['k'],len(n['terms']))!=(16,0,2,1):continue
        t=n['terms'][0];value=n['output']
        if (objects[t['b']].get('literal')!=65536 or (t['coefficient'],t['scale_shift'])!=(1,0) or
            value in public or 'literal' in objects[t['a']]):continue
        uses=[c for c in ops if value in c['inputs']]
        if not uses:continue
        if all(c['kind']=='M' and all(term['a']==value and objects[term['b']].get('literal')==1 and term.get('k',c['k'])==1
                   for term in c['terms'] if value in (term['a'],term['b'])) for c in uses):
            result[value]={'raw':t['a'],'basis':t['b'],'consumers':[c['id'] for c in uses]}
    return result


def cover(tile,selected=None):
    options=candidates(tile);selected=sorted(options if selected is None else selected)
    if len(set(selected))!=len(selected) or not set(selected)<=options.keys():raise ValueError('invalid high16 cover selection')
    result=deepcopy(tile);graph=result['graph'];removed=set();ops=[]
    for n in graph['operations']:
        if n['output'] in selected:removed.add(n['id']);continue
        if n['kind']=='M':
            changed=False
            for term in n['terms']:
                if term['a'] in selected:
                    rule=options[term['a']];term.update(a=rule['raw'],b=rule['basis'],k=2);changed=True
            if changed:n['inputs']=list(dict.fromkeys(v for t in n['terms'] for v in (t['a'],t['b'])))
        ops.append(n)
    graph['operations']=ops;graph['kind']='native-pointwise-covered-v1';graph.pop('reuse_proof')
    result['groups']=[[name for name in group if name not in removed] for group in result['groups']]
    result['groups']=[group for group in result['groups'] if group]
    result['operand_cover']={'kind':KIND,'source_sha256':digest(tile),'source_tile':deepcopy(tile),'selected':selected}
    verify(result);return result


def verify(tile):
    """Independent source-bound rule checker; never calls cover/candidates."""
    from resident_batch_graph import verify as verify_original
    proof=tile.get('operand_cover',{});source=proof.get('source_tile')
    if proof.get('kind')!=KIND or not isinstance(source,dict) or 'operand_cover' in source:raise ValueError('invalid high16 cover source')
    verify_original(source)
    if proof.get('source_sha256')!=digest(source):raise ValueError('high16 cover source hash differs')
    selected=proof.get('selected');g=source['graph'];obj=g['objects']
    if not isinstance(selected,list) or selected!=sorted(set(selected)):raise ValueError('high16 cover selection differs')
    defs={n['output']:n for n in g['operations'] if 'reuse_of' not in n};rules={}
    for value in selected:
        if value not in defs:raise ValueError('high16 definition missing')
        n=defs[value]
        if (n['kind']!='M' or n['width']!=16 or n['shift']!=0 or n['k']!=2 or len(n['terms'])!=1 or
            value in g['primitive_outputs'].values() or value in g['live_out'].values()):raise ValueError('high16 extraction is observable or inexact')
        term=n['terms'][0];raw=term['a'];basis=term['b']
        if (obj[basis].get('literal')!=1<<16 or term['coefficient']!=1 or term['scale_shift']!=0 or
            'literal' in obj[raw] or term.get('k',2)!=2):raise ValueError('high16 basis/source differs')
        found=False
        for user in defs.values():
            if value not in user['inputs']:continue
            found=True
            if user['kind']!='M':raise ValueError('non-M high16 consumer')
            for t in user['terms']:
                if value not in (t['a'],t['b']):continue
                if t['a']!=value or obj[t['b']].get('literal')!=1 or t.get('k',user['k'])!=1:
                    raise ValueError('high16 consumer cannot use the basis')
        if not found:raise ValueError('unconsumed extraction is not a cover')
        rules[value]=(raw,basis)
    expected=deepcopy(source);expected['operand_cover']=deepcopy(proof);expected['graph']['kind']='native-pointwise-covered-v1'
    expected['graph'].pop('reuse_proof');ops=[];removed=set()
    for n in expected['graph']['operations']:
        if n['output'] in rules:removed.add(n['id']);continue
        if n['kind']=='M':
            changed=False
            for term in n['terms']:
                if term['a'] in rules:
                    term['a'],term['b']=rules[term['a']];term['k']=2;changed=True
            if changed:n['inputs']=list(dict.fromkeys(v for t in n['terms'] for v in (t['a'],t['b'])))
        ops.append(n)
    expected['graph']['operations']=ops
    expected['groups']=[[n for n in group if n not in removed] for group in source['groups']]
    expected['groups']=[group for group in expected['groups'] if group]
    if tile!=expected:raise ValueError('high16 cover changes unrelated fields, terms, order or outputs')
    return {'passed':True,'covered_dynamic_extractions':len(selected),'rows':tile['rows'],
            'scope':'source-bound integer term equivalence; mixed-K RTL and timing qualification required separately'}
