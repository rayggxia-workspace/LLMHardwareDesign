import os
import struct
import unittest
from copy import deepcopy

from event_control_replay import execute
from run import compile_event_graph, compile_event_ir, retry_event_graph
from test_event_execution import binding, hardware, stage, task


FMT = {'shape': [8], 'dtype': 'INT16', 'format': {'bits': 16, 'exponent': 0, 'lanes': 8}}


def fixture(layers):
    model = {'inputs': ['x', 'a0'], 'outputs': [f'a{layers}'], 'tasks': [], 'values': {}}
    h = hardware()
    h['topology_id'] = 7
    h['sites']['P1']['bytes'] = 48
    spec = h['event_model']
    spec['windows']['acc'] = {'site': 'P1', 'offset': 32, 'bytes': 16}
    spec['initial_copies'] = {'other': 'x', 'acc': 'a0'}
    spec['value_bytes'] = {}
    spec['routes'] = {
        'direct': {**spec['routes']['direct'], 'setup': 1},
        'local0': {'src': 'P0', 'dst': 'P0', 'setup': 1, 'bytes_per_tick': 16, 'claims': {'S0': 1}},
        'local1': {'src': 'P1', 'dst': 'P1', 'setup': 1, 'bytes_per_tick': 16, 'claims': {'S1': 1}},
    }
    h['nets']['P0-P1']['signals'] = [
        {'name': 'data', 'width': 128, 'driver': 'P0.data[{bit}]', 'sinks': ['P1.data[{bit}]']},
        {'name': 'valid', 'width': 1, 'driver': 'P0.valid', 'sinks': ['P1.valid']},
        {'name': 'ready', 'width': 1, 'driver': 'P1.ready', 'sinks': ['P0.ready']},
        {'name': 'ack', 'width': 1, 'driver': 'P1.ack', 'sinks': ['P0.ack']},
    ]
    spec['services']['increment'] = {**spec['services']['produce'], 'control_site': 'P0'}
    spec['services']['add'] = {**spec['services']['consume'], 'control_site': 'P1'}
    spec['recipes'] = [
        {'op': 'Increment', 'inputs': [FMT], 'outputs': [FMT],
         'binding': {'id': 'P0.increment', 'site': 'P0', 'event_stages': [
             {'service': 'increment', 'inputs': {'other': 'in:0'}, 'outputs': {'source': 'out:0'}}]}},
        {'op': 'Add', 'inputs': [FMT, FMT], 'outputs': [FMT],
         'binding': {'id': 'P1.add', 'site': 'P1', 'event_stages': [
             {'service': 'add', 'inputs': {'input': 'in:0', 'acc': 'in:1'}, 'outputs': {'result': 'out:0'}}]}},
    ]
    names = {'x', 'a0'}
    for n in range(1, layers+1):
        names.update((f't{n}', f'a{n}'))
        model['tasks'].extend([
            {'id': f'map{n:02}', 'op': 'Increment',
             'inputs': ['x' if n == 1 else f't{n-1}'], 'outputs': [f't{n}']},
            {'id': f'sum{n:02}', 'op': 'Add', 'inputs': [f't{n}', f'a{n-1}'], 'outputs': [f'a{n}']},
        ])
    model['values'] = {name: FMT for name in sorted(names)}
    return model, h


def words(value):
    return struct.unpack('<8h', value)


def pack(values):
    return struct.pack('<8h', *values)


def compute(service, data):
    if service == 'increment':
        return [pack([value+1 for value in words(data[0])])]
    if service == 'add':
        return [pack([a+b for a,b in zip(words(data[0]),words(data[1]))])]
    raise ValueError('unregistered independent arithmetic')


