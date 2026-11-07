"""Typed operator recipes for actual G/E/M/R/T commands.

Layouts are part of the semantics. Unsupported runtime packing is rejected,
not performed by an invisible host. Initial checkpoint tile packing is an
explicit offline recipe. Stateful M K partitions retain the same context.
"""
from copy import deepcopy
import math

from leaf_catalog import duration as measured_duration, register
from numeric import Format, conversion
from solver import Unsupported


def duration(profile, kind, **parameters):
    try:
        return measured_duration(profile, kind, **parameters)
    except ValueError as exc:
        raise Unsupported(str(exc)) from exc


def lower(model, hardware):
    h = deepcopy(hardware)
    model = deepcopy(model)
    profile = h['native_leaf_profiles']
    graph = {'tasks': [], 'values': {}, 'outputs': [], 'state_groups': [],
             'source': model.get('source'), 'lowered': True, 'offline_weight_recipes': []}
    formats = {n: Format.read(v['format']) for n, v in model['values'].items() if 'format' in v}
    produced = {n for t in model['tasks'] for n in t['outputs']}
    pieces = {}

    def shape(name):
        dims = model['values'][name]['shape']
        if any(not isinstance(d, int) or d <= 0 for d in dims):
            raise Unsupported('recipe needs resolved positive dimensions: ' + name)
        return dims

    def fmt(name):
        if name not in formats:
            raise Unsupported('explicit native format missing: ' + name)
        return formats[name]

    def chunk(name, offset, count, *, producer=None, words=None, suffix=''):
        f = fmt(name)
        if offset % f.lanes:
            raise Unsupported('unaligned runtime record needs an explicit reader: ' + name)
        key = (name, offset, count, suffix)
        identity = f'{name}@{offset}:{count}{suffix}'
        if key not in pieces:
            if name in produced and producer is None:
                raise Unsupported('producer and consumer record partitions differ: ' + name)
            value = {'tensor': name, 'offset_elements': offset, 'valid_elements': count,
                     'words': words if words is not None else math.ceil(count/f.lanes),
                     'format': model['values'][name]['format']}
            if producer is not None:
                value['producer'] = producer
            else:
                value['site'] = h['external']
            if name in model['outputs']:
                value['output_site'] = h['external']
                graph['outputs'].append(identity)
            graph['values'][identity] = value
            pieces[key] = identity
        elif producer is not None and graph['values'][identity].get('producer') != producer:
            raise Unsupported('inconsistent recipe producer')
        return pieces[key]

    def task(identity, macro, op, attrs, ins, outs, ticks, program, stateful=False):
        numeric = 'native-record-v1'
        try:
            alternatives = register(h, macro, op, numeric, attrs,
                [graph['values'][n]['words'] for n in ins], [graph['values'][n]['words'] for n in outs],
                ticks, program, stateful=stateful)
        except ValueError as exc:
            raise Unsupported(str(exc)) from exc
        graph['tasks'].append({'id': identity, 'op': op, 'numeric': numeric, 'attributes': attrs,
                               'source_op': node['id'], 'inputs': ins, 'outputs': outs, 'alternatives': alternatives})

    for node in model['tasks']:
        op, ins, outs = node['op'], node['inputs'], node['outputs']
        attrs = node.get('attributes', {})
        if node.get('domain', '') not in ('', 'llmhardware.native'):
            raise Unsupported('unregistered recipe domain')
        if op in ('SiLU', 'Sigmoid', 'GELU', 'Softplus', 'GatedSiLU', 'Requantize', 'Handoff'):
            if len(outs) != 1 or not ins or any(shape(n) != shape(outs[0]) for n in ins):
                raise Unsupported('elementwise recipe shape/arity differs')
            f, output = fmt(ins[0]), fmt(outs[0])
            count = math.prod(shape(outs[0]))
            if op == 'Handoff':
                if len(ins) != 1 or f != output or attrs:
                    raise Unsupported('T preserves raw records and scale; no arithmetic')
                measured = sorted((int(k.split('"words":')[1].split('}')[0]), v) for k,v in profile['measurements'].items()
                                  if k.startswith('T:') and '"stall":0,' in k)
                if not measured:
                    raise Unsupported('no measured T transfer lengths')
                offset = 0
                while offset < count:
                    remaining_words = math.ceil((count-offset)/f.lanes)
                    if ins[0] in produced:
                        remaining_words = 1  # No unmodeled runtime concatenation.
                    words, ticks = max((w,t) for w,t in measured if w <= remaining_words)
                    length = min(words*f.lanes, count-offset)
                    tid = f'{node["id"]}@{offset}'
                    a = chunk(ins[0], offset, length)
                    b = chunk(outs[0], offset, length, producer=tid)
                    task(tid, 'T', op, {}, [a], [b], ticks,
                         [{'command': 'BeginWriteCommitTakeRelease', 'words': words, 'release_after': 'last consumer take'}], True)
                    offset += length
                continue
            if op == 'Requantize':
                if len(ins) != 1 or attrs:
                    raise Unsupported('conversion needs exactly one typed input')
                try:
                    program = conversion(f, output)
                except ValueError as exc:
                    raise Unsupported(str(exc)) from exc
                macro, width = 'E', f.lanes
                ticks = duration(profile, 'E', op=program['op'], shift=program['shift'])
            else:
                fn = {'SiLU': 0, 'Sigmoid': 1, 'GELU': 2, 'Softplus': 3, 'GatedSiLU': 0}[op]
                gated = op == 'GatedSiLU'
                expected = Format(16, -14 if op == 'Sigmoid' else -10, 2)
                if f != Format(16, -10, 2) or output != expected or attrs or len(ins) != (2 if gated else 1):
                    raise Unsupported('G requires two-lane native Q5.10 inputs and exact output encoding')
                if gated and fmt(ins[1]) != f:
                    raise Unsupported('G gate format differs')
                macro, width = 'G', 2
                program = {'command': 'Activate', 'function': fn, 'gated': gated, 'valid_lanes': 2}
                ticks = duration(profile, 'G', function=fn, gated=int(gated))
            for offset in range(0, count, width):
                valid = min(width, count-offset)
                tid = f'{node["id"]}@{offset}'
                args = [chunk(n, offset, valid) for n in ins]
                result = chunk(outs[0], offset, valid, producer=tid)
                task(tid, macro, op, {'valid_lanes': valid, 'recipe': program}, args, [result], ticks, [program])
        elif op in ('Add', 'Sub', 'Mul'):
            if len(ins)!=2 or len(outs)!=1 or attrs or any(shape(n)!=shape(outs[0]) for n in ins):
                raise Unsupported('E arithmetic needs same-shape native operands')
            a,b,c=(fmt(n) for n in ins+outs)
            if any(f.bits!=16 or f.unsigned or f.lanes!=c.lanes for f in (a,b,c)):
                raise Unsupported('E arithmetic cannot reorder or widen records')
            shift=c.exponent-a.exponent-b.exponent if op=='Mul' else 0
            if not 0<=shift<=31:
                raise Unsupported('E product exponent outside its native RNE shift')
            for offset in range(0,math.prod(shape(outs[0])),c.lanes):
                valid=min(c.lanes,math.prod(shape(outs[0]))-offset)
                args=[]
                for name in ins:
                    source=chunk(name,offset,valid)
                    if op!='Mul' and fmt(name)!=c:
                        try:
                            conv=conversion(fmt(name),c)
                        except ValueError as exc:
                            raise Unsupported(str(exc)) from exc
                        temporary=f'{node["id"]}:aligned:{name}'
                        model['values'][temporary]={'shape':shape(name),'format':model['values'][outs[0]]['format']}
                        formats[temporary]=c
                        tid=f'{temporary}@{offset}'
                        target=chunk(temporary,offset,valid,producer=tid)
                        task(tid,'E','Requantize',{'recipe':conv,'valid_lanes':valid},[source],[target],
                             duration(profile,'E',op=conv['op'],shift=conv['shift']),[conv])
                        source=target
                    args.append(source)
                tid=f'{node["id"]}@{offset}'
                result=chunk(outs[0],offset,valid,producer=tid)
                code={'Add':0,'Sub':1,'Mul':2}[op]
                program={'command':'Elementwise','op':code,'shift':shift,'valid_lanes':valid}
                task(tid,'E',op,program,args,[result],duration(profile,'E',op=code,shift=shift),[program])
        elif op in ('RMSNorm','L2Norm','Softmax'):
            soft=op=='Softmax'
            if len(outs)!=1 or len(ins)!=(1 if soft else 3) or attrs not in ({},{'axis':-1}):
                raise Unsupported('N row recipe arity/axis differs')
            dims=shape(ins[0])
            if not dims or shape(outs[0])!=dims:
                raise Unsupported('N row output shape differs')
            f=fmt(ins[0]); target=fmt(outs[0]); length=dims[-1]
            if f.bits!=16 or f.exponent!=-10 or f.lanes not in (1,2,4,8) or target!=Format(16,-14 if soft else -10,f.lanes):
                raise Unsupported('N input/output fixed-point encoding differs')
            if not 1<=length<=65535:
                raise Unsupported('N vector count exceeds native context')
            if not soft and (shape(ins[1])!=[length] or fmt(ins[1])!=f or math.prod(shape(ins[2]))!=1 or fmt(ins[2])!=Format(32,0,1)):
                raise Unsupported('N gamma or raw epsilon layout differs')
            mode=0 if soft else 1 if op=='RMSNorm' else 2
            for row in range(math.prod(dims[:-1])):
                group=[]
                prefix=f'{node["id"]}@row{row}'
                def stage(suffix,code,count,args,results,after):
                    tid=prefix+':'+suffix
                    p={'command':'N','mode':mode,'op':code,'count':count}
                    task(tid,'N','NStage',p,args,results,duration(profile,'N',mode=mode,op=code,count=count),[p],True)
                    graph['tasks'][-1]['after']=list(after)
                    group.append(tid)
                    return tid
                begin=stage('begin',0,0,[] if soft else [chunk(ins[2],0,1)],[],[])
                fragments=[(j,min(f.lanes,length-j)) for j in range(0,length,f.lanes)]
                stats=[stage(f'stats{j}',1,n,[chunk(ins[0],row*length+j,n)],[],[begin]) for j,n in fragments]
                final=stage('finalize',2,0,[],[],stats)
                if soft:
                    exps=[]
                    intermediate=[]
                    for j,n in fragments:
                        tid=prefix+f':exp{j}'; name=tid+':record'
                        graph['values'][name]={'words':1,'producer':tid,'valid_elements':n,
                                               'format':{'bits':16,'unsigned':True,'exponent':-15,'lanes':f.lanes}}
                        exps.append(stage(f'exp{j}',3,n,[chunk(ins[0],row*length+j,n)],[name],[final]))
                        intermediate.append(name)
                    barrier=stage('finish_exp',4,0,[],[],exps)
                else:
                    barrier=final
                for index,(j,n) in enumerate(fragments):
                    tid=prefix+f':replay{j}'
                    result=chunk(outs[0],row*length+j,n,producer=tid)
                    args=[intermediate[index]] if soft else [chunk(ins[0],row*length+j,n),chunk(ins[1],j,n)]
                    stage(f'replay{j}',6 if soft else 5,n,args,[result],[barrier])
                graph['state_groups'].append({'id':prefix,'tasks':group,
                    'meaning':'one finite N context, including all statistics/EXP/replay and intervening memory traffic'})
        elif op == 'MatMul':
            if len(ins) != 2 or len(outs) != 1 or attrs:
                raise Unsupported('M recipe supports a resolved two-input matrix product')
            a_shape, b_shape, c_shape = shape(ins[0]), shape(ins[1]), shape(outs[0])
            if len(a_shape)!=2 or len(b_shape)!=2 or a_shape[1]!=b_shape[0] or c_shape!=[a_shape[0],b_shape[1]]:
                raise Unsupported('M matrix dimensions differ')
            af,bf,cf = fmt(ins[0]),fmt(ins[1]),fmt(outs[0])
            if any(f.bits!=16 or f.unsigned for f in (af,bf,cf)) or af.lanes not in (1,2,4,8) or cf.lanes not in (1,2,4):
                raise Unsupported('M native S16 record shape differs')
            if ins[1] in produced or ins[1] not in model.get('weights', []):
                raise Unsupported('runtime B tile packing needs an explicit gather recipe; not an offline weight')
            rows, reduction, columns = a_shape[0], a_shape[1], b_shape[1]
            shift = cf.exponent-af.exponent-bf.exponent
            if not 0<=shift<=63 or reduction.bit_length()+30>62:
                raise Unsupported('M final scaling/accumulator bound outside native contract')
            for row in range(rows):
                for column in range(0,columns,cf.lanes):
                    n = min(cf.lanes, columns-column)
                    measured_columns = next(c for c in (1,2,4,8) if c>=n)
                    group=[]
                    for k in range(0,reduction,af.lanes):
                        valid = min(af.lanes,reduction-k)
                        tid=f'{node["id"]}@{row},{column},k{k}'
                        arg=chunk(ins[0],row*reduction+k,valid)
                        weight=f'{ins[1]}@M_B:{column},{k},{n},{valid}'
                        graph['values'].setdefault(weight,{'tensor':ins[1],'site':h['external'],'words':8,
                            'offline_layout':{'kind':'M-B-column-K8','matrix_shape':b_shape,'column':column,'columns':n,'k':k,'k_valid':valid}})
                        if not any(r['value']==weight for r in graph['offline_weight_recipes']):
                            graph['offline_weight_recipes'].append({'value':weight,**graph['values'][weight]['offline_layout']})
                        last=k+valid==reduction
                        output=[]
                        if last:
                            raw=f'{node["id"]}:native-s32'
                            model['values'][raw]={'shape':c_shape,'format':{'bits':32,'exponent':cf.exponent,'lanes':cf.lanes}}
                            formats[raw]=Format(32,cf.exponent,cf.lanes)
                            output=[chunk(raw,row*columns+column,n,producer=tid)]
                        program=[{'command':'LoadA','tile':0,'input':0},
                                 {'command':'LoadB','tile':0,'half':0,'input':1,'word_offset':0},
                                 {'command':'LoadB','tile':0,'half':1,'input':1,'word_offset':4},
                                 {'command':'Execute','rows':1,'columns':measured_columns,'k':valid,'clear':k==0}]
                        ticks=3+duration(profile,'M',columns=measured_columns,k=valid)
                        if k==0:
                            program.insert(0,{'command':'Scale','coefficient':1,'shift':0})
                            ticks+=duration(profile,'M_SCALE')
                        if last:
                            for half in range((n+3)//4):
                                program.append({'command':'ReadFinal','half':half,'width':16,'shift':shift,'pack16':False})
                                ticks+=duration(profile,'M_READ')
                        task(tid,'M','MAccumulate',{'columns':measured_columns,'k':valid,'clear':k==0,'last':last,'shift':shift},
                             [arg,weight],output,ticks,program,True)
                        if group:
                            graph['tasks'][-1]['after']=[group[-1]]
                        group.append(tid)
                    graph['state_groups'].append({'id':f'{node["id"]}:{row},{column}','tasks':group,
                        'meaning':'one native S64 result context; no K-partition intermediate rounding'})
                    convert_id=f'{node["id"]}@{row},{column}:pack'
                    converted=chunk(outs[0],row*columns+column,n,producer=convert_id)
                    recipe=conversion(formats[raw],cf)
                    task(convert_id,'E','Requantize',{'recipe':recipe,'valid_lanes':n},output,[converted],
                         duration(profile,'E',op=recipe['op'],shift=recipe['shift']),[recipe])
        elif op == 'GDNUpdate':
            if len(ins)!=5 or len(outs)!=2 or attrs:
                raise Unsupported('R GDN needs old-state, key, query, x and raw decay/beta parameters')
            dims=shape(ins[0])
            if len(dims)!=2 or dims[1] not in (2,4,8):
                raise Unsupported('R eight-lane state recipe shape differs')
            rows,columns=dims
            if shape(ins[1])!=[rows] or shape(ins[2])!=[rows] or shape(ins[3])!=[columns] or shape(outs[0])!=dims or shape(outs[1])!=[columns]:
                raise Unsupported('R state/key/query/output dimensions differ')
            if fmt(ins[0])!=fmt(outs[0]) or fmt(ins[0])!=fmt(ins[3]) or fmt(ins[3])!=fmt(outs[1]) or fmt(ins[0])!=Format(32,-16,min(columns,4)):
                raise Unsupported('R state/x/output require native Q16.16 records')
            if fmt(ins[1])!=Format(16,-14,8) or fmt(ins[2])!=fmt(ins[1]):
                raise Unsupported('R key/query require packed Q1.14')
            if shape(ins[4])!=[2] or fmt(ins[4])!=Format(32,-31,2,True):
                raise Unsupported('R raw decay/beta parameter record differs')
            lengths=sorted(int(k.split('"rows":')[1].split('}')[0]) for k in profile['measurements'] if k.startswith('R_PREDICT:'))
            if not lengths:
                raise Unsupported('R tiled pass profile missing')
            tile_rows=max(lengths)
            group=[]; parts=[]
            def rstage(suffix,kind,args,result,parameters,after):
                tid=node['id']+':'+suffix
                program={'command':kind,**parameters,'inactive_lanes':'zero',
                         'state_bank':'shadow until all passes succeed'}
                measured={'rows':parameters['rows']} if 'rows' in parameters else {}
                task(tid,'R','RStage',program,args,result,duration(profile,kind,**measured),[program],True)
                graph['tasks'][-1]['after']=list(after)
                group.append(tid)
                return tid
            begin=rstage('begin','R_BEGIN',[],[],{},[])
            previous=begin
            for offset in range(0,rows,tile_rows):
                length=min(tile_rows,rows-offset)
                tid=node['id']+f':predict{offset}'
                temporary=tid+':decayed'
                graph['values'][temporary]={'words':length*math.ceil(columns/4),'producer':tid,
                    'format':model['values'][ins[0]]['format'],'valid_elements':length*columns}
                args=[chunk(ins[0],offset*columns,length*columns),chunk(ins[1],offset,length),chunk(ins[4],0,2)]
                previous=rstage(f'predict{offset}','R_PREDICT',args,[temporary],
                    {'rows':length,'columns':columns,'clear_dot':offset==0},[previous])
                parts.append((offset,length,temporary))
            error=rstage('error','R_ERROR',[chunk(ins[3],0,columns),chunk(ins[4],0,2)],[],{},[previous])
            previous=error
            for offset,length,temporary in parts:
                tid=node['id']+f':update{offset}'
                result=chunk(outs[0],offset*columns,length*columns,producer=tid)
                previous=rstage(f'update{offset}','R_UPDATE',
                    [temporary,chunk(ins[1],offset,length),chunk(ins[2],offset,length)],[result],
                    {'rows':length,'columns':columns,'clear_dot':offset==0},[previous])
            tid=node['id']+':finish'
            result=chunk(outs[1],0,columns,producer=tid)
            rstage('finish','R_FINISH',[],[result],{},[previous])
            graph['state_groups'].append({'id':node['id']+':global-dot-update','tasks':group,
                'meaning':'global prediction/query dot and update survive state-tile replacement; no per-tile rounding'})
        else:
            raise Unsupported('no native recipe for '+op)
    graph['outputs']=list(dict.fromkeys(graph['outputs']))
    return graph,h
