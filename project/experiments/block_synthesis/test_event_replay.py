from copy import deepcopy
import random
import unittest

from benchmark_event_ffn import copy_bank_receipt
from benchmark_ffn_dma_provider import RECORD_BYTES, paired_input
from benchmark_native_dma_read import CASES, OLD, event_input, moves_by_task
from benchmark_native_sram_replay import check_trace
from cover_frontier import search
from dma_offer import DmaOfferChannel
from event_replay import Operation, Phase, ReadyWindow, ReplayDeadlock, replay
from ffn_mid import MIN_TICKS, MidTile
from test_event_execution import binding, hardware, stage, task
from verify_cover_frontier import verify


class ReplayTest(unittest.TestCase):
    def test_new_request_changes_old_completion_and_keeps_credit(self):
        write = Operation((Phase('issue', 1), Phase('data', 4, (('bus', 1),)),
                           Phase('ack', 2)), holds=(('credit', 1),))
        read = Operation((Phase('read', 3, (('bus', 1),), priority=-1),), release=1)
        next_write = Operation((Phase('issue', 1),), release=2, holds=(('credit', 1),))
        capacity = {'bus': 1, 'credit': 1}
        old = replay((write, next_write), capacity)
        changed = replay((write, next_write, read), capacity)
        self.assertEqual((old[0][-1].end, changed[0][-1].end), (7, 10))
        self.assertEqual((changed[0][0].start, changed[2][0].start), (0, 1))
        self.assertEqual((old[1][0].start, changed[1][0].start), (7, 10))

    def test_work_already_granted_runs_to_phase_end(self):
        first = Operation((Phase('data', 4, (('bus', 1),)),))
        late = Operation((Phase('data', 1, (('bus', 1),), priority=-1),), release=1)
        consumer = Operation((Phase('consume', 1),), after=frozenset({0}))
        results = replay((first, late, consumer), {'bus': 1})
        self.assertEqual([op[0].start for op in results], [0, 4, 4])

    def test_circular_backpressure_reports_deadlock(self):
        operations = tuple(
            Operation((Phase('issue', 1), Phase('data', 1, ((other, 1),))),
                      holds=((hold, 1),))
            for hold, other in (('x', 'y'), ('y', 'x')))
        with self.assertRaisesRegex(ReplayDeadlock, 'tick 1'):
            replay(operations, {'x': 1, 'y': 1})

    def test_frontier_replays_previously_chosen_action_and_its_consumer(self):
        h = hardware()
        spec = h['event_model']
        spec['initial_backing'] = ['x', 'y']
        h['resources']['DDR.credit'] = 2
        for i, port in enumerate(('S0', 'S1')):
            spec['routes'][f'DDR-to-{port}'].update(
                claims={'DDR.bus': 1}, priority=-i,
                phases={'issue': {'ticks': 1, 'claims': {}},
                        'ack': {'ticks': 1, 'claims': {port: 1}},
                        'hold_claims': {'DDR.credit': 1}})
        spec['services'].update(
            short={'ticks': 1, 'claims': {}}, long={'ticks': 8, 'claims': {}})
        tasks = [
            task('old', binding('old', stage('short', inputs={'source': 'x'}))),
            task('consumer', binding('use-old', stage('short', inputs={'source': 'x'})), after=('old',)),
            task('urgent', binding('new', stage('long', inputs={'input': 'y'}))),
        ]
        calendar_plan = None
        for timing, expected in [('calendar', (7, 8, 18)), ('replay', (11, 12, 14))]:
            spec['timing'] = timing
            plan = search(tasks, h, width=1)
            self.assertEqual([row['id'] for row in plan['tasks']], ['old', 'consumer', 'urgent'])
            self.assertEqual(tuple(row['end'] for row in plan['tasks']), expected)
            self.assertEqual(plan['makespan'], expected[-1])
            self.assertEqual(plan['external_read_bytes'], 32)
            verify(tasks, h, (), plan)
            if timing == 'calendar':
                calendar_plan = plan
            beam = search(tasks, h, width=8, backbone=plan)
            verify(tasks, h, (), beam)
            self.assertLessEqual(beam['makespan'], plan['makespan'])
        with self.assertRaisesRegex(ValueError, 'arbitration grant differs at tick 1'):
            verify(tasks, h, (), {**calendar_plan, 'timing': 'replay'})

        spec['services']['alternate'] = {'ticks': 16, 'claims': {}}
        tasks[-1]['bindings'] += (binding('alternate', stage('alternate')),)
        chosen = {}
        for timing in ('calendar', 'replay'):
            spec['timing'] = timing
            for width in (1, 8):
                plan = search(tasks, h, width=width)
                verify(tasks, h, (), plan)
                urgent = next(row for row in plan['tasks'] if row['id'] == 'urgent')
                chosen[timing, width] = urgent['binding'], plan['makespan']
        self.assertEqual(chosen['calendar', 1], ('alternate', 16))
        self.assertEqual(chosen['replay', 1], ('new', 14))
        self.assertEqual(chosen['replay', 8], ('new', 14))

    def test_single_phase_scheduler_matches_tick_reference(self):
        for seed in range(80):
            rng = random.Random(seed)
            capacity = rng.randint(1, 4)
            operations = []
            for index in range(18):
                deps = frozenset(rng.sample(range(index), min(index, rng.randrange(3))))
                phase = Phase('service', rng.randint(1, 5), (('bank', rng.randint(1, capacity)),),
                              rng.randint(-1, 1), ready_window=ReadyWindow(7, 2, index % 7) if seed % 2 else None)
                operations.append(Operation((phase,), deps, rng.randint(0, 12)))
            expected = self.tick_reference(operations, capacity)
            actual = replay(operations, {'bank': capacity})
            self.assertEqual([(row[0].start, row[0].end) for row in actual], expected, seed)

    def test_reconstructed_checkpoint_matches_reset_replay(self):
        capacity = {'bank': 2, 'credit': 2, 'ack': 1}
        for seed in range(120):
            rng = random.Random(seed)
            rates = {'bank': (3, 4)} if seed % 2 else {}
            operations = []
            previous = ()
            for i in range(16):
                deps = frozenset(rng.sample(range(i), min(i, rng.randrange(3))))
                phases = (
                    Phase('bank', rng.randint(1, 5), (('bank', rng.randint(1, 2)),),
                          rng.randint(-1, 1), ready_window=ReadyWindow(7, 2, i % 7) if seed % 3 else None),
                    Phase('ack', rng.randint(1, 3), (('ack', 1),),
                          ready_window=ReadyWindow(11, 4, i % 11) if seed % 3 == 2 else None),
                )
                phase_after = ()
                if i and rng.randrange(2):
                    parent = rng.randrange(i)
                    phase_after = (frozenset({(parent, 0)}), frozenset({(parent, 1)}))
                operations.append(Operation(phases, deps, rng.randint(0, 22), (('credit', 1),), phase_after))
                resumed = replay(operations, capacity, previous=previous, issue_rates=rates)
                self.assertEqual(resumed, replay(operations, capacity, issue_rates=rates), (seed, i))
                previous = resumed

    def test_compute_writeback_and_command_ownership_follow_distinct_phases(self):
        h = hardware()
        h['resources']['LC.slot'] = 1
        spec = h['event_model']
        spec['timing'] = 'replay'
        spec['services'].update(
            busy={'ticks': 8, 'claims': {'S0': 1}, 'priority': -1},
            coarse={'ticks': 5, 'claims': {'M0': 1, 'S0': 1, 'LC.slot': 1}},
            split={'ticks': 5, 'claims': {}, 'hold_claims': {'LC.slot': 1},
                   'phases': [{'kind': 'compute', 'ticks': 4, 'claims': {'M0': 1}},
                              {'kind': 'write_ack', 'ticks': 1, 'claims': {'S0': 1}}]},
            use={'ticks': 1, 'claims': {'LC.slot': 1}},
        )
        for candidate, visible in [('coarse', 13), ('split', 9)]:
            tasks = [
                task('occupy', binding('busy', stage('busy'))),
                task('produce', binding('producer', stage(candidate, outputs={'source': 'y'}))),
                task('consume', binding('use', stage('use', inputs={'source': 'y'})), after=('produce',)),
            ]
            plan = search(tasks, h)
            verify(tasks, h, (), plan)
            producer = next(r for r in plan['tasks'] if r['id'] == 'produce')
            self.assertEqual((producer['end'], plan['makespan']), (visible, visible + 1))
            if candidate == 'split':
                phases = producer['evaluation']['events'][0]['phases']
                self.assertEqual([(p['start'], p['end']) for p in phases], [(0, 4), (8, 9)])
                phases[1].update(start=4, end=5)
                with self.assertRaisesRegex(ValueError, 'phase coverage'):
                    verify(tasks, h, (), plan)

    def test_route_choice_compares_replayed_schedule_not_booked_arrival(self):
        h = hardware()
        spec = h['event_model']
        spec['initial_copies'] = {'source': 'x'}
        spec['initial_backing'] = ['x']
        spec['routes']['direct']['setup'] = 5
        spec['routes']['DDR-to-S1'].update(
            claims={'DDR.bus': 1}, priority=-1,
            phases={'issue': {'ticks': 1, 'claims': {}},
                    'ack': {'ticks': 1, 'claims': {'S1': 1}},
                    'hold_claims': {'DDR.credit': 1}})
        spec['services'].update(
            old={'ticks': 6, 'claims': {},
                 'phases': [{'kind': 'issue', 'ticks': 1, 'claims': {}},
                            {'kind': 'data', 'ticks': 4, 'claims': {'DDR.bus': 1}},
                            {'kind': 'ack', 'ticks': 1, 'claims': {}}]},
            use={'ticks': 8, 'claims': {}},
        )
        tasks = [
            task('old', binding('old', stage('old'))),
            task('use', binding('use', stage('use', inputs={'input': 'x'}, outputs={'result': 'y'}))),
        ]
        for timing, limit, route, makespan in (
            ('calendar', None, 'direct', 15), ('replay', 1, 'direct', 15),
            ('replay', None, 'DDR-to-S1', 14),
        ):
            spec.update(timing=timing, transport_limit=limit)
            plan = search(tasks, h, width=1)
            verify(tasks, h, (), plan)
            self.assertEqual(plan['tasks'][0]['id'], 'old')
            move = plan['tasks'][1]['evaluation']['events'][0]
            self.assertEqual((move['route'], plan['makespan']), (route, makespan))
            if timing == 'replay':
                self.assertEqual(plan['transport_truncated'], 2 if limit == 1 else 0)
                if limit is None:
                    self.assertEqual(plan['tasks'][0]['end'], 10)
                    self.assertEqual(plan['external_read_bytes'], 16)
                    verify(tasks, h, (), search(tasks, h, width=2, backbone=plan))

    def test_store_load_branches_preserve_legal_path_behind_incompatible_store(self):
        h = hardware(resident=False)
        spec = h['event_model']
        spec.update(timing='replay', initial_copies={'source': 'x'})
        h['nets'].update({'fast-store': {'cost': 1}, 'load': {'cost': 1}})
        h['incompatible_nets'] = [('fast-store', 'load')]
        store = spec['routes']['S0-to-DDR']
        spec['routes']['slow-store'] = {**store, 'setup': 5}
        store['nets'] = ['fast-store']
        spec['routes']['DDR-to-S1']['nets'] = ['load']
        tasks = [task('consume', binding('use', stage('consume', inputs={'input': 'x'},
                                                      outputs={'result': 'y'})))]
        plan = search(tasks, h, width=1)
        verify(tasks, h, (), plan)
        events = plan['tasks'][0]['evaluation']['events']
        self.assertEqual([event['route'] for event in events if event['kind'] == 'move'],
                         ['slow-store', 'DDR-to-S1'])
        self.assertEqual((plan['external_write_bytes'], plan['external_read_bytes']), (16, 16))

    def test_native_channel_rate_blocks_third_cycle_even_with_free_lanes(self):
        h = hardware()
        h['resources'].update({'DDR0.issue': 2, 'DDR1.issue': 2})
        spec = h['event_model']
        spec['live_out'] = []
        spec['issue_rates'] = {f'DDR{i}.issue': {'window_ticks': 3, 'max_issues': 4} for i in range(2)}
        for i in range(2):
            spec['services'][f'issue{i}'] = {'ticks': 1, 'claims': {f'DDR{i}.issue': 1}}
        tasks = [task(f'c0-{i}', binding('beat', stage('issue0'))) for i in range(6)]
        spec['services']['gate'] = {'ticks': 2, 'claims': {}}
        tasks += [task('gate', binding('gate', stage('gate'))),
                  task('other', binding('beat', stage('issue1')), after=('gate',))]
        static = search(tasks, h, width=1)
        verify(tasks, h, (), static)
        spec['timing'] = 'replay'
        plan = search(tasks, h, width=1)
        verify(tasks, h, (), plan)
        self.assertEqual([r['start'] for r in plan['tasks'] if r['id'].startswith('c0')], [0, 0, 1, 1, 3, 3])
        self.assertEqual(next(r['start'] for r in plan['tasks'] if r['id'] == 'other'), 2)
        with self.assertRaisesRegex(ValueError, 'arbitration grant differs at tick 2'):
            verify(tasks, h, (), {**static, 'timing': 'replay'})

    def test_checkpoint_retains_issue_history_after_phase_end(self):
        cap = {'port': 2}
        rate = {'port': (3, 4)}
        beat = Phase('issue', 1, (('port', 1),))
        operations = [Operation((beat,)) for _ in range(4)]
        operations += [Operation((beat,), release=2) for _ in range(2)]
        prefix = replay(operations[:4], cap, issue_rates=rate)
        resumed = replay(operations, cap, previous=prefix, issue_rates=rate)
        self.assertEqual(resumed, replay(operations, cap, issue_rates=rate))
        self.assertEqual([grants[0].start for grants in resumed], [0, 0, 1, 1, 3, 3])

    def test_native_dma_held_offer_reserves_the_last_issue_credit(self):
        # Channel zero at cycle 14 of the #251 typed seed-1 probe.
        before = DmaOfferChannel((2, 3), previous_issues=2, cursor=4)
        blocked = before.advance(reserved=0b11110000, ready=0b01)
        self.assertEqual(blocked, DmaOfferChannel((None, 3), previous_issues=1, cursor=4))
        self.assertEqual(blocked.advance(reserved=0b1111110000, ready=0),
                         DmaOfferChannel((4, 3), previous_issues=0, cursor=5))

    def test_typed_dma_frontier_retimes_old_reads_and_audits_beats(self):
        tasks, hardware = event_input(OLD)
        before = search(tasks, hardware, width=1)
        self.assertEqual(moves_by_task(before)[1]['dma_beats'][0]['reserved'], 1)
        tasks, hardware = event_input(*CASES['added'])
        plan = search(tasks, hardware, width=1, ready_limit=1)
        verify(tasks, hardware, (), plan)
        self.assertEqual(plan['tasks'][-1]['id'], 'read-02')
        move = moves_by_task(plan)[1]
        self.assertEqual((move['dma_beats'][0]['reserved'], plan['makespan'], plan['external_read_bytes']),
                         (2, 13, 384))
        for field in ('address', 'captured'):
            bad = deepcopy(plan)
            moves_by_task(bad)[1]['dma_beats'][0][field] += 1
            with self.assertRaisesRegex(ValueError, 'DMA handshakes or completion differ'):
                verify(tasks, hardware, (), bad)

    def test_typed_dma_frontier_chooses_route_based_on_client_backpressure(self):
        for blocked in (0, 1):
            tasks, hardware = event_input(*CASES[f'blocked-{blocked}-client-0'], alternatives={2: (1,)})
            for width in (1, 8):
                plan = search(tasks, hardware, width=width)
                verify(tasks, hardware, (), plan)
                self.assertEqual((moves_by_task(plan)[2]['route'], plan['makespan']), (f'P2.read-{1-blocked}', 13))
        del hardware['event_model']['typed_dma']['addresses']['v2']
        self.assertEqual(search(tasks, hardware, width=1)['status'], 'no_plan_in_bounded_search')

    def test_ffn_provider_selects_weight_replica_from_live_channel_occupancy(self):
        for old_channel, route, new_channel in ((0, 'P1.read-10-replica', 1), (1, 'P1.read-10', 0)):
            tasks, hardware = paired_input(old_channel)
            plan = search(tasks, hardware, width=8)
            verify(tasks, hardware, (), plan)
            move = moves_by_task(plan)[1]
            self.assertEqual((move['route'], plan['external_read_bytes']), (route, 2 * RECORD_BYTES))
            for beat in move['dma_beats']:
                self.assertEqual((beat['channel'], beat['issue_lane'] // 2), (new_channel, new_channel))
                self.assertEqual(beat['issue_lane'], beat['return_lane'])
            bad = deepcopy(plan)
            moves_by_task(bad)[1]['dma_beats'][0]['return_lane'] ^= 1
            with self.assertRaisesRegex(ValueError, 'DMA handshakes or completion differ'):
                verify(tasks, hardware, (), bad)

        spec = hardware['event_model']
        spec['external_capacity_bytes'] -= 1
        with self.assertRaisesRegex(ValueError, 'invalid external backing capacity'):
            search(tasks, hardware, width=1)
        spec['external_capacity_bytes'] += 1
        addresses = spec['typed_dma']['addresses']['v1']
        addresses['replica'] = addresses['primary'] + 64
        with self.assertRaisesRegex(ValueError, 'replicas overlap'):
            search(tasks, hardware, width=1)

    def test_archive_audit_rejects_same_word_count_with_wrong_bank_or_early_ack(self):
        rows = [{'header': 20, 'copy': 40}]
        writes = [(20 + word - 880, p, word) for p in range(3) for word in range(880, 896)]
        self.assertEqual(copy_bank_receipt(rows, writes), {
            'verified_words': 48, 'last_write_to_ack_min': 5, 'last_write_to_ack_max': 5})
        with self.assertRaisesRegex(ValueError, 'repeated'):
            copy_bank_receipt(rows, writes[:-1] + [writes[-2]])
        with self.assertRaisesRegex(ValueError, 'outside'):
            copy_bank_receipt([{'header': 20, 'copy': 35}], writes)

    def test_native_sram_trace_rejects_delayed_reuse_of_a_response_slot(self):
        lines = [
            'TRACE wide 0 issue 0', 'TRACE wide 1 issue 1', 'TRACE narrow 0 issue 2',
            'TRACE narrow 1 issue 3', 'TRACE wide 0 ack 6', 'TRACE wide 2 issue 6',
            'TRACE wide 1 ack 7', 'TRACE wide 2 ack 8', 'TRACE narrow 0 ack 9',
            'TRACE narrow 2 issue 9', 'TRACE narrow 1 ack 10', 'TRACE narrow 2 ack 11', 'PASS mode=3',
        ]
        self.assertEqual(check_trace(3, lines)['end'], 11)
        lines[9] = 'TRACE narrow 2 issue 10'
        with self.assertRaisesRegex(ValueError, 'RTL=10, replay=9'):
            check_trace(3, lines)

    def test_deferred_write_waits_for_reader_and_publishes_before_retirement(self):
        h = hardware()
        h['resources']['result.slot'] = 1
        spec = h['event_model']
        spec.update(timing='replay', initial_copies={'source': 'x'})
        spec['services'].update(
            old={'ticks': 12, 'claims': {}},
            new={'ticks': 15, 'claims': {}, 'hold_claims': {'result.slot': 1},
                 'phases': [{'kind': 'compute', 'ticks': 4, 'claims': {'M0': 1}},
                            {'kind': 'write', 'ticks': 2, 'claims': {'S0': 1}},
                            {'kind': 'commit', 'ticks': 1, 'claims': {}},
                            {'kind': 'retire', 'ticks': 8, 'claims': {}}],
                 'window_phases': {'write': 'write', 'publish': 'commit', 'result_hold': 'result.slot'}},
            read={'ticks': 1, 'claims': {'S0': 1}},
            slot={'ticks': 1, 'claims': {'result.slot': 1}},
        )
        tasks = [
            task('a-old', binding('old', stage('old', inputs={'source': 'x'}))),
            task('b-produce', binding('new', stage('new', outputs={'source': 'y'}))),
            task('c-read', binding('read', stage('read', inputs={'source': 'y'}))),
            task('d-slot', binding('slot', stage('slot'))),
        ]
        plan = search(tasks, h, width=1, ready_limit=1)
        verify(tasks, h, (), plan)
        old, producer, reader, contender = plan['tasks']
        self.assertEqual(old['end'], 12)
        phases = producer['evaluation']['events'][0]['phases']
        self.assertEqual([(p['start'], p['end']) for p in phases], [(0, 4), (12, 14), (14, 15), (15, 23)])
        self.assertEqual((reader['start'], contender['start'], plan['makespan']), (15, 23, 24))

        bad = deepcopy(plan)
        bad['tasks'][1]['evaluation']['events'][0]['phases'][1].update(start=10, end=12)
        with self.assertRaisesRegex(ValueError, 'custody'):
            verify(tasks, h, (), bad)
        bad = deepcopy(plan)
        bad['tasks'][2]['evaluation']['events'][0].update(start=14, end=15)
        bad['tasks'][2].update(start=14, end=15)
        with self.assertRaisesRegex(ValueError, 'precedes ACK'):
            verify(tasks, h, (), bad)
        del spec['services']['new']['window_phases']['result_hold']
        with self.assertRaisesRegex(ValueError, 'result hold'):
            search(tasks, h)

    def test_deferred_write_allows_compute_while_preserving_live_victim_in_ddr(self):
        h = hardware()
        h['resources']['result.slot'] = 1
        spec = h['event_model']
        spec.update(timing='replay', initial_copies={'source': 'x'}, live_out=['x', 'y'])
        spec['routes']['S0-to-DDR']['setup'] = 7
        spec['services']['split'] = {
            'ticks': 5, 'claims': {}, 'hold_claims': {'result.slot': 1},
            'phases': [{'kind': 'compute', 'ticks': 4, 'claims': {'M0': 1}},
                       {'kind': 'write', 'ticks': 1, 'claims': {'S0': 1}}],
            'window_phases': {'write': 'write', 'publish': 'write', 'result_hold': 'result.slot'},
        }
        tasks = [task('overwrite', binding('split', stage('split', outputs={'source': 'y'})))]
        for timing, expected in [('calendar', 14), ('replay', 10)]:
            spec['timing'] = timing
            plan = search(tasks, h, width=1)
            verify(tasks, h, (), plan)
            move, compute = plan['tasks'][0]['evaluation']['events']
            self.assertEqual((move['end'], move['output_eviction']), (9, 'source'))
            self.assertEqual((plan['makespan'], plan['external_write_bytes']), (expected, 16))
            if timing == 'replay':
                self.assertEqual((compute['start'], compute['phases'][-1]['start']), (0, 9))

    def test_deferred_input_capture_changes_the_best_candidate_with_residency(self):
        h = hardware()
        h['resources']['LC.slot'] = 1
        spec = h['event_model']
        spec.update(initial_backing=['x'], live_out=[])
        spec['routes']['DDR-to-S1']['setup'] = 3
        for name, setup, capture in (('long-setup', 5, 2), ('short-setup', 1, 4)):
            spec['services'][name] = {
                'ticks': setup + capture, 'claims': {}, 'hold_claims': {'LC.slot': 1},
                'phases': [{'kind': 'descriptor', 'ticks': setup, 'claims': {}},
                           {'kind': 'capture', 'ticks': capture, 'claims': {'S1': 1}}],
                'window_phases': {'read': 'capture'},
            }
        choices = [binding(name, stage(name, inputs={'input': 'x'}))
                   for name in ('long-setup', 'short-setup')]
        tasks = [task('consume', *choices)]
        for timing, resident, expected in (
            ('calendar', False, ('short-setup', 10)),
            ('replay', False, ('long-setup', 7)),
            ('replay', True, ('short-setup', 5)),
        ):
            spec.update(timing=timing, initial_copies={'input': 'x'} if resident else {})
            for width in (1, 8):
                plan = search(tasks, h, width=width)
                verify(tasks, h, (), plan)
                self.assertEqual((plan['tasks'][0]['binding'], plan['makespan']), expected)
                self.assertEqual(plan['external_read_bytes'], 0 if resident else 16)

        spec['initial_copies'] = {}
        short_only = [task('consume', choices[1])]
        bad = search(short_only, h, width=1)
        verify(short_only, h, (), bad)
        row = bad['tasks'][0]
        move, service = row['evaluation']['events']
        self.assertEqual((service['start'], move['end'], service['phases'][-1]['start']), (0, 5, 5))
        service['phases'][-1].update(start=4, end=8)
        service['end'] = row['end'] = bad['makespan'] = 8
        with self.assertRaisesRegex(ValueError, 'read precedes move ACK'):
            verify(short_only, h, (), bad)

    def test_checkpoint_uses_phase_completion_instead_of_retirement(self):
        old = Operation((Phase('capture', 3), Phase('retire', 9)), holds=(('slot', 1),))
        capture = (frozenset({(0, 0)}),)
        write = Operation((Phase('write', 1),), phase_after=capture)
        cap = {'slot': 1}
        prefix = replay((old,), cap)
        resumed = replay((old, write), cap, previous=prefix)
        self.assertEqual(resumed, replay((old, write), cap))
        self.assertEqual((resumed[1][0].start, resumed[0][-1].end), (3, 12))

    def test_cross_task_phase_gate_retimes_old_work_and_changes_the_best_binding(self):
        h = hardware()
        h['event_model'].update(timing='replay', live_out=[])
        services = h['event_model']['services']

        def split(name, phases):
            services[name] = {'ticks': sum(p[1] for p in phases), 'claims': {},
                              'phases': [{'kind': kind, 'ticks': ticks, 'claims': claims,
                                          'priority': priority}
                                         for kind, ticks, claims, priority in phases]}

        services['start'] = {'ticks': 1, 'claims': {}}
        split('controller', [('decode', 1, {}, 0), ('release', 2, {'DDR.bus': 1}, 0),
                             ('retire', 1, {}, 0)])
        split('priority-read', [('prepare', 2, {}, 0), ('request', 4, {'DDR.bus': 1}, -1)])
        split('long-setup', [('descriptor', 7, {}, 0), ('dispatch', 1, {'M0': 1}, 0)])
        split('short-setup', [('descriptor', 1, {}, 0), ('dispatch', 3, {'M0': 1}, 0)])
        producer = task('a-controller', binding('controller', stage('start'), stage('controller')))
        consumer = task('b-ffn', binding('short', stage('short-setup')), binding('long', stage('long-setup')))
        consumer['event_after'] = [{'task': producer['id'], 'from': [1, 'release'], 'to': [0, 'dispatch']}]
        urgent = task('c-urgent', binding('priority-read', stage('priority-read')))

        def row_for(plan, ident):
            return next(row for row in plan['tasks'] if row['id'] == ident)

        def dispatch(plan):
            return row_for(plan, 'b-ffn')['evaluation']['events'][0]['phases'][-1]

        base = [producer, consumer]
        old = search(base, h, width=1, ready_limit=1)
        verify(base, h, (), old)
        self.assertEqual((dispatch(old)['start'], old['makespan'], row_for(old, 'b-ffn')['binding']),
                         (4, 7, 'short'))
        self.assertEqual(row_for(old, 'a-controller')['end'], 5)
        self.assertEqual(row_for(old, 'b-ffn')['start'], 0)

        crowded = [*base, urgent]
        greedy = search(crowded, h, width=1, ready_limit=1)
        beam = search(crowded, h, width=8)
        for plan in (greedy, beam):
            verify(crowded, h, (), plan)
            self.assertEqual((dispatch(plan)['start'], row_for(plan, 'a-controller')['end']), (8, 9))
        self.assertEqual((row_for(greedy, 'b-ffn')['binding'], greedy['makespan']), ('short', 11))
        self.assertEqual((row_for(beam, 'b-ffn')['binding'], beam['makespan']), ('long', 9))

        bad = deepcopy(greedy)
        dispatch(bad).update(start=7, end=10)
        consumer_row = row_for(bad, 'b-ffn')
        consumer_row['evaluation']['events'][0]['end'] = consumer_row['end'] = bad['makespan'] = 10
        with self.assertRaisesRegex(ValueError, 'before its producer phase completed'):
            verify(crowded, h, (), bad)

        # A singleton alternate action can export the original task's phase.
        services['fast-start'] = {'ticks': 1, 'claims': {}, 'priority': -1}
        split('fast-controller', [('decode', 1, {}, 0), ('release', 1, {}, 0),
                                  ('retire', 1, {}, 0)])
        alias = {'id': 'fast-control', 'covers': [producer['id']],
                 'bindings': [binding('fast', stage('fast-start'), stage('fast-controller'))]}
        covered = search(base, h, [alias], width=8)
        verify(base, h, [alias], covered)
        self.assertEqual((row_for(covered, 'fast-control')['end'], dispatch(covered)['start']), (4, 3))
        with self.assertRaisesRegex(ValueError, 'no mapping'):
            search(base, h, [{**alias, 'covers': [producer['id'], consumer['id']]}], width=8)

        broken = deepcopy(base)
        broken[1]['event_after'][0]['from'] = [0, 'release']
        with self.assertRaisesRegex(ValueError, 'unknown phase'):
            search(broken, h)
        cyclic = deepcopy(base)
        cyclic[0]['after'] = [consumer['id']]
        with self.assertRaisesRegex(ValueError, 'cycle'):
            search(cyclic, h)
        h['event_model']['timing'] = 'calendar'
        with self.assertRaisesRegex(ValueError, 'require event replay'):
            search(base, h)

    def test_ready_window_reprices_old_grant_and_rejects_wrong_edges(self):
        h = hardware()
        spec = h['event_model']
        spec.update(timing='replay', live_out=[])
        spec['services']['gated'] = {
            'ticks': 2, 'claims': {'S0': 1},
            'ready_window': {'period': 7, 'closed': 2, 'offset': 0},
        }
        spec['services']['interfere'] = {
            'ticks': 3, 'claims': {},
            'phases': [{'kind': 'prepare', 'ticks': 2, 'claims': {}},
                       {'kind': 'write', 'ticks': 1, 'claims': {'S0': 1}, 'priority': -1}],
        }
        old = task('a-old', binding('old', stage('gated')))
        other = task('b-new', binding('new', stage('interfere')))
        base = search([old], h, width=1)
        verify([old], h, (), base)
        self.assertEqual(base['tasks'][0]['start'], 2)
        crowded = search([old, other], h, width=1, ready_limit=1)
        verify([old, other], h, (), crowded)
        self.assertEqual((crowded['tasks'][0]['start'], crowded['makespan']), (3, 5))
        for tick in (1, 4):
            bad = deepcopy(base)
            row = bad['tasks'][0]
            row.update(start=tick, end=tick+2)
            row['evaluation']['events'][0].update(start=tick, end=tick+2)
            bad['makespan'] = tick+2
            with self.assertRaisesRegex(ValueError, 'arbitration grant differs'):
                verify([old], h, (), bad)
        spec['services']['gated']['ready_window']['closed'] = 7
        with self.assertRaisesRegex(ValueError, 'invalid phase READY'):
            search([old], h)

    def test_mid_service_can_finish_earlier_after_later_launch(self):
        tile = MidTile(1, 0)
        claims = tile.claims()
        names = {'gate': (720, 32), 'up': (784, 32), 'output': (256, 16)}
        hardware = {
            'resources': claims, 'nets': {}, 'sites': {'P0': {'words': 1024, 'bytes': 16384}},
            'event_model': {
                'kind': 'qualified-event-model-v1', 'timing': 'replay', 'routes': {},
                'windows': {name: {'site': 'P0', 'offset': address * 16, 'bytes': count * 16}
                            for name, (address, count) in names.items()},
                'value_bytes': {name: count * 16 for name, (_, count) in names.items()},
                'initial_copies': {'gate': 'gate', 'up': 'up'},
                'services': {
                    'early': {'ticks': 10, 'claims': {}},
                    'late': {'ticks': 11, 'claims': {}},
                    'mid': {'ticks': MIN_TICKS, 'claims': claims, 'ffn_mid': {'mode': 1, 'first': 0}},
                },
            },
        }
        tasks = [
            task('producer', binding('early', stage('early')), binding('late', stage('late'))),
            task('mid', binding('mid', stage('mid', inputs={'gate': 'gate', 'up': 'up'},
                                            outputs={'output': 'output'})), after=('producer',)),
        ]
        for width, choice, start, finish in ((1, 'early', 10, 385), (8, 'late', 11, 375)):
            plan = search(tasks, hardware, width=width)
            verify(tasks, hardware, (), plan)
            self.assertEqual((plan['tasks'][0]['binding'], plan['tasks'][1]['start'], plan['makespan']),
                             (choice, start, finish))
        plan['tasks'][1]['end'] -= 1
        plan['tasks'][1]['evaluation']['events'][0]['end'] -= 1
        plan['makespan'] -= 1
        with self.assertRaisesRegex(ValueError, 'FFN Mid completion differs'):
            verify(tasks, hardware, (), plan)
        hardware['event_model']['windows']['up']['offset'] += 16
        with self.assertRaisesRegex(ValueError, 'windows differ from physical inputs or output'):
            search(tasks, hardware)

    @staticmethod
    def tick_reference(operations, capacity):
        assigned = {}
        for tick in range(130):
            free = capacity - sum(operations[i].phases[0].claims[0][1]
                                  for i, (_, end) in assigned.items() if end > tick)
            eligible = []
            for i, op in enumerate(operations):
                if i in assigned or not op.after <= assigned.keys():
                    continue
                ready = max([op.release] + [assigned[p][1] for p in op.after])
                gate = op.phases[0].ready_window
                if ready <= tick and (gate is None or (tick + gate.offset) % gate.period >= gate.closed):
                    eligible.append((op.phases[0].priority, ready, i))
            for _, _, i in sorted(eligible):
                phase = operations[i].phases[0]
                units = phase.claims[0][1]
                if units <= free:
                    free -= units
                    assigned[i] = tick, tick + phase.ticks
            if len(assigned) == len(operations):
                return [assigned[i] for i in range(len(operations))]
        raise AssertionError('reference did not drain')


if __name__ == '__main__':
    unittest.main()
