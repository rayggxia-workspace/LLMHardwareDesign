"""Independent link between executed primitive IR and scheduled native work.

Does not import the compiler, DP, counts() or primitive_body(). Unknown
primitives fail. Constants/views are offline metadata, never CPU fallback.
"""
from collections import Counter,defaultdict
import math
from leaf_catalog import duration
from memory import descriptor_ticks


def verify(ir):
    program=ir.get('primitive_program')
    if not program:raise ValueError('executable primitive program required')
    library=ir['native_templates'];profile=ir['hardware']['native_leaf_profiles']
    def walk(body,stack=()):
        if 'call' in body:
            key=body['call']
            if key in stack:raise ValueError('recursive native program')
            return walk(library[key],stack+(key,))
        if 'repeat' in body:
            if not isinstance(body['repeat'],int) or body['repeat']<0:raise ValueError('unbounded native loop')
            return Counter({k:v*body['repeat'] for k,v in walk(body['body'],stack).items()})
        if 'sequence' in body:
            result=Counter()
            for part in body['sequence']:result.update(walk(part,stack))
            return result
        macro=body['macro'];result=Counter({macro+':read':body['read_words'],macro+':write':body['write_words'],
            macro+':commands':int('native' in body),macro+':core':body.get('ticks',0)})
        if 'native' in body:
            expected=1 if body['native']=='M_LOAD' else duration(profile,body['native'],**body['parameters'])
            if expected!=body['ticks']:raise ValueError('native leaf timing differs from qualification')
        return result
    primitive={name:walk({'call':name}) for name in library}
    read=primitive['dot_final'];split=primitive['split32'];partial=primitive['partial']
    def combine(*terms):
        result=Counter()
        for count,term in terms:result.update({k:count*v for k,v in term.items()})
        return result
    expected=defaultdict(Counter)
    widths={name:1 if meta['bits']==16 else 3 for name,meta in program.get('initial_formats',{}).items()}
    def narrow_literal(x):
        return all(narrow_literal(v) for v in x) if isinstance(x,list) else isinstance(x,int) and -32768<=x<=32767
    for node in program['instructions']:
        op=node['op'];n=math.prod(node['shape']);a=node['attributes'];work=Counter()
        c=[widths.get(name,3) for name in node['inputs']]
        if c!=ir['native_operand_components'][node['id']]:raise ValueError('native component specialization differs')
        widths[node['id']]=1 if node['bits']==16 or (op=='Constant' and narrow_literal(a['raw'])) else 3
        if op in ('Constant','View','Mask'):pass
        elif op in ('Gather','Concat'):work=primitive['copy']
        elif op=='Convert':work=combine((int(c[0]==3),split),(c[0],partial),(1,read))
        elif op=='Product':work=combine((sum(count==3 for count in c),split),(c[0]*c[1],partial),(1,read))
        elif op=='Add':
            terms=len(node['inputs']);work=combine((terms,split),(terms*3,partial),(1,read))
        elif op=='Dot':work=combine((sum(count==3 for count in c)*a['length'],split),
            (c[0]*c[1]*a['length'],partial),(1,read))
        elif op in ('Maximum','Minimum'):work=primitive['select_max']
        elif op in ('Select','MaskZero','MaskFloor'):work=primitive['select']
        elif op=='Compare':work=primitive['compare_le' if a['le'] else 'compare']
        elif op in ('Sum','SquareSum'):
            length=a['length'];square=op=='SquareSum'
            work=combine((length*(2 if square else 1),split),(length*(9 if square else 3),partial),(1,read))
        elif op=='Max':work=combine((max(0,a['length']-1),primitive['select_max']))
        elif op=='NFactor':
            which='n_rms' if a['mode']==1 else 'n_l2'
            work=combine((1,primitive[which+'_begin']),(a['length'],primitive[which+'_stats']),
                (1,primitive[which+'_finalize']),(1,primitive[which+'_factor']))
        elif op=='NExp':work=combine(*[(1,primitive[k]) for k in ('n_soft_begin','n_soft_stats','n_soft_finalize','n_exp')])
        else:raise ValueError('unregistered executed primitive '+op)
        expected[node['kernel']].update({k:n*v for k,v in work.items()})
    hardware=ir['hardware'];checked=0
    if {name for name,work in expected.items() if any(work.values())}!={t['id'] for t in ir['tasks']}:
        raise ValueError('native kernel coverage differs from executed program')
    for task in ir['tasks']:
        name=task['id'];kernel=next(row for row in ir['program'] if row['id']==name)
        work=walk(kernel['body'])
        if work!=expected[name] or Counter(kernel['primitive_counts'])!=work:raise ValueError('executed/scheduled primitive work differs '+name)
        for b in task['bindings']:
            required={m for m in ('M','E','N') if work[m+':commands']}
            if set(b['macro_binding'])!=required:raise ValueError('missing native macro binding')
            ticks=0;reads=writes=0
            resources=set();groups=set(b['macro_binding'].values())
            for macro,group in b['macro_binding'].items():
                meta=hardware['leaf_inventory'][group];r,w=work[macro+':read'],work[macro+':write']
                instance=group+'.'+macro;resources.update([instance,meta['io_resource'],group+'.LC.service'])
                if instance+'.context' in hardware['resources']:resources.add(instance+'.context')
                ticks+=work[macro+':core']+r*meta['io_read_ticks']+w*meta['io_write_ticks']
                ticks+=r*descriptor_ticks(hardware['virtual_memory'],1,'load',meta['io_write_ticks'])
                ticks+=w*descriptor_ticks(hardware['virtual_memory'],1,'store',meta['io_read_ticks']);reads+=r;writes+=w
            if work['IO:read'] or work['IO:write']:
                meta=hardware['sites'][b['site']];r,w=work['IO:read'],work['IO:write']
                group=next(g for g,v in hardware['leaf_inventory'].items() if v['site']==b['site'])
                groups.add(group);resources.update([meta['io_resource'],group+'.LC.service'])
                ticks+=r*descriptor_ticks(hardware['virtual_memory'],1,'load',meta['io_write_ticks'])
                ticks+=w*descriptor_ticks(hardware['virtual_memory'],1,'store',meta['io_read_ticks']);reads+=r;writes+=w
            if (max(1,ticks),reads,writes)!=(b['ticks'],b['external_read_words'],b['external_write_words']):
                raise ValueError('native/virtual-memory cost differs '+name)
            for group in groups:resources.add('virtual-memory.channel.'+str(hardware['leaf_inventory'][group]['memory_group']%hardware['virtual_memory']['channels']))
            if resources!=set(b['resources']):raise ValueError('native resource omission')
            checked+=1
    regions=list(ir['external_regions'].values())+list(ir['primitive_regions'].values())+list(ir['native_constants'].values())
    regions += [row['temporary_external_region'] for row in ir['program'] if 'temporary_external_region' in row]
    end=0
    for r in sorted(regions,key=lambda r:r['address_words']):
        if r['address_words']<end:raise ValueError('overlapping external object regions')
        end=r['address_words']+r['words']
    if end*16!=ir['required_external_bytes']:raise ValueError('external object extent differs')
    return {'passed':True,'kernels':len(ir['tasks']),'bindings':checked,'primitive_instructions':len(program['instructions']),
        'scope':'executed primitive coverage, native profiles, memory traffic/timing and external regions; LC/physical timing excluded'}
