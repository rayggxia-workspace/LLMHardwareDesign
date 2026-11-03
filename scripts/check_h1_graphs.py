"""H1 v0.1 offline graph compiler and abstract protocol/resource checker.

No RTL, numerical or physical simulation. One record invokes a bounded helper;
payload words/real ACKs remain obligations of the future common RTL.
"""
from __future__ import annotations
import argparse
from collections import Counter
import copy
import hashlib
import json
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]
DATA = Path('project/experiments/hybrid_control/h1/v0_1')
TYPE = dict(element='signed_integer', bits=16, fin=10, shape=[2, 1024],
            layout='token_major_natural_axis', tail=0, profile='AF_BASELINE_W7_EPS1')
OPS = {name: i + 1 for i, name in enumerate([
    'ALLOC', 'IMPORT', 'WAIT_STORED', 'ARM', 'START', 'LOAD', 'WAIT_INPUT',
    'PARAM', 'WAIT_PARAM', 'WAIT_SEALED', 'STORE', 'CLOSE', 'WAIT_RELEASE',
    'WAIT_DONE', 'FREE', 'IF', 'SETOUT', 'HALT', 'EXPORT', 'WAIT_HOST_STORED', 'CLOSE_OUTPUT'])}
FIELDS = {op:set('a') for op in OPS}
FIELDS.update(ALLOC={'a'}, IMPORT={'a','imm'}, ARM={'a','b','c','imm','aux'},
              LOAD={'a','b','c','imm'}, STORE={'a','b','c','imm'}, WAIT_INPUT={'a','b','c'}, PARAM={'a','b','c','imm'},
              IF={'a','b','c'}, HALT=set(), EXPORT={'a','imm'})


class Reject(ValueError):
    pass


def require(test, code):
    if not test:
        raise Reject(code)


def canonical(x):
    return (json.dumps(x, ensure_ascii=False, indent=2) + '\n').encode('utf-8')


def validate(graph, target):
    require(graph.get('schema_version') == 'h1.graph.0.1', 'E_SCHEMA')
    require(graph['type'] == TYPE, 'E_TYPE_LAYOUT_PROFILE')
    require(target['slot_bytes'] == 4096 and target['slot_count'] >= 1, 'E_STORE_SHAPE')
    require(target['edge_store_bytes'] >= target['slot_count']*target['slot_bytes'] and
            target['edge_store_bytes'] == 16384 and target['slot_count'] <= 4, 'E_EDGE_STORE_BUDGET')
    require(target['native_leaves'] == dict(M=2,N=2,E=2,G=1,S=3,T=2,R=0), 'E_NATIVE_RESOURCE_BUDGET')
    require(target['edge_store_port_owners'] == 1 and target['transfer_words_inflight'] == 1, 'E_PORT_PROFILE')
    require(target['record_bits'] == 128, 'E_RECORD_WIDTH')
    require(1 <= target['max_records'] <= 256 and 1 <= target['max_calls'] <= 16 and
            1 <= target['max_object_records'] <= 17 and 1 <= target['max_parameter_records'] <= 16 and
            target['route_records'] == 6, 'E_TARGET_TABLE_BUDGET')
    require(target['ack_slots'] >= 1 and target['event_slots'] >= 1, 'E_RETURN_CAPACITY')
    require(target['max_active_jobs'] == 1, 'E_CONCURRENCY_SCOPE')
    require(len(graph['calls']) > 0 and len(graph['calls']) <= target['max_calls'], 'E_CALL_CAPACITY')
    produced = {'x'}
    names = set()
    param_kernel = {}
    for call in graph['calls']:
        require(call['id'] not in names, 'E_CALL_ID')
        names.add(call['id'])
        require(call['kernel'] in ('A2', 'F2'), 'GAP_ENTRY')
        require(call['input'] in produced, 'E_READ_BEFORE_PRODUCE')
        require(call['output'] not in produced, 'E_VERSION_SINGLE_ASSIGNMENT')
        require(call['parameter_ref'] and isinstance(call['parameter_ref'], str), 'E_PARAM_ID')
        require(param_kernel.get(call['parameter_ref'], call['kernel']) == call['kernel'], 'E_PARAM_PROFILE')
        param_kernel[call['parameter_ref']] = call['kernel']
        produced.add(call['output'])
    out = graph['output']
    require(out['kind'] in ('direct', 'select'), 'GAP_CONTROL_GRAMMAR')
    choices = [out['object']] if out['kind'] == 'direct' else [out['true'], out['false']]
    require(all(x in produced for x in choices), 'E_OUTPUT_UNDEFINED')
    if out['kind'] == 'select':
        require(out['predicate'] == 'p0' and out['capture'] == 'AT_ACCEPT', 'E_PREDICATE_LIFETIME')
        require(out['true'] != out['false'], 'E_SELECT_IDENTICAL')
    require(graph.get('feedback') is None, 'GAP_RUNTIME_FEEDBACK')
    return choices


