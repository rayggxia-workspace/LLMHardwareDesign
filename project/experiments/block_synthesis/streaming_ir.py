"""Finite-loop lowering and conservative scheduling of a complete typed graph.

This fallback deliberately spills between primitive calls. It is slow, but
does not require whole vectors/weights in S, runtime packing, or new arithmetic
hardware. Macro command templates and bounded memory model remain explicit.
The output is compiler IR, not LC machine code or a cycle-accurate system model.
"""
from collections import Counter
from copy import deepcopy
from itertools import product
import math

from leaf_catalog import duration
from memory import descriptor_ticks


def seq(*body):return {'sequence':list(body)}
def repeat(n,body):
    if not isinstance(n,int) or n<0:raise ValueError('nonfinite native loop')
    return {'repeat':n,'body':body}
def call(name,**args):return {'call':name,**args}


def templates(profile):
    """Every leaf timing is a measured native command, not a FLOP estimate.

    Scalar records use one 128-bit word and a canonical low S32 slot. Static
    S16 weights are sign-extended offline. Three S16 components represent S32:
    low, signed high, low-negative flag, with powers 0,16,16. All component
    preparation precedes the live dot accumulator.
    """
    def leaf(kind,command,reads=0,writes=0,**parameters):
        if kind=='M_LOAD':ticks=1  # native probe asserts this on every load
        else:ticks=duration(profile,kind,**parameters)
        return {'native':kind,'command':command,'parameters':parameters,'ticks':ticks,
                'read_words':reads,'write_words':writes,'macro':kind.split('_')[0]}
    scale=leaf('M_SCALE','Scale(coefficient=signed 1|2,shift=0|16|31)')
    load_a=leaf('M_LOAD','LoadA(wide_a=1,record=src)',1)
    load_b=seq(leaf('M_LOAD','LoadB(wide_b=1,half=0,record=src)',1),
               leaf('M_LOAD','LoadB(wide_b=1,half=1,record=zero)',1))
    execute=leaf('M','Execute(rows=1,tiles=1,columns=1,last_k=1,clear=first)',columns=1,k=1)
    read=leaf('M_READ','ReadFinal(width=32,shift=recipe_shift)',writes=1)
    partial=seq(scale,load_a,load_b,execute)
    e=lambda op,n:leaf('E','E(op='+str(op)+',shift=0)',n,1,op=op,shift=0)
    return {
        'split32':seq(scale,load_a,load_b,
            leaf('M','Execute(rows=1,columns=1,last_k=2,b=[0,1],clear=1)',columns=1,k=2),
            leaf('M_READ','ReadFinal(width=16,shift=0)',writes=1),
            e(5,2),e(6,3)),
        'partial':partial,
        'product':seq(repeat(2,call('split32')),repeat(9,partial),read),
        'sum3':seq(repeat(3,call('split32')),repeat(9,partial),read),
        'convert':seq(call('split32'),repeat(3,partial),read),
        'select_max':seq(repeat(2,call('split32')),repeat(6,partial),
            leaf('M_READ','ReadFinal(width=16,shift=0) signed difference saturation',writes=1),
            e(5,2),repeat(3,e(6,3)),repeat(3,partial),read),
        'select':seq(repeat(2,call('split32')),repeat(3,e(6,3)),repeat(3,partial),read),
        'compare':seq(repeat(2,call('split32')),repeat(6,partial),
            leaf('M_READ','ReadFinal(width=16,shift=0) signed difference saturation',writes=1),
            e(5,2),e(6,3)),
        'compare_le':seq(repeat(2,call('split32')),repeat(6,partial),
            leaf('M_READ','ReadFinal(width=16,shift=0) signed difference saturation',writes=1),
            e(1,2),e(5,2),e(6,3)),
        'dot_final':read,
        'poly_sigmoid':seq(repeat(19,seq(call('product'),call('sum3'))),call('product'),call('sum3')),
        'poly_exp':seq(repeat(31,seq(call('product'),call('sum3'))),call('product'),call('sum3')),
        'n_rms_begin':leaf('N','Begin(mode=RMS,epsilon=encoded)',mode=1,op=0,count=0),
        'n_l2_begin':leaf('N','Begin(mode=L2,epsilon=1)',mode=2,op=0,count=0),
        'n_soft_begin':leaf('N','Begin(mode=Softmax)',mode=0,op=0,count=0),
        'n_soft_finalize':leaf('N','Finalize()',mode=0,op=2,count=0),
        'n_rms_stats':leaf('N','Stats(count=1)',1,mode=1,op=1,count=1),
        'n_l2_stats':leaf('N','Stats(count=1)',1,mode=2,op=1,count=1),
        'n_soft_stats':leaf('N','Stats(count=1)',1,mode=0,op=1,count=1),
        'n_rms_finalize':leaf('N','Finalize()',mode=1,op=2,count=0),
        'n_l2_finalize':leaf('N','Finalize()',mode=2,op=2,count=0),
        'n_rms_factor':leaf('N','ReadFactor()',writes=1,mode=1,op=11,count=0),
        'n_l2_factor':leaf('N','ReadFactor()',writes=1,mode=2,op=11,count=0),
        'n_exp':leaf('N','Exp(count=1)',1,1,mode=0,op=3,count=1),
        'copy':{'transfer':True,'read_words':1,'write_words':1,'macro':'IO'},
    }


