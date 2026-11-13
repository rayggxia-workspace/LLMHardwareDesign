from copy import deepcopy
import random
import unittest

from cover_frontier import search
from event_execution import Model
from verify_cover_frontier import verify


def binding(name, *stages):
    return {'id': name, 'site': 'P0', 'ticks': 1, 'resources': [], 'nets': [],
            'scratch_words': 0, 'event_stages': stages}


def stage(service, *, inputs=None, outputs=None, policy='any'):
    return {'service': service, 'inputs': inputs or {}, 'outputs': outputs or {}, 'input_policy': policy}


def task(name, *bindings, after=()):
    return {'id': name, 'after': after, 'bindings': bindings}


def hardware(*, resident=True):
    def window(site, offset):
        return {'site': site, 'offset': offset, 'bytes': 16}

    def route(src, dst, *claims):
        return {'src': src, 'dst': dst, 'setup': 2, 'bytes_per_tick': 8, 'claims': dict.fromkeys(claims, 1)}

    resources = dict.fromkeys(('M0', 'M1', 'S0', 'S1', 'DDR.bus', 'DDR.credit'), 1)
    routes = {
        'S0-to-DDR': route('P0', 'DDR', 'S0', 'DDR.bus', 'DDR.credit'),
        'DDR-to-S1': route('DDR', 'P1', 'S1', 'DDR.bus', 'DDR.credit'),
        'DDR-to-S0': route('DDR', 'P0', 'S0', 'DDR.bus', 'DDR.credit'),
    }
    if resident:
        routes['direct'] = {**route('P0', 'P1', 'S0', 'S1'), 'nets': ['P0-P1']}
    return {
        'resources': resources,
        'sites': {p: {'words': 2, 'bytes': 32} for p in ('P0', 'P1')},
        'nets': {'P0-P1': {'cost': 1}},
        'event_model': {
            'kind': 'qualified-event-model-v1',
            'windows': {'source': window('P0', 0), 'other': window('P0', 16),
                        'input': window('P1', 0), 'result': window('P1', 16)},
            'value_bytes': dict.fromkeys(('x', 'y', 'z'), 16),
            'services': {
                'produce': {'ticks': 5, 'claims': {'M0': 1, 'S0': 1}},
                'consume': {'ticks': 3, 'claims': {'M1': 1, 'S1': 1}},
                'slow-resident': {'ticks': 6, 'claims': {'M1': 1, 'S1': 1}},
                'block-source': {'ticks': 30, 'claims': {'S0': 1}},
                'wait-credit': {'ticks': 10, 'claims': {'DDR.credit': 1}},
            },
            'routes': routes, 'live_out': ['y'],
        },
    }