def native_fixture(layers):
    """Repeated real-ABI Add/Mul, with a different transferred tensor per layer."""
    sites = ('U0.S', 'U1.S')
    model = {'inputs': ['x','c0','c1'], 'outputs': [f'v{layers}'], 'tasks': [], 'values': {}}
    h = {'topology_id': 0x01930010, 'abi_id': 0x01930001, 'sites': {}, 'resources': {},
         'control_groups': {}, 'nets': {},
         'event_model': {'kind':'qualified-event-model-v1', 'windows':{}, 'services':{}, 'routes':{},
                         'recipes': [], 'initial_copies': {'u0.in':'x', 'u0.const':'c0', 'u1.const':'c1'},
                         'native_control': {'profile':'pr214-u64-native-subset', 'block_type':0,
                             'assembler_sha256':'dade4e16514634367195c5a6e996636d13c26b5eff2f5503ea1018d43aab1ca2',
                             'native_opcodes':{'COMMAND':0x100,'SEND':0x101,'RECEIVE':0x102,'RESERVE':0x103}}}}
    spec = h['event_model']
    for n, site in enumerate(sites):
        group = f'U{n}'
        h['control_groups'][group] = {'site':site, 'block_id':n}
        h['sites'][site] = {'bytes':16384, 'words':1024}
        for name, index in (('const',40),('in',42),('out',43)):
            spec['windows'][f'u{n}.{name}'] = {'site':site, 'offset':index*16, 'bytes':16}
        e, port = f'{group}.E', f'{group}.S.port'
        h['resources'].update({e:1,port:1})
        operation = ('Add','Mul')[n]
        service = group+'.'+operation
        spec['services'][service] = {'ticks':5, 'claims':{e:1,port:1}, 'control_site':site,
                                     'native_e':{'op':2*n,'shift':0}}
        spec['recipes'].append({'op':operation, 'domain':'llmhardware.native', 'inputs':[FMT,FMT],
                                'outputs':[FMT], 'binding':{'id':service,'site':site,'event_stages':[
            {'service':service, 'inputs':{f'u{n}.in':'in:0',f'u{n}.const':'in:1'},
             'outputs':{f'u{n}.out':'out:0'}}]}})
        other = 1-n
        route = f'U{n}->U{other}'
        h['nets'][route] = {'cost':1,'fixed':True}
        spec['routes'][route] = {'src':site,'dst':sites[other], 'setup':2,'bytes_per_tick':16,
                                'claims':{port:1,f'U{other}.S.port':1}, 'nets':[route],
                                'native_transport':'u64-stored-link'}
    for i in range(1, layers+1):
        add = i % 2 == 1
        model['tasks'].append({'id':f'layer{i:02}', 'op':'Add' if add else 'Mul',
                              'domain':'llmhardware.native', 'inputs':[
                                  'x' if i == 1 else f'v{i-1}', 'c0' if add else 'c1'],
                              'outputs':[f'v{i}']})
    model['values'] = {name:FMT for name in (*model['inputs'], *(f'v{i}' for i in range(1,layers+1)))}
    return model,h


def direct_control_fabric(groups):
    fabric = {'schema_version': 'block-event-control-fabric/1', 'mother': 'MC',
              'targets': {}, 'bundles': {}}
    for number, group in enumerate(groups):
        local, name = group + '.LC', 'control.' + group
        fabric['targets'][group] = {'target_id': number, 'controller': local, 'bundles': [name]}
        fabric['bundles'][name] = {'cost': 1, 'signals': [
            {'name': 'command', 'role': 'command', 'width': 1,
             'driver': f'MC/cmd{number}', 'sinks': [local + '/cmd']},
            {'name': 'done', 'role': 'done', 'width': 1,
             'driver': local + '/done', 'sinks': [f'MC/done{number}']},
        ]}
    return fabric


