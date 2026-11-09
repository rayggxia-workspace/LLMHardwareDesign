"""Rebuild source/whole-loop work and audit each registered resident service.

No planner, registrar, or declared binding ticks is used to establish native
work/copy costs. Numeric fixtures are independent original scalar execution
and finite-S command replay; actual model/full loop replay is still separate.
"""
from collections import Counter
import hashlib
import json
import math

from native_pointwise import bind_external,counts,execute,lower
from resident_replay import replay
from resident_survey import build_actors,reference
from resident_timing import audit
from streaming_ir import counts as primitive_counts,primitive_body


def _digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def verify(ir,*,numeric=True):
    p=ir['primitive_program'];nodes={n['id']:n for n in p['instructions']}
    timing=ir['resident_timing'];actors=build_actors(ir,timing);h=ir['hardware']
    source=_digest(p);recipes=ir['resident_recipes'];declared=h['tile_service_bindings']
    checked=cases=0
    for key,r in recipes.items():
        if _digest(r)!=key or r['source_program_sha256']!=source:raise ValueError('resident recipe/source digest differs')
        names=r['primitives'];shape=nodes[names[0]]['shape'];count=math.prod(shape)
        graph=bind_external(lower(p,names,0),ir)
        if graph!=r['graph']:raise ValueError('resident recipe native graph differs from source')
        if r['plan']['actors']!=actors or r['plan']['zero_address']!=ir['native_constants']['0']['address_words']:
            raise ValueError('resident allocator/zero source differs')
        loop=r['loop'];sources=set().union(*(set(nodes[n]['inputs']) for n in names))-set(names)
        formats={**p.get('initial_formats',{}),**nodes};alloc={**ir['external_regions'],**ir['primitive_regions']}
        expected={}
        for name in sources:
            s=formats[name]['shape']
            if math.prod(s)==1:mode='scalar';extent=1
            elif s==shape:mode='element';extent=count
            else:raise ValueError('resident whole-loop shape proof failed')
            if extent>1 and (formats[name].get('op')=='Constant' or 'literal' in formats[name]):
                raise ValueError('resident whole-loop indexed literal proof missing')
            if formats[name].get('op')=='View' or name not in alloc or alloc[name]['words']<extent:
                raise ValueError('resident whole-loop direct source proof failed')
            expected[name]=mode
        if (loop.get('kind')!='direct-scalar-or-element-loop-v1' or loop['sources']!=expected or
            loop['elements']!=count or loop['shape']!=shape or
            loop['iteration_order']!='ascending, serial; cold records/banks; all live-outs STORE-ACKed'):
            raise ValueError('resident whole-loop contract differs')
        intervals=[(alloc[n]['address_words'],alloc[n]['address_words']+(1 if m=='scalar' else count))
                   for n,m in expected.items()]
        if any(max(a,c)<min(b,d) for i,(a,b) in enumerate(intervals) for c,d in intervals[i+1:]):
            raise ValueError('resident whole-loop input allocations alias')
        work=Counter()
        for name in names:
            body,_=primitive_body(nodes[name],ir['native_operand_components'][name])
            for field,value in primitive_counts(body,ir['native_templates']).items():
                if field.endswith((':read',':write',':commands')) and value:
                    if value%count:raise ValueError('nonuniform resident native work')
                    work[field]+=value//count
        if counts(graph)!=dict(work):raise ValueError('resident native work changed')
        audit(r['plan'],timing)
        if numeric:
            for trial,value in enumerate((0,1,-1,32767,-32768,1048575,-1048576)):
                values={}
                for o in graph['objects'].values():
                    if o['kind']=='external' and 'literal' not in o:
                        v=value if o['bits']==32 else max(-32768,min(32767,value))
                        values[(o['tensor'],o['index'])]=v
                gold=execute(graph,values);original=reference(p,graph,values)
                for name,record in graph['primitive_outputs'].items():
                    word=gold[record]&0xffffffff;signed=word-(1<<32) if word&(1<<31) else word
                    if signed!=original[name]:raise ValueError('resident native/original scalar numeric differs')
                result=replay(graph,r['plan'],values)
                if result['observed_native_outputs']!={n['output']:gold[n['output']] for n in graph['operations']}:
                    raise ValueError('resident finite SRAM numeric differs')
                cases+=1
    for action in ir['resident_actions']:
        for b in action['bindings']:
            spec=b['resident_region'];r=recipes[spec['recipe']];plan=r['plan'];count=r['loop']['elements']
            if action['covers']!=r['primitives'] or spec['elements']!=count:
                raise ValueError('resident cover/iteration extent differs')
            mapping=spec['actor_map'];resources=set();nets=set();scratch={}
            if set(mapping)!=set(actors) or len(set(mapping.values()))!=len(mapping):
                raise ValueError('resident instance map differs')
            for old,new in mapping.items():
                a=actors[old];kind=a['kind'];role='P' if kind=='M' else 'E'
                if new not in declared[role]:raise ValueError('unqualified resident service instance')
                m=h['leaf_inventory'][new];original=h['leaf_inventory'][old]
                if (m['words']!=a['words'] or m['io_read_ticks']!=original['io_read_ticks'] or
                    m['io_write_ticks']!=original['io_write_ticks']):raise ValueError('resident rebound allocator differs')
                resources.update((new+'.'+kind,new+'.LC.service',m['io_resource'],
                    'virtual-memory.channel.'+str(m['memory_group']%h['virtual_memory']['channels'])))
                if kind=='M':resources.add(new+'.M.context')
                site=m['site'];scratch[site]=a['words']
                nets.update((new+'.'+kind+'.read',new+'.'+kind+'.write',site+'.io.load',site+'.io.store'))
                if b['macro_binding'].get(kind)!=new:raise ValueError('resident macro binding differs')
            if (b['ticks']!=count*plan['total_ticks'] or b['external_read_words']!=count*plan['external_load_words'] or
                b['external_write_words']!=count*plan['external_store_words'] or b['scratch_by_site']!=scratch or
                set(b['resources'])!=resources or set(b['nets'])!=nets or
                spec['invalidate_read_cache']!=sorted(scratch) or b.get('read_cache') or b.get('dot_tile')):
                raise ValueError('resident binding work/resources/cache effects differ')
            checked+=1
    return {'passed':True,'recipes':len(recipes),'bindings':checked,'synthetic_numeric_cases':cases,
        'scope':'independent source/native-work, uniform loop restriction, event cost, service rebinding and finite-S fixtures; not actual-weight full-loop or system qualification'}