def compile_graph(graph, target):
    choices = validate(graph, target)
    objects = ['x'] + [c['output'] for c in graph['calls']]
    oid = {n: i for i, n in enumerate(objects)}
    uses = Counter(c['input'] for c in graph['calls'])
    ids = {c['id']: i + 1 for i, c in enumerate(graph['calls'])}
    params = list(dict.fromkeys(c['parameter_ref'] for c in graph['calls']))
    pid = {n: i for i, n in enumerate(params)}
    p = []

    def emit(op, a=0, b=0, c=0, imm=0, flags=0, aux=0):
        p.append(dict(op=op, flags=flags, a=a, b=b, c=c, imm=imm, next=len(p)+1, aux=aux))

    emit('ALLOC', oid['x'])
    emit('IMPORT', oid['x'], imm=256)
    emit('WAIT_STORED', oid['x'])
    for call in graph['calls']:
        out, src = oid[call['output']], oid[call['input']]
        island = 1 if call['kernel'] == 'A2' else 2
        emit('ALLOC', out)
        for row in range(1 if island == 1 else 2):
            context = ids[call['id']] * 2 + row
            # Same physical island, one native T lease/job at a time.
            emit('ARM', island, out, row, context, aux=pid[call['parameter_ref']])
            emit('LOAD', src, island, row, 256 if island == 1 else 128)
            emit('WAIT_INPUT', src, island, row)
            last_row = island == 1 or row == 1
            emit('PARAM', pid[call['parameter_ref']], island, row, 192 if island == 1 else 128)
            emit('WAIT_PARAM', island)
            if last_row:
                uses[call['input']] -= 1
                if uses[call['input']] == 0 and call['input'] not in choices:
                    emit('FREE', src)
            emit('START', island)
            emit('WAIT_SEALED', island)
            emit('STORE', island, out, row, 256 if island == 1 else 128)
            emit('WAIT_STORED', out)
            emit('CLOSE', island)
            emit('WAIT_RELEASE', island)
            emit('WAIT_DONE', island)
    if graph['output']['kind'] == 'direct':
        emit('SETOUT', oid[choices[0]])
        emit('EXPORT', oid[choices[0]], imm=256)
        emit('WAIT_HOST_STORED', oid[choices[0]])
        emit('CLOSE_OUTPUT', oid[choices[0]])
        emit('HALT')
    else:
        pc = len(p)
        emit('IF', 0, pc+1, pc+7)
        emit('FREE', oid[choices[1]])
        emit('SETOUT', oid[choices[0]])
        emit('EXPORT', oid[choices[0]], imm=256)
        emit('WAIT_HOST_STORED', oid[choices[0]])
        emit('CLOSE_OUTPUT', oid[choices[0]])
        emit('HALT')
        emit('FREE', oid[choices[0]])
        emit('SETOUT', oid[choices[1]])
        emit('EXPORT', oid[choices[1]], imm=256)
        emit('WAIT_HOST_STORED', oid[choices[1]])
        emit('CLOSE_OUTPUT', oid[choices[1]])
        emit('HALT')
    p[-1]['next'] = 0
    require(len(p) <= min(65535, target['max_records']), 'E_PROGRAM_CAPACITY')
    require(len(objects) < 65536 and len(params) < 65536, 'E_INDEX_CAPACITY')
    require(len(objects) <= target['max_object_records'] and len(params) <= target['max_parameter_records'], 'E_METADATA_CAPACITY')
    for pc, ins in enumerate(p):
        if ins['op'] not in ('HALT', 'IF'):
            require(ins['next'] < len(p), 'E_PC_RANGE')
        if ins['op'] == 'IF':
            require(ins['b'] < len(p) and ins['c'] < len(p), 'E_PC_RANGE')
    return dict(graph=graph['name'], objects=objects, parameters=params, instructions=p)