def native_operand_components(program):
    widths={name:1 if meta['bits']==16 else 3 for name,meta in program.get('initial_formats',{}).items()}
    result={}
    def fits_s16(raw):
        if isinstance(raw,list):return all(fits_s16(v) for v in raw)
        return isinstance(raw,int) and -32768<=raw<=32767
    for node in program['instructions']:
        result[node['id']]=[widths.get(name,3) for name in node['inputs']]
        widths[node['id']]=1 if node['bits']==16 or (node['op']=='Constant' and fits_s16(node['attributes']['raw'])) else 3
    return result


def primitive_body(node,components=None,preparation=None):
    """Lower the *executed* vector instruction, never a separate op estimate.

    The three-component identity covers every S32 value. Native calls are
    parameterized by this instruction's inputs, exponent/shift and loop index.
    The formal operand order is low16, high16, low-negative flag, with scale
    powers 0,16,16; every split finishes before its dot state is acquired.
    """
    op=node['op'];n=math.prod(node['shape']);attrs=node['attributes']
    c=components or [3]*len(node.get('inputs',[]))
    if op in ('Convert','Product','Dot','Sum','SquareSum'):
        shift=attrs['shift']
        if op in ('Product','Dot'):power=sum(16 if count==3 else 0 for count in c[:2])
        elif op=='SquareSum':power=32
        elif op=='Convert':power=16 if c[0]==3 else 0
        else:power=16
        if shift>63 or power+max(0,-shift)>45:
            raise ValueError('registered M scale/read encoding does not cover primitive shift')
    if op=='NFactor' and (not 0<attrs['epsilon']<1<<32 or not 0<attrs['length']<=65535):
        raise ValueError('native N factor epsilon/count encoding')
    if op in ('Constant','View','Mask'):return repeat(0,call('copy')),0
    if op in ('Gather','Concat'):return repeat(n,call('copy')),64
    if op=='Convert':return repeat(n,seq(repeat(int(c[0]==3),call('split32')),repeat(c[0],call('partial')),call('dot_final'))),64
    if op=='Product':return repeat(n,seq(repeat(sum(count==3 for count in c),call('split32')),
        repeat(c[0]*c[1],call('partial')),call('dot_final'))),64
    if op=='Add':
        length=len(node['inputs'])
        return repeat(n,seq(repeat(length,call('split32')),repeat(3*length,call('partial')),call('dot_final'))),64
    if op=='Dot':
        length=attrs['length']
        if preparation:
            # A(row,k) is invariant in the output-column loop. Its existing
            # split32 commands write the explicit external prepared region
            # before any live output accumulator. B preparation is unchanged.
            return seq(repeat(preparation['rows']*length,call('split32')),
                repeat(n,seq(repeat(int(c[1]==3)*length,call('split32')),
                    repeat(c[0]*c[1]*length,call('partial')),call('dot_final')))),sum(count for count in c if count==3)*length+64
        return repeat(n,seq(repeat(sum(count==3 for count in c)*length,call('split32')),
            repeat(c[0]*c[1]*length,call('partial')),call('dot_final'))),sum(count for count in c if count==3)*length+64
    if op in ('Maximum','Minimum'):return repeat(n,call('select_max')),64
    if op in ('Select','MaskZero','MaskFloor'):return repeat(n,call('select')),64
    if op=='Compare':
        body=call('compare_le') if attrs['le'] else call('compare')
        return repeat(n,body),64
    if op in ('Sum','SquareSum'):
        length=attrs['length'];square=op=='SquareSum'
        return repeat(n,seq(repeat(length*(2 if square else 1),call('split32')),
            repeat(length*(9 if square else 3),call('partial')),call('dot_final'))),6*length+64
    if op=='Max':return repeat(n*max(0,attrs['length']-1),call('select_max')),64
    if op=='NFactor':
        which='n_rms' if attrs['mode']==1 else 'n_l2'
        return repeat(n,seq(call(which+'_begin'),repeat(attrs['length'],call(which+'_stats')),
            call(which+'_finalize'),call(which+'_factor'))),64
    if op=='NExp':return repeat(n,seq(call('n_soft_begin'),call('n_soft_stats'),call('n_soft_finalize'),call('n_exp'))),64
    raise ValueError('no native lowering for emitted primitive '+op)


