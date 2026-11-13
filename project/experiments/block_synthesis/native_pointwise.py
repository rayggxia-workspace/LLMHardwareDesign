"""SSA records for existing exact pointwise M/E recipes, before allocation.

This is an addressed-dataflow preparation for finite-S residency. It does not
assign a free local copy, remove a transfer, alter the scheduler or claim a
qualified complete backend. M commands own one accumulator through final read.
Every record is a whole 128-bit word; views consume low S16 without packing.
"""
from collections import Counter
import json
import math

from layout_views import broadcast_index,coordinates
from streaming_ir import native_operand_components


SUPPORTED=frozenset(('Convert','Product','Add'))


def regions(program):
    """Contiguous same-shape runs are convex; do not fuse across reductions.

    Inputs through tensor views are explicit region boundaries for now. A
    constant is an offline record, not a compute barrier or a free runtime op.
    """
    result=[];current=[];shape=None
    for n in program['instructions']:
        if n['op']=='Constant':continue
        if n['op'] not in SUPPORTED or (current and n['shape']!=shape):
            if current:result.append(current);current=[]
        if n['op'] in SUPPORTED:
            shape=n['shape'];current.append(n['id'])
    if current:result.append(current)
    return result


def _scale(power,sign=1):
    if type(power)!=int or not 0<=power<=45 or sign not in (-1,1):
        raise ValueError('native M scale encoding exceeded')
    return sign*(1<<max(0,power-31)),min(31,power)