class EventCompilerTest(unittest.TestCase):
    def test_control_pin_conflict_prunes_only_the_incompatible_combination(self):
        h = hardware()
        spec = h['event_model']
        spec['live_out'] = ['x', 'y']
        spec['services']['produce']['control_site'] = 'P0'
        spec['services']['consume']['control_site'] = 'P1'
        spec['services']['slow'] = {'ticks': 12, 'claims': {'M0': 1}, 'control_site': 'P0'}
        fast = {**binding('fast', stage('consume', outputs={'result': 'y'})), 'site': 'P1'}
        graph = {'tasks': [
            task('a', binding('first', stage('produce', outputs={'source': 'x'}))),
            task('b', fast, binding('slow', stage('slow', outputs={'other': 'y'})), after=('a',)),
        ]}
        fabric = direct_control_fabric(('P0', 'P1'))
        conflicting = deepcopy(fabric)
        conflicting['bundles']['control.P1']['signals'][1]['sinks'] = ['MC/done0']
        for width in (1, 8):
            direct = compile_event_ir(graph, h, control_fabric=fabric, width=width)
            mapped = compile_event_ir(graph, h, control_fabric=conflicting, width=width)
            self.assertEqual(direct['plan']['tasks'][-1]['binding'], 'fast')
            self.assertEqual(mapped['plan']['tasks'][-1]['binding'], 'slow')
            self.assertEqual(mapped['outputs']['control_connectivity']['targets'], {'P0': 0})

    def test_router_feedback_accepts_selected_control_dependency(self):
        from event_handoff_acceptance import fixture as alternative_targets

        graph, h = alternative_targets()
        fabric = direct_control_fabric(('U0', 'U1'))
        fabric['bundles']['control.U0']['requires'] = ['control.credit']
        fabric['bundles']['control.credit'] = {'cost': 1, 'signals': [
            {'name': 'credit', 'width': 1, 'driver': 'MC/credit', 'sinks': ['U0.LC/credit']},
        ]}
        for width in (1, 8):
            before = compile_event_graph(graph, h, control_fabric=fabric, width=width, budget=3)
            outputs = before['outputs']
            self.assertEqual(outputs['control_connectivity']['targets'], {'U0': 0})
            self.assertNotIn('control.credit', outputs['wiring']['users'])
            self.assertEqual(len(outputs['control_connectivity']['users']['control.credit']), 36)
            feedback = {'source': outputs['wiring']['source'], 'trial_exclude': ['control.credit']}
            after = retry_event_graph(graph, h, before, feedback, width=width, budget=3)
            self.assertEqual(after['outputs']['control_connectivity']['targets'], {'U1': 1})
            self.assertEqual(set(after['outputs']['program']['locals']), {'U1'})

    def test_feedback_preserves_data_catalog_requirements(self):
        from event_handoff_acceptance import fixture as alternative_targets

        graph, h = alternative_targets()
        h['nets']['enable'] = {'cost': 1, 'signals': [
            {'name': 'enable', 'width': 1, 'driver': 'IO/enable', 'sinks': ['U1/enable']},
        ]}
        catalog = {'schema_version': 'route-contract/1',
                   'demands': {'U1.N_to_E': {'requires': ['enable']}}}
        fabric = direct_control_fabric(('U0', 'U1'))
        for width in (1, 8):
            first = compile_event_graph(graph, h, control_fabric=fabric, route_catalog=catalog,
                                        width=width, budget=2)
            feedback = {'source': first['outputs']['wiring']['source'], 'trial_exclude': ['control.U0']}
            blocked = retry_event_graph(graph, h, first, feedback, width=width)
            self.assertNotEqual(blocked['status'], 'planned')
            rerouted = retry_event_graph(graph, h, first, feedback, width=width, budget=3)
            self.assertEqual(rerouted['plan']['wire_cost'], 3)
            self.assertEqual(rerouted['outputs']['control_connectivity']['targets'], {'U1': 1})
            wiring = rerouted['outputs']['wiring']
            self.assertIn(['U1.N_to_E', 'enable'], wiring['dependencies'])
            self.assertIn('enable', {member['demand_id'] for member in wiring['members']})
            with self.assertRaisesRegex(ValueError, 'route catalog conflicts'):
                retry_event_graph(graph, h, first, feedback, width=width, budget=3, route_catalog={
                    'schema_version': 'route-contract/1', 'demands': {'U1.N_to_E': {'requires': []}},
                })
            falsified = deepcopy(first)
            falsified['outputs']['wiring']['users']['control.U1'] = []
            with self.assertRaisesRegex(ValueError, 'selected demand IDs'):
                retry_event_graph(graph, h, falsified, {**feedback, 'trial_exclude': ['control.U1']},
                                  width=width, budget=3)

    def test_combined_demands_reject_control_and_data_pin_conflict(self):
        graph, h = fixture(2)
        fabric = direct_control_fabric(('P0', 'P1'))
        data = h['nets']['P0-P1'].pop('signals')
        data[1]['sinks'] = ['P1.LC/cmd']
        catalog = {'schema_version': 'route-contract/1', 'demands': {'P0-P1': {'signals': data}}}
        for width in (1, 8):
            blocked = compile_event_graph(graph, h, control_fabric=fabric, route_catalog=catalog, width=width)
            self.assertNotEqual(blocked['status'], 'planned')
            data[1]['sinks'] = ['P1/valid']
            good = compile_event_graph(graph, h, control_fabric=fabric, route_catalog=catalog, width=width)
            self.assertTrue(good['verification']['passed'])
            data[1]['sinks'] = ['P1.LC/cmd']
        catalog['demands']['control.P0'] = {'requires': ['P0-P1']}
        with self.assertRaisesRegex(ValueError, 'changes the declared control bundle'):
            compile_event_graph(graph, h, control_fabric=fabric, route_catalog=catalog)
        del catalog['demands']['control.P0']
        data[1]['sinks'] = ['P1/valid']
        h['nets']['unbound'] = {'cost': 1}
        catalog['demands']['P0-P1']['requires'] = ['unbound']
        incomplete = compile_event_graph(graph, h, control_fabric=fabric, route_catalog=catalog)
        self.assertEqual(incomplete['outputs']['wiring']['status'], 'unbound')
        self.assertEqual(incomplete['outputs']['wiring']['unresolved'], [
            {'demand_id': 'unbound', 'reason': 'missing_interface_template'},
        ])

    def test_control_fabric_binds_selected_groups_and_shares_physical_signal_names(self):
        model, h = fixture(36)
        h['control_groups'] = {'P0': {'site': 'P0'}, 'U0': {'site': 'P1'}}
        for data_width, beam in ((128, 1), (512, 8)):
            with self.subTest(data_width=data_width, beam=beam):
                fabric = {'schema_version': 'block-event-control-fabric/1', 'mother': 'MC',
                          'targets': {}, 'bundles': {}}
                bundles = fabric['bundles']
                bundles['shared'] = {'cost': 1, 'signals': [
                    {'name': 'done', 'role': 'done', 'width': data_width,
                     'driver': 'relay/return[{bit}]', 'sinks': ['MC/return[{bit}]']}]}
                for number, group in enumerate(('P0', 'U0', 'C0', 'F0', 'J0')):
                    local = group + '.LC'
                    bundle = 'dispatch.' + group
                    fabric['targets'][group] = {'target_id': number, 'controller': local, 'bundles': [bundle]}
                    bundles[bundle] = {'cost': 1, 'requires': ['shared'], 'signals': [
                        {'name': 'command', 'role': 'command', 'width': data_width,
                         'driver': 'MC/task[{bit}]', 'sinks': [local + '/task[{bit}]']},
                        {'name': 'done', 'role': 'done', 'width': data_width,
                         'driver': local + '/event[{bit}]', 'sinks': [f'relay/event{number}[{{bit}}]']},
                        {'name': 'ready', 'width': 1,
                         'driver': local + '/ready', 'sinks': [f'relay/ready{number}']}]}
                result = compile_event_graph(model, h, control_fabric=fabric, budget=4, width=beam)
                outputs = result['outputs']
                self.assertTrue(result['verification']['passed'])
                self.assertEqual(result['plan']['wire_cost'], 4)
                connectivity = outputs['control_connectivity']
                self.assertEqual(connectivity['source'], outputs['program']['source'])
                self.assertEqual(connectivity['targets'], {'P0': 0, 'U0': 1})
                self.assertEqual(connectivity['controllers'], {'P0': 'P0.LC', 'U0': 'U0.LC'})
                self.assertEqual(len(connectivity['users']['shared']), len(outputs['program']['mother']) - 1)
                self.assertEqual(len(connectivity['nets']), 4 * data_width + 2)
                bits = {net['driver']: net['sinks'] for net in connectivity['nets']}
                self.assertEqual(bits['MC/task[0]'], ['P0.LC/task[0]', 'U0.LC/task[0]'])
                self.assertNotIn('dispatch.C0', outputs['wiring']['users'])
                self.assertNotEqual(compile_event_graph(model, h, control_fabric=fabric, budget=3,
                                                        width=beam)['status'], 'planned')
                wrong = deepcopy(fabric)
                del wrong['targets']['U0']
                blocked = compile_event_graph(model, h, control_fabric=wrong, budget=4, width=beam)
                self.assertNotEqual(blocked['status'], 'planned')
                self.assertIn('U0', blocked['logical_control_issues']['services']['add'])
                wrong = deepcopy(fabric)
                wrong['bundles']['shared']['signals'][0]['role'] = 'command'
                with self.assertRaisesRegex(ValueError, 'no declared done path'):
                    compile_event_graph(model, h, control_fabric=wrong, budget=4, width=beam)
                wrong = deepcopy(fabric)
                wrong['bundles']['dispatch.U0']['signals'][-1]['sinks'] = ['relay/ready0']
                blocked = compile_event_graph(model, h, control_fabric=wrong, budget=4, width=beam)
                self.assertNotEqual(blocked['status'], 'planned')

    def test_whole_graph_control_and_wire_reuse_with_delayed_ack(self):
        model, h = fixture(36)
        result = compile_event_graph(model, h, budget=1, width=8)
        self.assertTrue(result['verification']['passed'])
        self.assertEqual(result['plan']['covered_original_tasks'], 72)
        outputs = result['outputs']
        wiring, program = outputs['wiring'], outputs['program']
        self.assertEqual(wiring['source'], program['source'])
        self.assertEqual(len(wiring['members']), 131)
        self.assertEqual(len(wiring['users']['P0-P1']), 36)
        initial = {'x': pack(range(8)), 'a0': pack([0]*8)}
        replay = execute(program, result['resolved_hardware'], initial, compute,
                         ack_delay=lambda number, command: number % 5)
        self.assertEqual(words(replay['values']['a36']), tuple(36*value + 666 for value in range(8)))
        self.assertEqual(len(replay['events']), 2*(len(program['mother'])-1))

        wrong = deepcopy(program)
        wrong['mother'][0]['targets'] = ['P999']
        with self.assertRaisesRegex(ValueError, 'target'):
            execute(wrong, result['resolved_hardware'], initial, compute)
        wrong = deepcopy(program)
        transfer = wiring['users']['P0-P1'][-1]['event_id']
        for commands in wrong['locals'].values():
            for command in commands:
                if command['sequence'] == transfer:
                    command['required_completion'] = 'source_sent'
        with self.assertRaisesRegex(ValueError, 'must be ACK'):
            execute(wrong, result['resolved_hardware'], initial, compute)

    def test_fixed_topology_and_router_feedback_change_one_source_plan(self):
        model, h = fixture(8)
        h['nets']['P0-P1']['fixed'] = True
        first = compile_event_graph(model, h, budget=0, width=8)
        original = h['event_model']['routes'].pop('direct')
        h['event_model']['routes']['alt'] = {**original, 'nets': ['alternative']}
        h['nets']['alternative'] = {**h['nets'].pop('P0-P1'), 'fixed': False}
        second = compile_event_graph(model, h, budget=1, width=8)
        initial = {'x': pack(range(8)), 'a0': pack([0]*8)}
        for item, net in ((first, 'P0-P1'), (second, 'alternative')):
            out = item['outputs']
            self.assertEqual(list(out['wiring']['users']), [net])
            self.assertEqual(len(out['wiring']['users'][net]), 8)
            replay = execute(out['program'], item['resolved_hardware'], initial, compute)
            self.assertEqual(words(replay['values']['a8']), tuple(8*value + 36 for value in range(8)))
        self.assertNotEqual(first['outputs']['program']['source'], second['outputs']['program']['source'])
        self.assertEqual(compile_event_graph(model, h, budget=0)['status'], 'no_plan_in_bounded_search')

    def test_indexed_gather_emits_only_requested_rows_and_checks_before_issue(self):
        h = hardware()
        spec = h['event_model']
        h['sites']['P1']['bytes'] = 80
        spec['initial_copies'] = {'input':'ids'}
        spec['weights_in_ddr'] = True
        spec['value_bytes'] = {}
        spec['windows']['result']['bytes'] = 48
        spec['indexed_gather'] = [{'id':'gather-P1','site':'P1','index_window':'input',
                                    'output_window':'result','address_bits':48,'bytes_per_tick':16,
                                    'setup_per_index':3,'claims':{'DDR.bus':1,'S1':1}}]
        fmt = {'bits':16,'lanes':8,'exponent':-17}
        model = {'inputs':['ids'],'weights':['table'],'outputs':['embedding'],
                 'values': {'table':{'shape':[4,8],'dtype':'INT16','format':fmt},
                            'ids':{'shape':[1,2],'dtype':'INT64'},
                            'embedding':{'shape':[1,2,8],'dtype':'INT16','format':fmt}},
                 'tasks':[{'id':'embed','op':'Gather','inputs':['table','ids'],'outputs':['embedding']}]}
        result = compile_event_graph(model,h)
        self.assertTrue(result['verification']['passed'])
        plan, program = result['plan'],result['outputs']['program']
        self.assertEqual((plan['makespan'],plan['external_read_bytes']), (8,32))
        self.assertEqual(program['locals']['P1'][0]['op'],'INDEXED_LOAD')
        external_reads = []
        contents = b''.join(pack(range(i,i+8)) for i in range(4))
        def table_slice(value,offset,length):
            external_reads.append((value,offset,length))
            return contents[offset:offset+length]
        replay = execute(program,result['resolved_hardware'],{'ids':struct.pack('<2q',-1,1)},
                         None,ack_delay=lambda *_:5,read_external=table_slice)
        self.assertEqual(replay['values']['embedding'], contents[48:64]+contents[16:32])
        self.assertEqual(external_reads,[('table',48,16),('table',16,16)])
        self.assertEqual(replay['reference_ticks'],13)
        external_reads.clear()
        with self.assertRaisesRegex(ValueError,'index outside table'):
            execute(program,result['resolved_hardware'],{'ids':struct.pack('<2q',1,4)},
                    None,read_external=table_slice)
        self.assertFalse(external_reads)
        wrong = deepcopy(program)
        wrong['locals']['P1'][0]['indexed_read']['table_address'] += 16
        with self.assertRaisesRegex(ValueError,'command or table address'):
            execute(wrong,result['resolved_hardware'],{'ids':struct.pack('<2q',1,3)},
                    None,read_external=table_slice)

    def test_matmul_from_graph_selects_independent_column_stages(self):
        h = hardware(resident=False)
        spec = h['event_model']
        for site in h['sites'].values():
            site['bytes'] = 128
        spec['windows'] = {name: {'site':site, 'offset':16*index, 'bytes':16}
                           for site,names in (('P0',('x0','w0','left','local_right','remote_right','out')),
                                              ('P1',('x1','w1','right')))
                           for index,name in enumerate(names)}
        spec['initial_copies'] = {'x0':'x','x1':'x','w0':'w','w1':'w'}
        spec['value_bytes'] = {}
        h['resources']['compute-credit'] = 2
        spec['services'] = {
            'col0':{'ticks':12,'claims':{'M0':1,'S0':1,'compute-credit':1},'control_site':'P0'},
            'col1-P0':{'ticks':12,'claims':{'M0':1,'S0':1,'compute-credit':1},'control_site':'P0'},
            'col1-P1':{'ticks':12,'claims':{'M1':1,'S1':1,'compute-credit':1},'control_site':'P1'},
            'concat':{'ticks':4,'claims':{'S0':1},'control_site':'P0'},
        }
        spec['routes'] = {'p1-to-p0':{'src':'P1','dst':'P0','setup':2,'bytes_per_tick':8,
                                      'claims':{'S0':1,'S1':1},'nets':['P0-P1']}}
        x,w = {'shape':[1,2],'dtype':'INT16'},{'shape':[2,2],'dtype':'INT16'}
        model = {'inputs':['x','w'],'outputs':['y'],'values':{'x':x,'w':w,'y':x},'tasks':[
            {'id':'qk','op':'MatMul','domain':'llmhardware.native','inputs':['x','w'],'outputs':['y']}]}
        left = {'id':'left','service':'col0','inputs':{'x0':'in:0','w0':'in:1'},
                'outputs':{'left':'tmp:l'}}
        spec['recipes'] = []
        for location in (0,1):
            right = 'right' if location else 'local_right'
            merge_input = 'remote_right' if location else 'local_right'
            spec['recipes'].append({
                'op':'MatMul','domain':'llmhardware.native','inputs':[x,w],'outputs':[x],
                'binding':{'id':f'col1-P{location}','site':'P0','temporaries':{'l':2,'r':2},
                           'event_stages':[
                    left, {'id':'right','service':f'col1-P{location}',
                           'inputs':{f'x{location}':'in:0',f'w{location}':'in:1'},
                           'outputs':{right:'tmp:r'}},
                    {'id':'join','after':['left','right'],'service':'concat',
                     'inputs':{'left':'tmp:l',merge_input:'tmp:r'},'outputs':{'out':'out:0'}},
                ]}})
        initial = {'x':struct.pack('<2h',2,3),'w':struct.pack('<4h',5,7,11,13)}

        def multiply(service, data):
            if service == 'concat':
                return [b''.join(data)]
            col = 0 if service == 'col0' else 1
            a,b = struct.unpack('<2h',data[0])
            weights = struct.unpack('<4h',data[1])
            return [struct.pack('<h',a*weights[col]+b*weights[col+2])]

        for capacity,budget,ticks,chosen in ((2,1,19,'col1-P1'),(1,1,28,'col1-P0'),(2,0,28,'col1-P0')):
            h['resources']['compute-credit'] = capacity
            result = compile_event_graph(model,h,budget=budget)
            self.assertEqual((result['plan']['makespan'],result['plan']['tasks'][0]['binding']),(ticks,chosen))
            state = execute(result['outputs']['program'],result['resolved_hardware'],initial,multiply)
            self.assertEqual(struct.unpack('<2h',state['values']['y']),(43,53))

    def test_router_feedback_reemits_instructions_and_bit_demands(self):
        model,h = fixture(8)
        alt = 'P0-P1-alt'
        spec = h['event_model']
        h['nets'][alt] = deepcopy(h['nets']['P0-P1'])
        for signal in h['nets'][alt]['signals']:
            signal['driver'] += '_alt'
            signal['sinks'] = [pin+'_alt' for pin in signal['sinks']]
        spec['routes']['alternate'] = {**spec['routes']['direct'], 'setup':3, 'nets':[alt]}
        first = compile_event_graph(model,h,budget=1)
        feedback = {'source':first['outputs']['wiring']['source'], 'trial_exclude':['P0-P1']}
        second = retry_event_graph(model,h,first,feedback,budget=1)
        self.assertEqual(second['plan']['nets'],[alt])
        output = second['outputs']
        self.assertEqual(len(output['wiring']['users'][alt]),8)
        self.assertTrue(all(pin['driver'].endswith('_alt') for pin in output['wiring']['members']))
        self.assertTrue(any(command.get('route')=='alternate' for commands in output['program']['locals'].values()
                            for command in commands))
        state = execute(output['program'],second['resolved_hardware'],
                        {'x':pack(range(8)),'a0':pack([0]*8)},compute)
        self.assertEqual(words(state['values']['a8']),tuple(8*value+36 for value in range(8)))
        with self.assertRaisesRegex(ValueError,'does not match'):
            retry_event_graph(model,h,second,feedback,budget=1)

    def test_required_control_connection_uses_static_budget_once(self):
        model, h = fixture(8)
        h['nets']['control.dispatch'] = {'cost': 1}
        catalog = {'schema_version': 'route-contract/1', 'demands': {
            'P0-P1': {'requires': ['control.dispatch']},
            'control.dispatch': {'signals': [
                {'name': 'dispatch', 'width': 1, 'driver': 'mother.dispatch', 'sinks': ['P1.dispatch']},
            ]},
        }}
        for width in (1, 8):
            rejected = compile_event_graph(model, h, budget=1, width=width, route_catalog=catalog)
            self.assertEqual(rejected['status'], 'no_plan_in_bounded_search')
            planned = compile_event_graph(model, h, budget=2, width=width, route_catalog=catalog)
            self.assertEqual(planned['plan']['wire_cost'], 2)
            self.assertTrue(planned['verification']['passed'])
            self.assertEqual(len(planned['outputs']['wiring']['users']['P0-P1']), 8)

    @unittest.skipUnless(os.environ.get('LLMHD_EVENT_NATIVE_ASSEMBLER'), 'external locked native assembler')
    def test_official_native_assembler_encodes_whole_repeated_graph(self):
        from event_native_u import assemble_u64, compact_assembler_image, load_assembler

        model, h = native_fixture(16)
        result = compile_event_graph(model,h,budget=0)
        cap = h['event_model']['native_control']
        assembler = load_assembler(os.environ['LLMHD_EVENT_NATIVE_ASSEMBLER'], cap['assembler_sha256'])
        images = assemble_u64(result['outputs']['program'],result['resolved_hardware'],
                              assembler,compact_assembler_image)
        self.assertEqual(set(images), {'mother','local0','local1'})
        self.assertEqual([struct.unpack_from('<H', image, 8)[0] for image in images.values()], [2,2,2])
        self.assertEqual(sum(len(v) for v in result['outputs']['wiring']['users'].values()), 15)
        from solver import Unsupported
        model, h = native_fixture(36)
        too_large = compile_event_graph(model,h,budget=0)
        with self.assertRaisesRegex(Unsupported,'execution descriptors, capacity 32'):
            assemble_u64(too_large['outputs']['program'],too_large['resolved_hardware'],
                         assembler,compact_assembler_image)

    def test_missing_qualification_points_to_operator(self):
        model, h = fixture(2)
        model['tasks'][0]['op'] = 'Unregistered'
        result = compile_event_graph(model, h)
        self.assertEqual(result['status'], 'blocked_lowering')
        self.assertIn('map01: no qualified event recipe', result['reason'])