class EventExecutionTest(unittest.TestCase):
    def test_same_candidate_reprices_local_copy_and_store_load(self):
        a = task('a', binding('producer', stage('produce', outputs={'source': 'x'})))
        b = task('b', binding('consumer', stage('consume', inputs={'input': 'x'},
                                               outputs={'result': 'y'})), after=('a',))
        for resident, makespan, traffic in ((True, 12, 0), (False, 16, 16)):
            with self.subTest(resident=resident):
                h = hardware(resident=resident)
                plan = search([a, b], h)
                verify([a, b], h, (), plan)
                self.assertEqual(plan['makespan'], makespan)
                self.assertEqual((plan['external_read_bytes'], plan['external_write_bytes']),
                                 (traffic, traffic))
                if resident:
                    constrained = search([a, b], h, wire_budget=0)
                    self.assertEqual(constrained['makespan'], 16)
                    verify([a, b], h, (), constrained, wire_budget=0)

    def test_booked_ddr_credit_changes_same_future_move(self):
        h = hardware(resident=False)
        h['event_model']['initial_backing'] = ['x']
        model = Model(h)
        b = binding('b', stage('consume', inputs={'input': 'x'}, outputs={'result': 'y'}))
        holding, _ = model.expand(model.initial, binding('wait', stage('wait-credit')), 0, set())
        warm, events = model.expand(model.initial, b, 0, set())
        delayed, later = model.expand(holding, b, 0, set())
        self.assertEqual((events[0]['start'], later[0]['start']), (0, 10))
        self.assertEqual((warm.read_bytes, delayed.read_bytes), (16, 16))

    def test_source_kept_until_copy_ack_and_spilled_before_overwrite(self):
        h = hardware()
        h['event_model']['initial_copies'] = {'source': 'x'}
        model = Model(h)
        b = binding('b', stage('consume', inputs={'input': 'x'}, outputs={'result': 'y'}))
        copying, events = model.expand(model.initial, b, 0, set())
        store = binding('replace', stage('produce', outputs={'source': 'z'}))
        after, moves = model.expand(copying, store, 0, set())
        self.assertEqual(moves[0]['start'], events[0]['end'])
        self.assertEqual(after.write_bytes, 0)
        after, moves = model.expand(model.initial, store, 0, {'x'})
        self.assertEqual([m['kind'] for m in moves], ['move', 'stage'])
        self.assertEqual(after.write_bytes, 16)
        self.assertEqual(after.backing['x'], 4)

    def test_verifier_rejects_wrong_data_ack_traffic_and_resource_overlap(self):
        h = hardware()
        h['event_model']['initial_copies'] = {'source': 'x'}
        a = task('a', binding('copy', stage('consume', inputs={'input': 'x'}, outputs={'result': 'y'})))
        b = task('b', binding('busy', stage('block-source')))
        plan = search([a, b], h, width=8)
        verify([a, b], h, (), plan)
        for field, replacement, message in (
            ('value', 'z', 'custody'), ('end', 3, 'duration'), ('route', 'S0-to-DDR', 'endpoints'),
        ):
            tampered = deepcopy(plan)
            row = next(r for r in tampered['tasks'] if r['id'] == 'a')
            row['evaluation']['events'][0][field] = replacement
            with self.assertRaisesRegex(ValueError, message):
                verify([a, b], h, (), tampered)
        bad = deepcopy(plan)
        row = next(r for r in bad['tasks'] if r['id'] == 'b')
        row['start'], row['end'] = 0, 30
        row['evaluation']['events'][0].update(start=0, end=30)
        with self.assertRaisesRegex(ValueError, 'resource capacity'):
            verify([a, b], h, (), bad)

    def test_same_pool_beam_preserves_better_resident_alternative(self):
        h = hardware()
        produce = task('a',
                       binding('quick', stage('produce', outputs={'source': 'x'})),
                       binding('on-destination', stage('slow-resident', outputs={'input': 'x'})))
        consume = task('b', binding('consume', stage('consume', inputs={'input': 'x'},
                                                    outputs={'result': 'y'})), after=('a',))
        greedy = search([produce, consume], h, width=1)
        beam = search([produce, consume], h, width=4, backbone=greedy)
        for plan in (greedy, beam):
            verify([produce, consume], h, (), plan)
        self.assertEqual((greedy['makespan'], beam['makespan']), (12, 9))

    def test_shared_resource_capacity_holes_are_not_tail_only(self):
        h = hardware()
        h['resources']['DDR.credit'] = 2
        m = Model(h)
        first, a, b = m.book(m.initial, {'DDR.credit': 2}, 20, 5)
        second, c, d = m.book(first, {'DDR.credit': 1}, 0, 10)
        _, e, f = m.book(second, {'DDR.credit': 2}, 7, 12)
        self.assertEqual((a, b, c, d, e, f), (20, 25, 0, 10, 25, 37))

    def test_calendar_matches_independent_tick_reference(self):
        for seed in range(32):
            rng = random.Random(seed)
            h = hardware()
            h['resources'].update({'DDR.bus': 3, 'DDR.credit': 2})
            model = Model(h)
            state = model.initial
            timeline = {r: [0]*160 for r in ('DDR.bus', 'DDR.credit')}
            for _ in range(25):
                claims = {r: rng.randrange(h['resources'][r]+1) for r in timeline}
                claims = {r: n for r, n in claims.items() if n}
                ticks, ready = rng.randint(1, 5), rng.randint(0, 26)
                expected = next(at for at in range(ready, 155) if all(
                    max(timeline[r][at:at+ticks])+n <= h['resources'][r] for r, n in claims.items()))
                state, start, end = model.book(state, claims, ready, ticks)
                self.assertEqual(start, expected, seed)
                for r, n in claims.items():
                    for at in range(start, end):
                        timeline[r][at] += n

    def test_issue_data_and_ack_hold_credit_across_channel_wait(self):
        h = hardware(resident=False)
        h['resources']['issue'] = 1
        spec = h['event_model']
        spec['initial_backing'] = ['x']
        spec['routes']['DDR-to-S1'].update(
            claims={'DDR.bus': 1},
            phases={'issue': {'ticks': 2, 'claims': {'issue': 1}},
                    'ack': {'ticks': 1, 'claims': {'S1': 1}}, 'hold_claims': {'DDR.credit': 1}},
        )
        spec['services']['bus'] = {'ticks': 10, 'claims': {'DDR.bus': 1}}
        a = task('a', binding('bus', stage('bus')))
        b = task('b', binding('read', stage('consume', inputs={'input': 'x'}, outputs={'result': 'y'})))
        plan = search([a, b], h, width=1)
        verify([a, b], h, (), plan)
        self.assertEqual(plan['tasks'][0]['id'], 'a')
        move = plan['tasks'][1]['evaluation']['events'][0]
        self.assertEqual([(p['start'], p['end']) for p in move['phases']], [(0, 2), (10, 14), (14, 15)])
        self.assertEqual(plan['external_read_bytes'], 16)
        bad = deepcopy(plan)
        bad['tasks'][1]['evaluation']['events'][0]['phases'][1].update(start=9, end=13)
        with self.assertRaisesRegex(ValueError, 'resource capacity'):
            verify([a, b], h, (), bad)

    def test_does_not_discard_wired_route_in_full_graph(self):
        h = hardware()
        spec = h['event_model']
        h['nets']['preferred-now'] = {'cost': 1}
        spec['routes']['preferred-now'] = {**spec['routes']['direct'], 'setup': 0,
                                          'nets': ['preferred-now']}
        spec['services']['final'] = {**spec['services']['consume'], 'nets': ['P0-P1']}
        spec['value_bytes'].update({f'x{i}':16 for i in range(36)})
        tasks = []
        for i in range(36):
            make, use = f'make{i}', f'use{i}'
            tasks.append(task(make, binding('make', stage('produce', outputs={'source':f'x{i}'})),
                              after=(f'use{i-1}',) if i else ()))
            output = {'result':'y'} if i == 35 else None
            tasks.append(task(use, binding('use', stage('final' if i == 35 else 'consume',
                                                       inputs={'input':f'x{i}'}, outputs=output)), after=(make,)))
        plan = search(tasks, h, width=8, wire_budget=1)
        self.assertTrue(verify(tasks,h,(),plan,wire_budget=1)['passed'])
        self.assertEqual(plan['nets'], ['P0-P1'])
        self.assertEqual(plan['makespan'], 36*12)

    def test_ddr_credit_uses_window_after_phase_wait_shrinks(self):
        h = hardware(resident=False)
        h['resources']['issue'] = 1
        h['event_model']['initial_backing'] = ['x']
        h['event_model']['routes']['DDR-to-S1'].update(
            claims={'DDR.bus':1},
            phases={'issue':{'ticks':2,'claims':{'issue':1}}, 'ack':{'ticks':1,'claims':{'S1':1}},
                    'hold_claims':{'DDR.credit':1}})
        model = Model(h)
        for first_end in (8,12,16):
            for gap in (8,9,10):
                for second_duration in (6,8,10):
                    state, _, _ = model.book(model.initial, {'DDR.credit':1}, 0, first_end)
                    state, _, _ = model.book(state, {'DDR.credit':1}, first_end+gap, second_duration)
                    state, _, _ = model.book(state, {'DDR.bus':1}, 0, first_end+1)
                    _, event = model.move(state, 'x', 'DDR', 'input', 0, 'DDR-to-S1')
                    self.assertEqual((event['start'],event['end']), (first_end,first_end+7))

    def test_full_36_layer_route_and_compute_capacity(self):
        h = hardware()
        spec = h['event_model']
        h['nets']['fast'] = {'cost': 1}
        h['resources']['compute-credit'] = 2
        spec['routes']['fast'] = {**spec['routes']['direct'], 'setup': 0, 'nets': ['fast']}
        spec['services'].update(
            left={'ticks': 8, 'claims': {'M0': 1, 'compute-credit': 1}},
            right={'ticks': 8, 'claims': {'M1': 1, 'compute-credit': 1}},
            join={'ticks': 8, 'claims': {'M1': 1, 'S1': 1}},
            terminal={'ticks': 8, 'claims': {'M1': 1, 'S1': 1}, 'nets': ['P0-P1']},
        )
        tasks = []
        for layer in range(36):
            source = f'x{layer}'
            left, right, join = f'left{layer}', f'right{layer}', f'join{layer}'
            parents = (f'join{layer-1}',) if layer else ()
            spec['value_bytes'][source] = 16
            tasks.extend((
                task(left, binding(left, stage('left', outputs={'source': source})), after=parents),
                task(right, binding(right, stage('right')), after=parents),
                task(join, binding(join, stage('terminal' if layer == 35 else 'join',
                     inputs={'input': source}, outputs={'result': 'y'} if layer == 35 else None)),
                     after=(left, right)),
            ))
        for capacity, expected in ((2, 720), (1, 1008)):
            with self.subTest(capacity=capacity):
                h['resources']['compute-credit'] = capacity
                plan = search(tasks, h, width=8, wire_budget=1)
                self.assertEqual(plan['makespan'], expected)
                self.assertEqual(plan['nets'], ['P0-P1'])
                self.assertEqual((plan['external_read_bytes'], plan['external_write_bytes']), (0, 0))
                self.assertTrue(verify(tasks, h, (), plan, wire_budget=1)['passed'])

    def test_complete_stage_cost_and_parallel_credit_limit(self):
        h = hardware()
        spec = h['event_model']
        spec['initial_copies'] = {'source':'x'}
        spec['initial_backing'] = ['x']
        h['resources']['credit'] = 2
        h['resources']['independent'] = 1
        spec['services'].update(
            slow={'ticks':20,'claims':{'independent':1, 'credit':1}},
            consume={'ticks':3,'claims':{'M1':1, 'S1':1, 'credit':1}},
        )
        spec['routes']['direct']['setup'] = 7
        left = dict(stage('slow'), id='left')
        right = dict(stage('consume', inputs={'input':'x'}, outputs={'result':'y'}), id='right')
        parallel = binding('parallel', left, right)
        tasks = [task('pair',parallel)]
        plan = search(tasks,h)
        verify(tasks,h,(),plan)
        self.assertEqual(plan['makespan'],20)

        right['after'] = ['left']
        h['resources']['credit'] = 1
        serial = search(tasks,h)
        verify(tasks,h,(),serial)
        self.assertEqual(serial['makespan'],27)

        # A second input gates the same stage. The early DDR arrival buys no time.
        spec['initial_copies']['other'] = 'z'
        spec['initial_backing'].append('z')
        spec['windows']['z_in'] = {'site':'P1','offset':32,'bytes':16}
        h['sites']['P1']['bytes'] = 48
        spec['windows']['other']['site'] = 'P2'
        spec['windows']['other']['offset'] = 0
        h['sites']['P2'] = {'words':1,'bytes':16}
        spec['routes']['z_onchip'] = {'src':'P2','dst':'P1','setup':20,'bytes_per_tick':8,
                                     'claims':{'independent':1}}
        # The hardware serves this value only on its dedicated on-chip path.
        spec['initial_backing'].remove('z')
        right['inputs']['z_in'] = 'z'
        right.pop('after')
        tasks = [task('pair',binding('only-right',right))]
        plan = search(tasks,h,width=None,ready_limit=None)
        verify(tasks,h,(),plan)
        self.assertEqual((plan['makespan'],plan['external_read_bytes']), (25,0))
        plan['tasks'][0]['site'] = 'INVALID-P999'
        with self.assertRaisesRegex(ValueError,'dispatch site'):
            verify(tasks,h,(),plan)

    def test_dominance_keeps_less_traffic_when_later_work_hides_time_lead(self):
        h = hardware()
        h['event_model']['live_out'] = []
        h['event_model']['services'].update({
            'fast':{'ticks':2,'claims':{'DDR.bus':1},'read_bytes':16},
            'slow-start':{'ticks':2,'claims':{'DDR.bus':1}},
            'slow-finish':{'ticks':3,'claims':{}},
            'critical':{'ticks':10,'claims':{'M1':1}},
        })
        a = task('a',binding('fast',stage('fast')),binding('slow',stage('slow-start'),stage('slow-finish')))
        for candidate in a['bindings']:
            candidate['ticks'] = 2
        tasks = [a,task('b',binding('critical',stage('critical')))]
        plan = search(tasks,h,width=None,ready_limit=1)
        verify(tasks,h,(),plan)
        self.assertEqual((plan['makespan'],plan['external_read_bytes']), (10,0))


if __name__ == '__main__':
    unittest.main()