def encode(program):
    # Conceptual little-endian 128-bit records; not a physical bitcell map.
    out = bytearray()
    for i in program['instructions']:
        out += struct.pack('<BBHHHIHH', OPS[i['op']], i['flags'], i['a'], i['b'], i['c'],
                           i['imm'], i['next'], i['aux'])
    return bytes(out)


def verify_decode(program, raw):
    reverse={v:k for k,v in OPS.items()}
    require(len(raw)==16*len(program['instructions']), 'E_ENCODING_LENGTH')
    decoded=[]
    for off in range(0,len(raw),16):
        op,flags,a,b,c,imm,nxt,aux=struct.unpack('<BBHHHIHH',raw[off:off+16])
        require(op in reverse, 'E_OPCODE')
        decoded.append(dict(op=reverse[op],flags=flags,a=a,b=b,c=c,imm=imm,next=nxt,aux=aux))
    require(decoded==program['instructions'], 'E_ENCODING_READBACK')


def metadata(graph, program):
    """Candidate table layouts. Parameter digests identify names, not weights."""
    consumers = Counter(c['input'] for c in graph['calls'])
    objects = []
    raw_objects = bytearray()
    for i,name in enumerate(program['objects']):
        producer = next((j+1 for j,c in enumerate(graph['calls']) if c['output']==name),65535)
        semantic_hash = hashlib.sha256(canonical(dict(graph=graph['name'],object=name,type=graph['type']))).digest()
        objects.append(dict(id=i,name=name,version_within_task=1,bytes=4096,shape=[2,1024],
                            consumer_calls=consumers[name],producer_call=producer,
                            slot_binding='DYNAMIC_FIRST_FREE_WITHIN_FOUR_SLOTS',semantic_sha256=semantic_hash.hex()))
        raw_objects += struct.pack('<HHIIHHBBBBHHI32sI',i,1,4096,int(name=='x'),2,1024,16,10,1,1,
                                   consumers[name],producer,0,semantic_hash,0)
    params=[]; raw_params=bytearray()
    for i,name in enumerate(program['parameters']):
        kernel=next(c['kernel'] for c in graph['calls'] if c['parameter_ref']==name)
        digest=hashlib.sha256(name.encode()).digest()[:24]
        params.append(dict(id=i,name=name,kernel=kernel,reference_digest192=digest.hex(),
                           identity_scope='SYMBOLIC_REFERENCE_ONLY; REAL_WEIGHT_MANIFEST_GAP'))
        raw_params += struct.pack('<HHHH24s',i,1,192 if kernel=='A2' else 128,1 if kernel=='A2' else 2,digest)
    routes=[];raw_routes=bytearray()
    for i,(src,dst) in enumerate([(0,3),(3,1),(3,2),(1,3),(2,3),(3,0)]):
        routes.append(dict(id=i,source=src,dest=dst,data_bits=128,ack_bits='H2_TBD',inflight_words=1,
                           status='CANDIDATE_SERVICE_ROUTE_NOT_WIRED'))
        raw_routes += struct.pack('<HHHHHHHH',i,src,dst,128,0,1,1,0)
    header=struct.pack('<8sHHHHIIII32s',b'H1IRv001',len(program['instructions']),len(objects),len(params),len(routes),
                       64,64+len(encode(program)),64+len(encode(program))+len(raw_objects),
                       64+len(encode(program))+len(raw_objects)+len(raw_params),hashlib.sha256(canonical(graph)).digest())
    require(len(header)==64 and len(raw_objects)==64*len(objects) and len(raw_params)==32*len(params), 'E_TABLE_ENCODING')
    image=header+encode(program)+raw_objects+raw_params+raw_routes
    return dict(header_bytes=64,object_record_bytes=64,parameter_record_bytes=32,route_record_bytes=16,
                objects=objects,parameters=params,routes=routes,product_image_bytes=len(image),
                product_image_sha256=hashlib.sha256(image).hexdigest()),image