def counts(body,library,stack=()):
    if 'call' in body:
        name=body['call']
        if name in stack:raise ValueError('recursive native template')
        return counts(library[name],library,stack+(name,))
    if 'repeat' in body:return Counter({k:v*body['repeat'] for k,v in counts(body['body'],library,stack).items()})
    if 'sequence' in body:
        result=Counter()
        for b in body['sequence']:result.update(counts(b,library,stack))
        return result
    result=Counter()
    m=body['macro'];result[m+':read']=body['read_words'];result[m+':write']=body['write_words']
    result[m+':core']=body.get('ticks',0);result[m+':commands']=int('native' in body)
    return result


def enumerate_bindings(stats,h):
    """Use the same native cost/resource contract for kernels or stages."""
    inventory=h['leaf_inventory']
    groups={m:[g for g,v in inventory.items() if m in v['macros']] for m in ('M','E','N')}
    channel_count=h['virtual_memory']['channels']
    macros=[m for m in ('M','E','N') if stats[m+':commands']]
    needs_io=bool(stats['IO:read'] or stats['IO:write'])
    candidates=[]
    # IO-only Gather can use any supplied private S. Arithmetic binding
    # enumerates a small local recipe combination, not whole model maps.
    choices=[groups[m] for m in macros] or [list(inventory)]
    for selected in product(*choices):
        binding=dict(zip(macros,selected));io_group=selected[0]
        sites={inventory[g]['site'] for g in selected};resources=set();nets=set();ticks=0;reads=writes=0
        scratch={site:8 for site in sites}  # named input[0:2], output[3], four staging words
        if any(h['sites'][site]['words']<8 for site in sites):continue
        for macro,g in binding.items():
            instance=g+'.'+macro;meta=inventory[g];site=meta['site']
            resources.update([instance,meta['io_resource'],g+'.LC.service'])
            if instance+'.context' in h['resources']:resources.add(instance+'.context')
            for direction in ('read','write'):nets.add(instance+'.'+direction)
            r,w=stats[macro+':read'],stats[macro+':write'];reads+=r;writes+=w
            # Deliberately one-word descriptors: safe upper-bound model.
            ticks+=stats[macro+':core']+r*meta['io_read_ticks']+w*meta['io_write_ticks']
            ticks+=r*descriptor_ticks(h['virtual_memory'],1,'load',meta['io_write_ticks'])
            ticks+=w*descriptor_ticks(h['virtual_memory'],1,'store',meta['io_read_ticks'])
        if needs_io:
            meta=inventory[io_group];resources.update([meta['io_resource'],io_group+'.LC.service'])
            r,w=stats['IO:read'],stats['IO:write'];reads+=r;writes+=w
            ticks+=r*descriptor_ticks(h['virtual_memory'],1,'load',meta['io_write_ticks'])
            ticks+=w*descriptor_ticks(h['virtual_memory'],1,'store',meta['io_read_ticks'])
        for g in set(selected):
            meta=inventory[g];channel=meta['memory_group']%channel_count
            resources.add('virtual-memory.channel.'+str(channel))
            for direction in ('load','store'):
                net=meta['site']+'.io.'+direction
                h['nets'].setdefault(net,{'cost':1,'fixed':False,'unit':'logical interface bundle',
                    'qualification':'unbound pin demand'})
                nets.add(net)
        bid='/'.join(m+'='+binding[m] for m in macros) or 'IO='+io_group
        candidates.append({'id':bid,'site':inventory[io_group]['site'],'ticks':max(1,ticks),
            'resources':sorted(resources),'nets':sorted(nets),'scratch_words':8,'scratch_by_site':scratch,
            'external_read_words':reads,'external_write_words':writes,'macro_binding':binding})
    return candidates