def lower(program,names,index=0):
    """Lower one actual element of a convex region, preserving native work.

    Repeated split32 calls deliberately keep distinct output identities. Any
    future CSE/preparation hoist is a separate, openly compared optimization.
    Offsets are resolved tensor indices, not unbounded private SRAM buffers.
    """
    nodes={n['id']:n for n in program['instructions']}
    if not names or len(names)!=len(set(names)) or any(n not in nodes for n in names):
        raise ValueError('invalid pointwise region identities')
    positions={n['id']:i for i,n in enumerate(program['instructions'])}
    if names!=sorted(names,key=positions.get):raise ValueError('region is not in program order')
    shape=nodes[names[0]]['shape']
    if any(nodes[n]['op'] not in SUPPORTED or nodes[n]['shape']!=shape for n in names):
        raise ValueError('pointwise region needs one shape and registered operators')
    between=program['instructions'][positions[names[0]]:positions[names[-1]]+1]
    if any(n['id'] not in names and n['op']!='Constant' for n in between):
        raise ValueError('region crosses an unrepresented operation')
    if type(index)!=int or not 0<=index<math.prod(shape):raise ValueError('pointwise element outside shape')
    formats={**program.get('initial_formats',{}),**{n['id']:n for n in program['instructions']}}
    components=native_operand_components(program)
    objects={};ops=[];outputs={};serial=0;owner=None
    def record(name,element):
        key=json.dumps([name,element],separators=(',',':'))
        if key not in objects:
            meta=formats[name]
            if meta.get('bits') not in (16,32):raise ValueError('unregistered source record width')
            entry={'kind':'external','tensor':name,'index':element,'bits':meta['bits'],
                   'abi':'canonical low S32 in one 128-bit record'}
            if meta.get('op')=='Constant' or 'literal' in meta:
                raw=meta['attributes']['raw'] if meta.get('op')=='Constant' else meta['literal']
                for at in coordinates(element,meta['shape']):raw=raw[at]
                if type(raw)!=int:raise ValueError('non-integer literal record')
                entry['literal']=raw
            objects[key]=entry
        return key
    def constant(value):
        key='constant:'+str(value)
        objects.setdefault(key,{'kind':'constant','literal':value,'bits':32,'abi':'canonical low S32 record'})
        return key
    def emit(kind,inputs,**attrs):
        nonlocal serial
        key='native:'+str(serial);serial+=1
        objects[key]={'kind':'produced','producer':key,'primitive':owner,'abi':attrs.pop('abi','canonical low S32 record')}
        ops.append({'id':key,'kind':kind,'inputs':list(inputs),'output':key,'primitive':owner,**attrs})
        return key
    def matrix(terms,*,width=32,shift=0,k=1):
        if width not in (16,32) or not 0<=shift<=63:raise ValueError('native final read encoding exceeded')
        return emit('M',list(dict.fromkeys(x for t in terms for x in (t['a'],t['b']))),
                    terms=terms,width=width,shift=shift,k=k,
                    context='one M S64 context; prepare all operands first; final SRAM write ACK')
    def term(a,b,power=0,sign=1):
        coeff,shift=_scale(power,sign)
        return {'a':a,'b':b,'coefficient':coeff,'scale_shift':shift}
    def split(raw):
        # M extracts high16 with K2 basis [0,1]. E Min/Select computes the
        # low-negative flag. low16 is an alias of the unchanged source word.
        high=matrix([term(raw,constant(65536))],width=16,k=2)
        neg=emit('E',[raw,constant(0)],opcode=5,shift=0,
                 abi='eight native S16 lanes; low lane is min(signed_low16,0)')
        flag=emit('E',[constant(1),constant(0),neg],opcode=6,shift=0,
                  abi='eight native S16 lanes; low lane is signed_low16<0')
        return (raw,high,flag)
    for name in names:
        owner=name;node=nodes[name];args=[]
        for source in node['inputs']:
            if source not in formats:raise ValueError('missing source record format')
            if source in positions and positions[source]>=positions[name]:raise ValueError('source not defined before use')
            i=broadcast_index(index,shape,formats[source]['shape'])
            args.append(outputs[source] if source in outputs else record(source,i))
        attrs=node['attributes'];op=node['op'];parts=[]
        if attrs.get('predicate_source') is not None:raise ValueError('masked arithmetic needs an explicit predicate record contract')
        for i,raw in enumerate(args):
            # Match the existing conservative Add: split every input, even
            # proven S16. Product/Convert follow the existing component proof.
            parts.append(split(raw) if op=='Add' or components[name][i]==3 else (raw,))
        terms=[];shift=attrs.get('shift',0)
        if type(shift)!=int:raise ValueError('integer pointwise shift required')
        if op=='Add':
            if len(attrs['signs'])!=len(parts):raise ValueError('Add sign arity differs')
            for pp,sign in zip(parts,attrs['signs']):
                terms.extend(term(x,constant(1),16*int(i!=0),sign) for i,x in enumerate(pp))
        elif op=='Convert':
            if len(parts)!=1:raise ValueError('Convert arity differs')
            terms=[term(x,constant(1),16*int(i!=0)+max(0,-shift)) for i,x in enumerate(parts[0])]
        else:
            if len(parts)!=2:raise ValueError('Product arity differs')
            terms=[term(a,b,16*(int(i!=0)+int(j!=0))+max(0,-shift))
                   for i,a in enumerate(parts[0]) for j,b in enumerate(parts[1])]
        outputs[name]=matrix(terms,width=node['bits'],shift=max(0,shift))
    users={name:set() for name in names}
    for node in program['instructions']:
        for name in node['inputs']:
            if name in users:users[name].add(node['id'])
    final=set(program.get('outputs',{}).values())
    live_out={name:outputs[name] for name in names if name in final or users[name]-set(names)}
    return {'kind':'native-pointwise-ssa-v1','shape':shape,'index':index,'primitives':names,
            'objects':objects,'operations':ops,'primitive_outputs':outputs,'live_out':live_out,
            'scope':'unallocated native SSA, exact original split/partial work; no residency, transfer removal or time qualification'}