def execute(graph, target, program, predicate=False):
    """Sequential abstract events under fair native/parameter/ACK services."""
    choices = validate(graph, target)
    objs = program['objects']
    for ins in program['instructions']:
        require(set(ins)=={'op','flags','a','b','c','imm','next','aux'} and ins['op'] in OPS, 'E_OPCODE')
        require(ins['flags'] == 0 and all(ins[k]==0 for k in ('a','b','c','imm','aux') if k not in FIELDS[ins['op']]), 'E_RESERVED_FIELDS')
        require(all(type(ins[k]) is int and 0 <= ins[k] < 65536 for k in ('a','b','c','aux','next')) and
                type(ins['imm']) is int and 0 <= ins['imm'] < 2**32, 'E_FIELD_RANGE')
    by_output = {c['output']: c for c in graph['calls']}
    remaining = Counter(c['input'] for c in graph['calls'])
    live, valid, slot, born, life, trace = set(), {}, {}, {}, [], []
    allocated, leases = set(), []
    active = None
    pending = None
    output = None
    host_stored = False
    output_closed = False
    host_export_started = False
    peak = weight_bytes = input_bytes = output_bytes = words_acked = 0
    pc = steps = 0
    p = program['instructions']
    counts = Counter()

    def event(op, **kw):
        trace.append(dict(step=len(trace), pc=pc, op=op, live=[objs[i] for i in sorted(live)],
                          slots={objs[i]: slot[i] for i in sorted(live)}, **kw))

    def retire_object(i, published=False):
        require(i in live, 'E_FREE_NOT_LIVE')
        require(remaining[objs[i]] == 0, 'E_FREE_BEFORE_CONSUMER_ACK')
        require(not pending or (pending.get('source') != i and pending.get('dest') != i), 'E_FREE_INFLIGHT')
        require(output != i or published, 'E_FREE_PUBLISHED_OUTPUT')
        life.append(dict(object=objs[i], slot=slot[i], allocate_pc=born[i], free_pc=pc))
        live.remove(i); valid.pop(i); slot.pop(i); born.pop(i)

    while True:
        require(0 <= pc < len(p), 'E_PC_RANGE')
        steps += 1
        require(steps <= target['max_records']*2, 'E_CONTROL_CYCLE')
        ins = p[pc]; op, a, b, c, imm = (ins[k] for k in ('op', 'a', 'b', 'c', 'imm'))
        counts[op] += 1
        require(op in OPS, 'E_OPCODE')
        if op == 'ALLOC':
            require(a < len(objs) and a not in allocated, 'E_ALLOC_ID')
            free = set(range(target['slot_count'])) - set(slot.values())
            require(bool(free), 'E_EDGE_STORE_CAPACITY')
            slot[a] = min(free); live.add(a); allocated.add(a); valid[a] = set(); born[a] = pc
            peak = max(peak, len(live))
        elif op == 'IMPORT':
            require(active is None and pending is None and objs[a] == 'x' and a in live, 'E_IMPORT_STATE')
            require(imm == 256 and not valid[a], 'E_TRANSFER_LENGTH')
            pending = dict(kind='import', dest=a, dest_slot=slot[a], words=imm)
        elif op == 'ARM':
            require(active is None and pending is None, 'E_NATIVE_REENTRY')
            require(b in live and a in (1, 2), 'E_ARM_RESOURCE')
            call = by_output.get(objs[b])
            require(call and a == (1 if call['kernel'] == 'A2' else 2), 'E_ENTRY_BINDING')
            require(c in ([0] if a == 1 else [0, 1]), 'E_ROW_RANGE')
            require(c not in valid[b], 'E_OUTPUT_OVERWRITE')
            require(a == 1 or c == 0 or valid[b] == {0}, 'E_F_ROW_ORDER')
            require(program['parameters'][ins['aux']] == call['parameter_ref'], 'E_PARAM_BINDING')
            require(imm == (graph['calls'].index(call)+1)*2+c, 'E_CONTEXT_BINDING')
            active = dict(island=a, dest=b, row=c, context=imm, parameter=ins['aux'],
                          arm_pc=pc,
                          call=call, started=False, input=False, param=False, sealed=False,
                          stored=False, closed=False, released=False)
        elif op == 'START':
            require(active and active['island'] == a and active['input'] and active['param'] and not active['started'], 'E_START_STATE')
            active['started'] = True
        elif op == 'LOAD':
            require(active and not active['started'] and not active['input'] and pending is None, 'E_LOAD_STATE')
            require(a in live and valid[a] == {0, 1}, 'E_READ_BEFORE_STORED')
            require(objs[a] == active['call']['input'] and b == active['island'] and c == active['row'], 'E_INPUT_BINDING')
            require(imm == (256 if b == 1 else 128), 'E_TRANSFER_LENGTH')
            pending = dict(kind='input', source=a, island=b, row=c, words=imm)
            active['source'] = a
        elif op == 'WAIT_INPUT':
            require(pending and pending['kind'] == 'input' and pending['source'] == a and pending['island'] == b and pending['row'] == c, 'E_INPUT_ACK')
            input_bytes += pending['words']*16; words_acked += pending['words']
            active['input'] = True
            event('HIDDEN_STORED', source=objs[a], words=pending['words'], basis='future wrapper fact from real native S ACK; not whole-frame input_stored')
            pending = None
        elif op == 'PARAM':
            require(active and active['input'] and not active['param'] and pending is None, 'E_PARAM_STATE')
            require(a == active['parameter'] and b == active['island'] and c == active['row'], 'E_PARAM_BINDING')
            require(imm == (192 if b == 1 else 128), 'E_PARAM_LENGTH')
            pending = dict(kind='param', island=b, words=imm)
        elif op == 'WAIT_PARAM':
            require(pending and pending['kind'] == 'param' and pending['island'] == a, 'E_PARAM_ACK')
            words_acked += pending['words']; active['param'] = True; pending = None
            src = active['source']
            if a == 1 or active['row'] == 1:
                remaining[objs[src]] -= 1
                require(remaining[objs[src]] >= 0, 'E_DUP_CONSUMPTION')
            event('FRAME_INPUT_STORED',source=objs[src],row=active['row'],basis='complete native frame S ACK before START')
        elif op == 'WAIT_SEALED':
            require(active and active['island'] == a and active['started'] and active['input'] and active['param'] and not active['sealed'] and pending is None, 'E_SEALED_STATE')
            active['sealed'] = True
            weight_bytes += 6*1024*1024 if a == 1 else 9*1024*1024
        elif op == 'STORE':
            require(active and active['island'] == a and active['sealed'] and not active['stored'] and pending is None, 'E_STORE_STATE')
            require(b == active['dest'] and c == active['row'] and b in live, 'E_OUTPUT_BINDING')
            require(imm == (256 if a == 1 else 128), 'E_TRANSFER_LENGTH')
            pending = dict(kind='output', dest=b, dest_slot=slot[b], words=imm)
        elif op == 'WAIT_STORED':
            require(pending and pending.get('dest') == a and pending['kind'] in ('import', 'output'), 'E_STORED_ACK')
            require(a in live and slot[a] == pending['dest_slot'], 'E_ACK_SLOT_VERSION')
            if pending['kind'] == 'import':
                valid[a] = {0, 1}
            else:
                valid[a].update([0, 1] if active['island'] == 1 else [active['row']])
                active['stored'] = True; output_bytes += pending['words']*16
            words_acked += pending['words']
            event('DEST_S_ACK_THEN_SOURCE_RETIRE', dest=objs[a], words=pending['words'],
                  kind=pending['kind'], basis='required helper word loop, not RTL evidence')
            pending = None
        elif op == 'CLOSE':
            require(active and active['island'] == a and active['stored'] and pending is None and not active['closed'], 'E_CLOSE_BEFORE_ACK')
            active['closed'] = True
        elif op == 'WAIT_RELEASE':
            require(active and active['island'] == a and active['closed'] and not active['released'], 'E_RELEASE_STATE')
            active['released'] = True
            active['release_pc'] = pc
        elif op == 'WAIT_DONE':
            require(active and active['island'] == a and active['released'] and pending is None, 'E_DONE_BEFORE_DRAIN_RELEASE')
            leases.append(dict(island='A' if a==1 else 'F',context=active['context'],row=active['row'],
                               arm_pc=active['arm_pc'],release_pc=active['release_pc'],done_pc=pc,
                               scope='whole native job resource envelope; A has two internal T leases'))
            active = None
        elif op == 'FREE':
            retire_object(a)
        elif op == 'IF':
            require(active is None and pending is None and a == 0, 'E_JOIN_NOT_QUIESCENT')
            require(graph['output']['kind'] == 'select' and all(valid.get(objs.index(n)) == {0, 1} for n in choices), 'E_JOIN_INPUT')
        elif op == 'SETOUT':
            require(active is None and pending is None and output is None and a in live and valid[a] == {0, 1}, 'E_PUBLISH_STATE')
            chosen = choices[0] if graph['output']['kind'] == 'direct' or predicate else choices[1]
            require(objs[a] == chosen, 'E_WRONG_SELECTED_VERSION')
            output = a
        elif op == 'EXPORT':
            require(not host_export_started, 'E_DUPLICATE_EXPORT')
            require(output == a and a in live and valid[a] == {0,1} and active is None and pending is None, 'E_EXPORT_STATE')
            require(imm == 256, 'E_TRANSFER_LENGTH')
            pending = dict(kind='host',source=a,words=imm)
            host_export_started=True
        elif op == 'WAIT_HOST_STORED':
            require(pending and pending['kind']=='host' and pending['source']==a, 'E_HOST_ACK')
            words_acked += pending['words']; host_stored=True; pending=None
        elif op == 'CLOSE_OUTPUT':
            require(output == a and host_stored and pending is None, 'E_OUTPUT_CLOSE_BEFORE_ACK')
            retire_object(a,published=True); output_closed=True
        elif op == 'HALT':
            require(active is None and pending is None and output is not None and output_closed, 'E_HALT_BUSY')
            require(not live and all(n == 0 for n in remaining.values()), 'E_HALT_LEAK')
            event(op, predicate=predicate, output=objs[output])
            break
        event(op, operands={k: ins[k] for k in ('a','b','c','imm')})
        pc = ins['b' if predicate else 'c'] if op == 'IF' else ins['next']
    return dict(predicate=predicate, output=objs[output], peak_slots=peak, peak_bytes=peak*4096,
                parameter_weight_bytes=weight_bytes, hidden_input_bytes=input_bytes,
                hidden_output_to_edge_bytes=output_bytes, abstract_S_ACK_words=words_acked,
                instruction_executions=steps, native_calls=counts['START'], counts=dict(counts),
                lifetimes=life, native_resource_lifetimes=leases, trace=trace)


