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

    def test_stored_link_admits_aligned_words_and_falls_back_for_larger_values(self):
        from verify_event_execution import verify as verify_timeline

        tasks = [
            task('a', binding('producer', stage('produce', outputs={'source': 'x'}))),
            task('b', binding('consumer', stage('consume', inputs={'input': 'x'},
                                                outputs={'result': 'y'})), after=('a',)),
        ]
        for size in (16, 32):
            with self.subTest(size=size):
                h = hardware()
                spec = h['event_model']
                spec['value_bytes']['x'] = size
                for window in ('source', 'input'):
                    site = spec['windows'][window]['site']
                    h['sites'][site] = {'words': 4, 'bytes': 64}
                    spec['windows'][window]['bytes'] = size
                for window in ('other', 'result'):
                    spec['windows'][window]['offset'] = size
                plan = search(tasks, h)
                self.assertEqual(plan['nets'], ['P0-P1'])
                spec['routes']['direct']['transport_abi'] = 'u-stored-link'
                if size == 32:
                    with self.assertRaisesRegex(ValueError, 'one aligned 16-byte SRAM word'):
                        verify_timeline(tasks, h, plan)
                legal = search(tasks, h)
                verify(tasks, h, (), legal)
                self.assertEqual(legal['nets'], ['P0-P1'] if size == 16 else [])
                self.assertEqual(legal['external_read_bytes'], 0 if size == 16 else size)

    def test_stored_link_rejects_unaligned_and_out_of_range_words(self):
        from event_execution import stored_link_operand

        route = {'transport_abi': 'u-stored-link'}
        for offset in (None, -16, 4, 16384):
            with self.subTest(offset=offset):
                self.assertFalse(stored_link_operand(route, offset, 16))
        self.assertTrue(stored_link_operand(route, 16368, 16))
        self.assertFalse(stored_link_operand(route, 0, 8))

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

    def test_external_output_is_published_only_after_its_store(self):
        from event_deploy import emit

        producer = stage('produce', outputs={'source': 'y'})
        producer['backed_outputs'] = ['source']
        tasks = [task('a', binding('producer', producer))]
        for timing in ('calendar', 'replay'):
            with self.subTest(timing=timing):
                h = hardware()
                spec = h['event_model']
                spec.update(timing=timing, external_outputs=['y'],
                            external_addresses={'y': 64})
                plan = search(tasks, h)
                verify(tasks, h, (), plan)
                compute, store = plan['tasks'][0]['evaluation']['events']
                self.assertTrue(store['materializes_output'])
                self.assertEqual((compute['end'], store['start'], store['end']), (5, 5, 9))
                self.assertEqual((plan['makespan'], plan['external_write_bytes']), (9, 16))
                program = emit(tasks, h, (), plan)['program']
                compute_command, store_command, _ = program['mother']
                self.assertIn(compute_command['sequence'], store_command['wait_for'])
                descriptor = program['locals']['P0'][1]
                self.assertEqual(descriptor['required_completion'], 'destination_commit_ack')
                self.assertEqual(descriptor['write'][0]['address'], 64)
                del spec['routes']['S0-to-DDR']
                self.assertEqual(search(tasks, h)['status'], 'no_plan_in_bounded_search')

    def test_qualified_native_inplace_window_waits_for_old_value(self):
        from event_deploy import emit

        update = stage('produce', inputs={'source': 'x'}, outputs={'source': 'y'})
        update['inplace_windows'] = ['source']
        tasks = [task('a', binding('update', update))]
        h = hardware()
        spec = h['event_model']
        spec['initial_backing'] = ['x']
        spec['services']['produce']['inplace_windows'] = {'source': 16}
        plan = search(tasks, h)
        verify(tasks, h, (), plan)
        program = emit(tasks, h, (), plan)['program']
        load, compute, _ = program['mother']
        self.assertEqual(compute['wait_for'], [load['sequence']])
        spec['services']['produce']['inplace_windows']['source'] = 8
        with self.assertRaisesRegex(ValueError, 'whole-window in-place contract'):
            search(tasks, h)

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


if __name__ == '__main__':
    unittest.main()