def bind_external(graph,ir):
    """Resolve whole-record identities to already reserved external regions.

    Internal preparation records reuse the owning primitive's explicit finite
    temporary region. Different fused elements must not run concurrently on
    these same regions. No new unbounded external array is silently allocated.
    """
    from copy import deepcopy
    from stream_addresses import Addresses
    result=deepcopy(graph);p=ir['primitive_program']
    values={k:dict(v) for k,v in ir['model']['values'].items()}
    values.update({k:dict(v) for k,v in p.get('initial_formats',{}).items()})
    views=[]
    for n in p['instructions']:
        values[n['id']]={'shape':n['shape']}
        if n['op']=='Constant':values[n['id']]['constant']=n['attributes']['raw']
        if n['op']=='View':views.append({'op':n['attributes']['view_op'],'inputs':n['inputs'],
            'outputs':[n['id']],'attributes':n['attributes']['source_attributes']})
    address=Addresses({'values':values,'tasks':views,
        'offline_weight_recipes':ir['model'].get('offline_weight_recipes',[])},
        {**ir['external_regions'],**ir['primitive_regions']})
    rows={r['id']:r for r in ir['program']};final={v:k for k,v in graph['primitive_outputs'].items()}
    slots=Counter();used={}
    for name,obj in result['objects'].items():
        if obj['kind']=='constant':
            region=ir['native_constants'].get(str(obj['literal']))
            if region is None:raise ValueError('native constant has no reserved external record')
            at=region['address_words']
        elif obj['kind']=='external':at=address.locate(obj['tensor'],obj['index'])
        elif name in final:at=address.locate(final[name],graph['index'])
        else:
            owner=obj['primitive'];row=rows.get(owner)
            if row is None:raise ValueError('native pointwise needs separately reserved primitive scratch')
            region=row['temporary_external_region'];offset=slots[owner];slots[owner]+=1
            if offset>=region['words']:raise ValueError('finite external preparation scratch exceeded')
            at=region['address_words']+offset
        if type(at)!=int or at<0 or 16*(at+1)>ir['required_external_bytes']:
            raise ValueError('native pointwise external address outside reserved extent')
        if at in used and used[at]!=name:raise ValueError('native pointwise external records alias')
        used[at]=name;obj['external_address']=at
    result['external_scratch_words']=dict(slots)
    result['external_scope']='existing primitive/input/constants and finite per-primitive scratch; fused elements serialize scratch reuse'
    return result


def counts(graph):
    result=Counter()
    for n in graph['operations']:
        if n['kind']=='M':
            result['M:commands']+=5*len(n['terms'])+1
            result['M:read']+=3*len(n['terms']);result['M:write']+=1
        elif n['kind']=='E':
            result['E:commands']+=1;result['E:read']+=len(n['inputs']);result['E:write']+=1
        else:raise ValueError('unregistered native pointwise service')
    return dict(result)


def execute(graph,external):
    """Independent native M/E word semantics, before SRAM placement.

    No split32 or complete Product/Add shortcut is called here. It interprets
    all generated native terms and E lane commands and returns actual words.
    This is a numerical interpreter, not a SystemC/time/energy qualification.
    """
    records={}
    def s16(word,lane=0):
        x=(word>>(16*lane))&65535
        return x-65536 if x&32768 else x
    def rounded(value,shift):
        if not shift:return value
        sign=-1 if value<0 else 1;q,r=divmod(abs(value),1<<shift)
        return sign*(q+int(2*r>1<<shift or (2*r==1<<shift and q%2)))
    for name,obj in graph['objects'].items():
        if obj['kind']=='produced':continue
        value=obj['literal'] if 'literal' in obj else external[(obj['tensor'],obj['index'])]
        if type(value)!=int or not -(1<<31)<=value<(1<<31):raise ValueError('external S32 record out of range')
        records[name]=value&0xffffffff
    for n in graph['operations']:
        if n['kind']=='M':
            acc=0
            for t in n['terms']:
                a,b=records[t['a']],records[t['b']]
                partial=sum(s16(a,i)*s16(b,i) for i in range(t.get('k',n['k'])))
                acc+=partial*t['coefficient']*(1<<t['scale_shift'])
                if not -(1<<63)<=acc<(1<<63):raise ValueError('native pointwise S64 partial overflow')
            value=rounded(acc,n['shift']);bits=n['width']
            value=max(-(1<<(bits-1)),min((1<<(bits-1))-1,value))
            records[n['output']]=value&0xffffffff
        elif n['kind']=='E':
            args=[records[x] for x in n['inputs']];word=0
            for i in range(8):
                a=[s16(x,i) for x in args]
                if n['opcode']==5:value=min(a)
                elif n['opcode']==6:value=a[0] if a[2] else a[1]
                else:raise ValueError('native E opcode not qualified by this interpreter')
                word|=(value&65535)<<(16*i)
            records[n['output']]=word
        else:raise ValueError('unregistered native pointwise command')
    return records