def compile_graph(model,hardware,trace,profile,primitive_program=None):
    """No model name, Block count or S capacity is hardcoded in this compiler."""
    if not primitive_program:raise ValueError('an executable primitive program is required; op-count estimates are not accepted')
    h=deepcopy(hardware);h['native_leaf_profiles']=deepcopy(profile);library=templates(profile)
    library['dot_final']={'native':'M_READ','command':'ReadFinal(width=32,shift=typed_output_shift)',
        'parameters':{},'ticks':duration(profile,'M_READ'),'read_words':0,'write_words':1,'macro':'M'}
    known={t['id']:t for t in trace};producer={};tasks=[];program=[];external=0;regions={}
    # All persistent objects are external, with scalar record address views.
    # No full tensor allocation is charged to any private S.
    aliases={name for t in model.get('offline_weight_recipes',[]) for name in t['outputs']}
    aliases.update(name for t in model['tasks'] if t['op'] in ('Reshape','Transpose','Slice','Unsqueeze','Squeeze','Expand','Identity') for name in t['outputs'])
    for name,value in model['values'].items():
        if name in aliases:continue
        if value.get('shape') is None:raise ValueError('concrete execution shapes required')
        words=math.prod(value['shape'])
        if words:
            regions[name]={'address_words':external,'words':words,'record_bytes':16}
            external+=words
    inventory=h['leaf_inventory'];groups={macro:[g for g,v in inventory.items() if macro in v['macros']]
        for macro in ('M','E','N')}
    primitive_by_kernel={}
    primitive_regions={}
    helper_constants={}
    if primitive_program:
        operand_components=native_operand_components(primitive_program)
        literals={0,1,65536,-(1<<31)}
        literals.update(int(node['attributes']['threshold']) for node in primitive_program['instructions'] if node['op']=='Compare')
        for value in sorted(literals):
            helper_constants[str(value)]={'address_words':external,'words':1,'record_bytes':16,
                'low32_raw_bits':value&0xffffffff,'purpose':'offline native operand packet; 65536 is S16 basis [0,1]'}
            external+=1
        for name,predicate in primitive_program.get('predicates',{}).items():
            words=math.prod(predicate['shape']);primitive_regions[name]={'address_words':external,'words':words,'record_bytes':16}
            external+=words
        for instruction in primitive_program['instructions']:
            body,temporary=primitive_body(instruction,operand_components[instruction['id']])
            primitive_by_kernel.setdefault(instruction['kernel'],[]).append((instruction,body,temporary))
            # Materialized primitive values live in external memory. Views
            # and masks retain explicit address transformations instead.
            if instruction['op'] not in ('View','Mask'):
                words=math.prod(instruction['shape'])
                primitive_regions[instruction['id']]={'address_words':external,'words':words,'record_bytes':16}
                external+=words
    if not h.get('virtual_memory'):raise ValueError('an explicit memory timing model is required')
    channel_count=h['virtual_memory']['channels']
    for c in range(channel_count):h['resources']['virtual-memory.channel.'+str(c)]=1
    for task in model['tasks']:
        if task['id'] not in known:raise ValueError('missing typed numerical result '+task['id'])
        row=known[task['id']]
        if primitive_program:
            instructions=primitive_by_kernel.get(task['id'],[])
            if not instructions:raise ValueError('emitted program has no kernel '+task['id'])
            body=seq(*[part for _,part,_ in instructions]);temporary=max(t for _,_,t in instructions)
        stats=counts(body,library)
        if not sum(stats.values()):
            # Zero-copy address views preserve dependencies on the producing
            # physical kernel. They are not zero-cost repacking instructions.
            upstream=set().union(*(producer.get(n,set()) for n in task['inputs']))
            for name in task['outputs']:producer[name]=upstream
            program.append({'id':task['id'],'op':task['op'],'address_view':deepcopy(task),'semantic_task':deepcopy(task)})
            continue
        candidates=enumerate_bindings(stats,h)
        if not candidates:raise ValueError('no inventory binding for '+task['op'])
        after=sorted(set().union(*(producer.get(n,set()) for n in task['inputs'])))
        tasks.append({'id':task['id'],'after':after,'bindings':candidates})
        for name in task['outputs']:producer[name]={task['id']}
        program.append({'id':task['id'],'op':task['op'],'shape':row['shape'],'exponent':row['exponent'],
            'semantic_task':deepcopy(task),
            'inputs':task['inputs'],'outputs':task['outputs'],'body':body,'primitive_counts':dict(stats),
            'temporary_external_region':{'address_words':external,'words':temporary},
            'S_layout':{'input_words':[0,1,2],'output_word':3,'staging_words':[4,5,6,7]},
            'lifetime':'LOAD waits for S commit; result STORE waits for external ACK before scratch reuse',
            'accumulator':'split components first; acquire M/context until final read, including memory waits'})
        external+=temporary
    if external*16>1<<h['virtual_memory']['address_bits']:raise ValueError('external address space overflow')
    capacity=h.get('external_capacity_words')
    if capacity is not None and external>capacity:raise ValueError('declared external capacity exceeded')
    return {'model':model,'tasks':tasks,'hardware':h,'native_templates':library,'program':program,
        'primitive_program':primitive_program,'primitive_regions':primitive_regions,
        'native_constants':helper_constants,
        'native_operand_components':operand_components,
        'native_call_abi':{
            'record':'128-bit scalar record with canonical low S32; initial S16 values sign-extended offline',
            'components':'S32: [low16,signed high16,low_negative_flag] at powers [0,16,16]; proven S16/literal operands use only low16',
            'operand_addresses':'stream_addresses.Addresses element/dot/gather and last-axis reduce indices, composed through views',
            'commands':'Scale; LoadA; LoadB half0; LoadB half1; Execute; ReadFinal; E Min/Select; N Begin/Stats/Finalize/ReadFactor or Exp',
            'state':'prepare all components in external scratch before M accumulator; keep context until final read ACK',
            'local_slots':'read up to three input words into S[0:3]; output S[3]; staging S[4:8]; wait every STORE ACK',
            'control':'coefficient signs/scale/read shift from each typed primitive; negative compare uses saturated S16 difference'},
        'external_regions':regions,'required_external_bytes':external*16,'capacity_qualified':capacity is not None,
        'timing_scope':'conservative serial native-command plus per-word PR182 virtual memory bound; not system cycles',
        'program_scope':'executable integer vector-loop IR and its native command templates; not LC binary',
        'indexed_address_timing_qualified':False,
        'optimization_scope':'all values spilled; scalar records; no inter-kernel S cache or tiled reuse yet'}
