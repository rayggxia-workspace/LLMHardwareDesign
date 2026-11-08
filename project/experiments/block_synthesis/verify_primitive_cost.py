"""Independent link between executed primitive IR and scheduled native work.

Does not import the compiler, DP, counts() or primitive_body(). Unknown
primitives fail. Constants/views are offline metadata, never CPU fallback.
"""
from collections import Counter,defaultdict
import json
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
    expected=defaultdict(Counter);dots_by_kernel=defaultdict(list)
    staged='primitive_stages' in ir; stage_map=ir.get('primitive_stages',{})
    expected_stages={}; expected_after={}; producers={}; expected_rows={}
    node_ids={n['id'] for n in program['instructions']}
    if len(node_ids)!=len(program['instructions']):raise ValueError('duplicate primitive identity')
    def upstream(names):
        if any(n in node_ids and n not in producers for n in names):
            raise ValueError('primitive source is not defined before use')
        return set().union(*(producers.get(n,set()) for n in names))
    preparations=ir.get('operand_preparations',{});seen_preparations=set()
    widths={name:1 if meta['bits']==16 else 3 for name,meta in program.get('initial_formats',{}).items()}
    def narrow_literal(x):
        return all(narrow_literal(v) for v in x) if isinstance(x,list) else isinstance(x,int) and -32768<=x<=32767
    for node in program['instructions']:
        op=node['op'];n=math.prod(node['shape']);a=node['attributes'];work=Counter()
        if op=='Dot':dots_by_kernel[node['id'] if staged else node['kernel']].append(node)
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
        total=Counter({k:n*v for k,v in work.items()})
        if node['id'] in preparations:
            p=preparations[node['id']];seen_preparations.add(node['id'])
            if op!='Dot' or c[0]!=3 or len(node['shape'])<2:
                raise ValueError('inapplicable operand preparation')
            columns=node['shape'][-1];rows=n//columns;k=a['length']
            if (columns<=1 or p.get('kind')!='dot-A-prepare-once-v1' or
                p.get('primitive')!=node['id'] or p.get('input')!=node['inputs'][0] or
                (p.get('rows'),p.get('columns'),p.get('K'),p.get('components'))!=(rows,columns,k,3) or
                p.get('layout')!='row-k-component' or
                p.get('old_split_calls')!=n*k or p.get('new_split_calls')!=rows*k or
                type(p.get('external_base'))!=int or p['external_base']<0 or
                p.get('external_words')!=3*rows*k):
                raise ValueError('prepared operand identity/extent differs')
            removed=(n-rows)*k
            for key,value in split.items():total[key]-=removed*value
        if staged:
            parents=upstream(node['inputs'])
            if any(total.values()):
                phases={'execute':node['id']}
                scratch=64
                if op=='Dot':scratch+=sum(x for x in c if x==3)*a['length']
                elif op in ('Sum','SquareSum'):scratch+=6*a['length']
                if node['id'] in preparations:
                    prep_id=node['id']+'#prepare-A'
                    if prep_id in node_ids:raise ValueError('prepared stage identity collision')
                    phases['prepare']=prep_id
                    prep=combine((preparations[node['id']]['rows']*a['length'],split))
                    expected[prep_id].update(prep)
                    expected_after[prep_id]=upstream(node['inputs'][:1])
                    expected_rows[prep_id]=(node,'prepare-A',64)
                    for key,value in prep.items():total[key]-=value
                    parents=upstream(node['inputs'][1:])|{prep_id}
                expected_stages[node['id']]=phases
                expected[node['id']].update(total)
                expected_after[node['id']]=parents
                expected_rows[node['id']]=(node,'execute',scratch)
                producers[node['id']]={node['id']}
            else:producers[node['id']]=parents
        else:expected[node['kernel']].update(total)
    if seen_preparations!=set(preparations):raise ValueError('unknown prepared primitive')
    if staged:
        if stage_map!=expected_stages:raise ValueError('primitive stage coverage/identity differs')
        if len(ir['program'])!=len(expected_rows) or {r['id'] for r in ir['program']}!=set(expected_rows):
            raise ValueError('primitive stage program coverage differs')
        for task in ir['tasks']:
            if set(task.get('after',[]))!=expected_after.get(task['id']):
                raise ValueError('primitive stage dependencies differ '+task['id'])
        for row in ir['program']:
            node,phase,scratch=expected_rows[row['id']]
            if (row.get('source_primitive'),row.get('source_kernel'),row.get('phase'),row.get('shape'),
                row.get('inputs'),row.get('exponent'),row['temporary_external_region']['words'])!=(
                node['id'],node['kernel'],phase,node['shape'],node['inputs'],node['exponent'],scratch):
                raise ValueError('primitive stage source/scratch differs')
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
            c=b.get('read_cache')
            scratch={hardware['leaf_inventory'][g]['site']:8 for g in groups}
            if c:
                dots=dots_by_kernel[name]
                if len(dots)!=1:raise ValueError('cache kernel must contain exactly one Dot')
                node=dots[0];ca,cb=ir['native_operand_components'][node['id']]
                columns=node['shape'][-1];rows=math.prod(node['shape'])//columns;k=node['attributes']['length']
                group=b['macro_binding']['M'];meta=hardware['leaf_inventory'][group];site=meta['site']
                t=c['stripe'];tag=json.dumps([node['inputs'][0],node['shape'][:-1],k,ca],separators=(',',':'))
                if (type(t)!=int or not 0<=t<=k or c['tag']!=tag or c['site']!=site or
                    c['primitive']!=node['id'] or c['components']!=[ca,cb] or
                    (c['rows'],c['columns'],c['K'])!=(rows,columns,k) or
                    c['cache_words']!=rows*t*ca or hardware['resources'][meta['io_resource']]!=1):
                    raise ValueError('cache address identity/capacity/serialized port differs')
                if c['layout']!={'scratch':[0,8],'zero':8,'A_start':9,'B_staging':[4,4+cb]}:
                    raise ValueError('cache S address allocation differs')
                old=rows*columns*k*ca*cb*3
                new=rows*t*ca+rows*columns*(k-t)*ca*cb+rows*columns*k*cb+1
                if (c['baseline_partial_external_reads'],c['cold_partial_external_reads'],c['warm_partial_external_reads'])!=(old,new,new-rows*t*ca):
                    raise ValueError('cache transfer proof differs')
                saved=old-new;ext=descriptor_ticks(hardware['virtual_memory'],1,'load',meta['io_write_ticks'])
                ticks-=saved*ext;reads-=saved
                if b['warm_ticks']!=ticks-rows*t*ca*ext or b['warm_read_words']!=reads-rows*t*ca:
                    raise ValueError('warm cache transfer/timing differs')
                if c.get('cost_model')=='dot-prefix-state-v2' and c.get('load_ticks')!=ext:
                    raise ValueError('state LOAD unit cost differs')
                scratch[site]=9+rows*t*ca
            if b.get('scratch_by_site')!=scratch or any(n>hardware['sites'][s]['words'] for s,n in scratch.items()):
                raise ValueError('cache/scratch S extent differs')
            if (max(1,ticks),reads,writes)!=(b['ticks'],b['external_read_words'],b['external_write_words']):
                raise ValueError('native/virtual-memory cost differs '+name)
            for group in groups:resources.add('virtual-memory.channel.'+str(hardware['leaf_inventory'][group]['memory_group']%hardware['virtual_memory']['channels']))
            if resources!=set(b['resources']):raise ValueError('native resource omission')
            checked+=1
    regions=list(ir['external_regions'].values())+list(ir['primitive_regions'].values())+list(ir['native_constants'].values())
    regions += [row['temporary_external_region'] for row in ir['program'] if 'temporary_external_region' in row]
    regions += ir.get('native_scratch_regions',[])
    regions += [{'address_words':p['external_base'],'words':p['external_words']} for p in preparations.values()]
    end=0
    for r in sorted(regions,key=lambda r:r['address_words']):
        if r['address_words']<end:raise ValueError('overlapping external object regions')
        end=r['address_words']+r['words']
    if end*16!=ir['required_external_bytes']:raise ValueError('external object extent differs')
    if end*16>1<<hardware['virtual_memory']['address_bits']:raise ValueError('external address width exceeded')
    if hardware.get('external_capacity_words') is not None and end>hardware['external_capacity_words']:
        raise ValueError('external capacity exceeded')
    return {'passed':True,'kernels':len(ir['tasks']),'bindings':checked,'primitive_instructions':len(program['instructions']),
        'scope':'executed primitive coverage, native profiles, memory traffic/timing and external regions; LC/physical timing excluded'}