def check_all(root, out, source_commit='UNCOMMITTED_LOCAL'):
    data = root/DATA
    target = json.loads((data/'target.json').read_text(encoding='utf-8'))
    graphs = [json.loads(p.read_text(encoding='utf-8')) for p in sorted((data/'graphs').glob('*.json'))]
    require(len(graphs) == 3, 'E_REGRESSION_SET')
    reports, inputs = [], []
    out.mkdir(parents=True, exist_ok=True)
    for graph in graphs:
        program = compile_graph(graph, target)
        runs = [execute(graph, target, program, v) for v in ([False, True] if graph['output']['kind']=='select' else [False])]
        encoded = encode(program)
        verify_decode(program,encoded)
        meta,image = metadata(graph,program)
        budget = dict(header_bytes=64,program_records=len(program['instructions']), record_bits=128,
                      program_bytes=len(encoded), object_records=len(program['objects']), object_bytes=64*len(program['objects']),
                      parameter_records=len(program['parameters']), parameter_reference_bytes=32*len(program['parameters']),
                      route_records=target['route_records'], route_bytes=16*target['route_records'])
        budget['logical_metal_table_bytes'] = sum(budget[k] for k in ['header_bytes','program_bytes','object_bytes','parameter_reference_bytes','route_bytes'])
        require(budget['logical_metal_table_bytes']==len(image), 'E_IMAGE_BUDGET')
        # Includes one input/output DMA each and one Sedge<->A/F service route each.
        summary = dict(graph=graph['name'], statuses=dict(semantic='SEMANTIC_LEGAL_IN_DECLARED_SLICE',
                       candidate_static='SCHEDULE_FEASIBLE_UNDER_H1_ABSTRACT_SERVICES', implemented='GAP_COMMON_SEQUENCER_ENDPOINT_EDGE_STORE',
                       mapped='GAP_REAL_TOPOLOGY_AND_PARAMETER_SERVICE', physical='UNVERIFIED', quality='NOT_ACCEPTED'),
                       budget=budget, scenarios=[{k:v for k,v in run.items() if k!='trace'} for run in runs])
        reports.append(summary)
        base = out/graph['name']
        base.with_suffix('.program.json').write_bytes(canonical(program))
        base.with_suffix('.program.hex').write_text('\n'.join(encoded[i:i+16].hex() for i in range(0,len(encoded),16))+'\n',encoding='ascii')
        base.with_suffix('.tables.json').write_bytes(canonical(meta))
        base.with_suffix('.image.hex').write_text('\n'.join(image[i:i+16].hex() for i in range(0,len(image),16))+'\n',encoding='ascii')
        lowered=[dict(pc=i,island='A' if x['a']==1 else 'F',row=x['c'],context=x['imm'],parameter_id=x['aux'],
                      output_object=program['objects'][x['b']],weight_bytes=(6 if x['a']==1 else 9)*1024*1024)
                 for i,x in enumerate(program['instructions']) if x['op']=='ARM']
        base.with_suffix('.lowered.json').write_bytes(canonical(dict(graph=graph['name'],native_calls=lowered)))
        base.with_suffix('.schedule.json').write_bytes(canonical(dict(graph=graph['name'],scenarios=runs)))
    negatives = []

    def bad(name, code, g=None, t=None, mutate=None):
        gg, tt = copy.deepcopy(g or graphs[0]), copy.deepcopy(t or target)
        try:
            pp = compile_graph(gg,tt)
            if mutate:
                mutate(pp)
            execute(gg,tt,pp)
        except Reject as e:
            require(str(e)==code, f'E_NEGATIVE_DIAGNOSTIC:{name}:{e}!={code}')
            negatives.append(dict(case=name,diagnostic=code,result='EXPECTED_REJECT'))
        else:
            raise Reject('E_NEGATIVE_ACCEPTED:'+name)

    g=copy.deepcopy(graphs[0]);g['type']['fin']=12;bad('same_width_wrong_Fin','E_TYPE_LAYOUT_PROFILE',g=g)
    g=copy.deepcopy(graphs[0]);g['type']['layout']='head_paired_rope';bad('wrong_hidden_axis','E_TYPE_LAYOUT_PROFILE',g=g)
    g=copy.deepcopy(graphs[0]);g['calls'][0]['input']='future';bad('uninitialized_edge','E_READ_BEFORE_PRODUCE',g=g)
    g=copy.deepcopy(graphs[0]);g['calls'][0]['kernel']='D';bad('missing_D_entry','GAP_ENTRY',g=g)
    g=copy.deepcopy(graphs[0]);g['calls'][1]['parameter_ref']=g['calls'][0]['parameter_ref'];bad('reuse_parameter_wrong_ABI','E_PARAM_PROFILE',g=g)
    g=copy.deepcopy(graphs[0]);g['feedback']={'bound':2,'initial':'x'};bad('runtime_loop_not_lowered','GAP_RUNTIME_FEEDBACK',g=g)
    t=copy.deepcopy(target);t['ack_slots']=0;bad('no_return_capacity','E_RETURN_CAPACITY',t=t)
    t=copy.deepcopy(target);t['slot_count']=2;bad('fork_store_overflow','E_EDGE_STORE_CAPACITY',g=graphs[2],t=t)
    t=copy.deepcopy(target);t['max_records']=16;bad('program_too_deep','E_PROGRAM_CAPACITY',t=t)
    t=copy.deepcopy(target);t['max_object_records']=2;bad('object_table_overflow','E_METADATA_CAPACITY',t=t)
    t=copy.deepcopy(target);t['edge_store_bytes']=4096;bad('inconsistent_physical_store_size','E_EDGE_STORE_BUDGET',t=t)
    t=copy.deepcopy(target);t['edge_store_port_owners']=0;bad('missing_edge_owner','E_PORT_PROFILE',t=t)
    t=copy.deepcopy(target);t['native_leaves']['S']=0;bad('missing_native_S','E_NATIVE_RESOURCE_BUDGET',t=t)
    t=copy.deepcopy(target);t['record_bits']=64;bad('inconsistent_record_width','E_RECORD_WIDTH',t=t)
    def replace_first(pp,op,new):
        ins=pp['instructions'][next(i for i,x in enumerate(pp['instructions']) if x['op']==op)]
        ins['op']=new
        for k in ('a','b','c','imm','aux'):
            if k not in FIELDS[new]: ins[k]=0
    bad('drop_initial_store_ACK','E_STORED_ACK',mutate=lambda p: replace_first(p,'IMPORT','WAIT_STORED'))
    bad('producer_DONE_before_drain','E_DONE_BEFORE_DRAIN_RELEASE',mutate=lambda p: replace_first(p,'WAIT_SEALED','WAIT_DONE'))
    bad('close_before_output_ACK','E_CLOSE_BEFORE_ACK',mutate=lambda p: replace_first(p,'STORE','CLOSE'))
    bad('native_reentry_without_release','E_NATIVE_REENTRY',mutate=lambda p: replace_first(p,'START','ARM'))
    bad('free_before_consumer_ACK','E_FREE_BEFORE_CONSUMER_ACK',mutate=lambda p: replace_first(p,'IMPORT','FREE'))
    def premature_dest_free(pp):
        ins=next(x for x in pp['instructions'] if x['op']=='WAIT_STORED' and x['a']!=0)
        ins['op']='FREE'
    # A-only graph has no downstream consumer, isolating the in-flight destination guard.
    g=copy.deepcopy(graphs[0]);g['calls']=g['calls'][:1];g['output']={'kind':'direct','object':'a'}
    bad('free_inflight_destination','E_FREE_INFLIGHT',g=g,mutate=premature_dest_free)
    bad('reserved_flags_nonzero','E_RESERVED_FIELDS',mutate=lambda p:p['instructions'][0].update(flags=1))
    def early_start(pp):
        ins=next(x for x in pp['instructions'] if x['op']=='LOAD')
        ins.update(op='START',a=ins['b'],b=0,c=0,imm=0)
    bad('native_start_before_whole_frame','E_START_STATE',mutate=early_start)
    def duplicate_export(pp):
        pc=next(i for i,x in enumerate(pp['instructions']) if x['op']=='CLOSE_OUTPUT')
        obj=pp['instructions'][pc]['a']
        extra=[dict(op='EXPORT',flags=0,a=obj,b=0,c=0,imm=256,next=pc+1,aux=0),
               dict(op='WAIT_HOST_STORED',flags=0,a=obj,b=0,c=0,imm=0,next=pc+2,aux=0)]
        pp['instructions'][pc:pc]=extra
        for i,ins in enumerate(pp['instructions']): ins['next']=0 if ins['op']=='HALT' else i+1
    bad('duplicate_final_export','E_DUPLICATE_EXPORT',mutate=duplicate_export)
    bad('publish_unwritten_output','E_PUBLISH_STATE',mutate=lambda p: replace_first(p,'START','SETOUT'))
    def double_free(pp):
        replace_first(pp,'START','FREE')
        next(x for x in pp['instructions'] if x['op']=='FREE' and x['a']==1)['a']=0
    bad('free_object_twice','E_FREE_NOT_LIVE',mutate=double_free)
    bad('free_hidden_before_gamma_frame_ACK','E_FREE_BEFORE_CONSUMER_ACK',mutate=lambda p:replace_first(p,'PARAM','FREE'))
    bad('IF_invalid_target','E_PC_RANGE',g=graphs[2],mutate=lambda p: next(x for x in p['instructions'] if x['op']=='IF').update(c=65535))
    bad('F_row_wrong_length','E_TRANSFER_LENGTH',mutate=lambda p: next(x for x in p['instructions'] if x['op']=='LOAD' and x['b']==2).update(imm=256))
    for path in [data/'target.json', *sorted((data/'graphs').glob('*.json')), Path(__file__).resolve()]:
        raw=path.read_bytes();inputs.append(dict(path=path.relative_to(root).as_posix(),sha256=hashlib.sha256(raw).hexdigest()))
    products=[]
    for path in sorted(out.iterdir()):
        if path.suffix in ('.hex','.json') and path.name != 'report.json':
            products.append(dict(path=path.name,sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    report=dict(schema_version='h1.static_report.0.1',input_research_commit='08451c3a563cdb331a3516d83cbf9647cd0554b1',
                checker_source_commit=source_commit,tool=dict(python=sys.version,engine='stdlib abstract checker; no HDL execution'),
                scope='three finite graph fixtures, four branch scenarios; not all-graph proof or numerical/physical validation',
                target=target,graphs=reports,negative_cases=negatives,inputs=inputs,products=products)
    (out/'report.json').write_bytes(canonical(report))
    print(json.dumps(dict(result='PASS',graphs=len(graphs),scenarios=4,negative_cases=len(negatives),
                         budgets=[dict(graph=x['graph'],**x['budget']) for x in reports],output=str(out)),ensure_ascii=False))
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=ROOT)
    parser.add_argument('--out',type=Path,default=Path('work/Melodydt/151/h1/evidence'))
    parser.add_argument('--source-commit',default='UNCOMMITTED_LOCAL',help='actual uploaded checker/input commit; no Git checkout inferred')
    args=parser.parse_args()
    try:
        check_all(args.root.resolve(), args.root.resolve()/args.out, args.source_commit)
    except (Reject, KeyError, IndexError, struct.error) as e:
        print('REJECT: '+str(e),file=sys.stderr);return 2
    return 0


if __name__=='__main__':
    raise SystemExit(main())
