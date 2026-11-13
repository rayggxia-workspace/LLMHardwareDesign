from copy import deepcopy
import random
import unittest
from unittest.mock import patch

from benchmark_decode_handoff import build as decode_handoff
from benchmark_event_ffn import copy_bank_receipt
from benchmark_ffn_control_trace import replay_readback
from benchmark_ffn_dma_provider import RECORD_BYTES, paired_input
from benchmark_native_dma_read import CASES, OLD, Request, event_input, moves_by_task
from benchmark_native_sram_replay import check_trace, event_input as sram_input
from cover_frontier import search
from dma_offer import DmaOfferChannel
from dma_read import Profile, Read
from event_execution import Model, backing_bytes
from event_replay import Operation, Phase, ReadyWindow, ReplayDeadlock, ReplayTrace, replay, replay_branch
from ffn_m import ALLOC, FILL, INPUT, INPUT_READY, RF, RF_READY, Record, Reply, commit_phases, reply_phase
from ffn_m_issue import ALLOC_CMD, Command, CommandLink, WeightCompletion, join_schedule
from ffn_mid import MIN_TICKS, MidTile
from ffn_program_cost import DESCRIPTOR_BASE, FfnCost, Program, READ_BYTES, SHARED_RESOURCES
from ffn_w import WeightTrace
from ffn_w_dma import WeightDma, WeightOwner
from sram_feeder import Access
from test_event_execution import binding, hardware, stage, task
from verify_cover_frontier import verify


class ReplayTest(unittest.TestCase):
    def test_layer_program_images_have_distinct_physical_backing(self):
        geometry = (2, 8, 512, 128)
        _, hardware = decode_handoff(geometry, geometry, tile=8, mode=1, seed=25001,
                                     candidate='lookahead', queue=16, cross_layer=True)
        spec = hardware['event_model']
        capacity = 2 * READ_BYTES + 2 * 512 * 2048
        spec['external_capacity_bytes'] = capacity
        first, second = (spec['services'][name]['ffn_program']
                         for name in ('programmed-ffn', 'programmed-ffn-l1'))
        second['lookahead'] = False
        spec['services']['alternate-l1'] = {**spec['services']['programmed-ffn-l1'],
                                            'ffn_program': {**second, 'lookahead': True}}
        self.assertEqual(backing_bytes(spec, spec['initial_backing']), capacity)
        self.assertEqual(len(Model(hardware).program_backing), 8)

        bad = deepcopy(hardware)
        bad['event_model']['external_capacity_bytes'] -= 1
        with self.assertRaisesRegex(ValueError, 'invalid external backing capacity'):
            Model(bad)
        bad = deepcopy(hardware)
        bad['event_model']['services']['programmed-ffn-l1']['ffn_program']['address_offset'] = 0x1000
        with self.assertRaisesRegex(ValueError, 'program images overlap'):
            Model(bad)
        bad = deepcopy(hardware)
        bad['event_model']['typed_dma']['addresses']['l1-h0-k-0'] = second['address_offset'] + DESCRIPTOR_BASE
        with self.assertRaisesRegex(ValueError, 'backing overlaps the calibrated FFN program'):
            Model(bad)
        for offset in (True, -4096, 2048, 2**64):
            with self.assertRaisesRegex(ValueError, 'invalid calibrated FFN address offset'):
                Program.from_spec({**first, 'address_offset': offset})

        base, moved = (Program.from_spec(config).start(32) for config in (first, second))
        offset = second['address_offset']
        for client, records in base.links.addresses.items():
            self.assertEqual(moved.links.addresses[client],
                             {sequence: address + offset for sequence, address in records.items()})
        base.call(32, 0)
        moved.call(32, 0)
        self.assertEqual(next(iter(base.descriptors.values())), [(0, 1, DESCRIPTOR_BASE)])
        self.assertEqual(next(iter(moved.descriptors.values())), [(0, 1, DESCRIPTOR_BASE + offset)])

    def test_shared_ffn_restores_live_state_and_reprices_inflight_reads(self):
        profile = Profile.from_spec({'ffn_provider': {'mode': 1, 'seed': 25001}})
        capacity = SHARED_RESOURCES
        spec = Program(1, 25001, True, 0)
        timer = Operation((Phase('timer', 128),))
        ffn = Operation((Phase('ffn', 1, tuple(capacity.items()), ffn_program=spec),), after=(0,))
        old_read = Operation((Phase('read', 1, dma_read=Read(3, 0x10000000, 4096, 2)),), release=126)

        class ShortProgram:
            def __init__(self, program, start, fabric):
                self.dma = WeightDma(profile, fabric=fabric)
                self.start = start

            def advance(self, tick):
                installs = ((0, 1, 1, 0, 1, 0x2000000),) if tick == self.start else ()
                _, completions = self.dma.step(tick, installs)
                result, reads = None, []
                for key, beats in completions:
                    if isinstance(key, WeightOwner):
                        result = FfnCost(tick, 17 * 64, 0)
                    else:
                        reads.append((key, beats))
                return result, reads

        with patch('event_replay.ActiveProgram', ShortProgram), patch('event_replay.PROGRAM_CHECKPOINT_STRIDE', 8):
            operations = [timer, old_read, ffn]
            prefix = replay_branch(operations, capacity, dma_profile=profile, previous=ReplayTrace((), (), 8))
            self.assertEqual(prefix.grants[2][0].start, 128)
            checkpoint = next(cp for cp in prefix.checkpoints if cp.tick == 128)
            self.assertIn((1, 0), checkpoint.fabric.remaining)
            active = next(cp for cp in prefix.checkpoints if cp.tick == 136)
            self.assertIs(active.program[1].dma.fabric, active.fabric)
            self.assertIn((2, 0), dict(active.starts))
            self.assertTrue(any(cp.tick == prefix.grants[2][0].end for cp in prefix.checkpoints))
            branches = []
            for address in (0x10010000, 0x10010800, 0x10010000):
                read = Operation((Phase('read', 1, dma_read=Read(4, address, 4096, 2)),), release=137)
                branch = replay_branch([*operations, read], capacity, dma_profile=profile, previous=prefix)
                self.assertEqual(branch.grants, replay([*operations, read], capacity, dma_profile=profile))
                branches.append(branch.grants)
            self.assertNotEqual(branches[0][1][0].dma_beats, prefix.grants[1][0].dma_beats)
            self.assertNotEqual(branches[0][2][0].ffn_program, branches[1][2][0].ffn_program)
            self.assertEqual(branches[0], branches[2])

    def test_prefetch_retimes_two_programs_on_one_live_fabric(self):
        profile = Profile.from_spec({'ffn_provider': {'mode': 1, 'seed': 25001},
                                     'mixed': {'queue': 8, 'write_latency': 9}})
        cap = {'MC': 1}
        claims = tuple(cap.items())
        first = Operation((Phase('ffn', 1, claims, ffn_program=Program(1, 25001, True, 0)),), release=20)
        store = Operation((Phase('store', 1, dma_read=Read(3, 0x30004000, 256, 2, True)),), release=24)
        second = Operation((Phase('ffn', 1, claims, ffn_program=Program(1, 25001, True, 0, 0x10000000)),),
                           after=(0,))

        class ShortProgram:
            def __init__(self, program, start, fabric):
                self.dma = WeightDma(profile, fabric=fabric)
                self.start = start
                base = 0x02000000 + program.address_offset
                self.installs = ((0, 1, 1, 0, 1, base), (1, 1, 2, 0, 1, base + 128))
                self.finished = 0

            def advance(self, tick):
                _, completions = self.dma.step(tick, self.installs if tick == self.start else ())
                reads = []
                for key, beats in completions:
                    if isinstance(key, WeightOwner):
                        self.finished += 1
                    else:
                        reads.append((key, beats))
                return (FfnCost(tick, 34 * 64, 0) if self.finished == 2 else None), reads

        with patch('event_replay.ActiveProgram', ShortProgram), patch('event_replay.PROGRAM_CHECKPOINT_STRIDE', 8):
            operations = [first, store, second]
            prior = replay_branch(operations, cap, dma_profile=profile, previous=ReplayTrace((), (), 8))
            expected = [(159, 84, 218), (97, 60, 182)]
            for address, ends in zip((0x40004000, 0x40004800), expected):
                prefetch = Operation((Phase('prefetch', 1, dma_read=Read(4, address, 4096, 2)),), release=24)
                branch = replay_branch([*operations, prefetch], cap, dma_profile=profile, previous=prior)
                self.assertEqual(branch.grants, replay([*operations, prefetch], cap, dma_profile=profile))
                self.assertEqual(tuple(grants[0].end for grants in branch.grants[:3]), ends)
                self.assertEqual(branch.grants[2][0].start, branch.grants[0][0].end)
            self.assertEqual(tuple(grants[0].end for grants in prior.grants), (95, 60, 152))

    def test_sram_checkpoint_preserves_pending_responses_and_reprices_old_reads(self):
        profiles = {'P0': ((0, 90, 2),), 'P1': ()}
        read = Operation((Phase('read', 1, sram_access=Access('P0', 0, 8, False, False)),))
        options = {'sram_profiles': profiles}
        timer = Operation((Phase('timer', 64),))
        old = replay_branch([read, timer], {}, **options)
        snapshot = next(checkpoint for checkpoint in old.checkpoints if checkpoint.tick == 64)
        self.assertEqual(snapshot.tick, 64)
        self.assertEqual(len(snapshot.feeders['P0'].responses[0]), 2)
        results = []
        for site in ('P0', 'P1', 'P0'):
            candidate = Operation((Phase('read', 1, sram_access=Access(site, 16, 64, True, False)),),
                                  release=86)
            operations = [read, timer, candidate]
            branch = replay_branch(operations, {}, previous=old, **options)
            self.assertIn(snapshot, branch.checkpoints)
            self.assertEqual(branch.grants, replay(operations, {}, **options))
            results.append(branch.grants)
        self.assertEqual(results[0], results[2])
        self.assertGreater(results[0][0][0].end, results[1][0][0].end)
        self.assertEqual(results[1][0], old.grants[0])

    def test_sram_plan_audit_rejects_changed_banks_and_slot_reuse(self):
        tasks, h = sram_input(3)
        plan = search(tasks, h, width=1, ready_limit=1)
        verify(tasks, h, (), plan)
        for changes, error in (
            ({'banks': [1, 0, 2, 3]}, 'address, bank'),
            ({'issue': 5}, 'bank grant'),
            ({'issue': 7, 'ack': 9}, 'bank grant'),
        ):
            bad = deepcopy(plan)
            row = next(row for row in bad['tasks'] if row['id'] == 'wide-2')
            row['evaluation']['events'][0]['sram_beats'][0].update(changes)
            if 'ack' in changes:
                # Keep the altered beat individually plausible.
                row['evaluation']['events'][0]['sram_beats'][0]['ack'] = 9
                row['evaluation']['events'][0]['end'] = row['end'] = 10
            with self.assertRaisesRegex(ValueError, error):
                verify(tasks, h, (), bad)

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

    def test_transport_budget_considers_route_ready_before_enumerating_combinations(self):
        h = hardware(resident=False)
        spec = h['event_model']
        spec.update(timing='replay', initial_backing=['x', 'z'], live_out=[])
        route = spec['routes']['DDR-to-S1']
        route.update(setup=0, ready_window={'period': 128, 'closed': 110, 'offset': 0})
        for index in range(20):
            spec['routes'][f'blocked-{index}'] = {
                **route, 'ready_window': {**route['ready_window'], 'closed': 90 + index},
            }
        spec['routes']['open'] = {**route, 'setup': 2, 'ready_window': {'period': 128, 'closed': 0, 'offset': 0}}
        spec['services']['use'] = {'ticks': 1, 'claims': {}}
        tasks = [task('graph', binding('graph', stage('use', inputs={'input': 'x'}),
                                       stage('use', inputs={'result': 'z'})))]
        bounded = search(tasks, h, width=1)
        spec['transport_limit'] = None
        exhaustive = search(tasks, h, width=1)
        for plan in (bounded, exhaustive):
            verify(tasks, h, (), plan)
            moves = [event for event in plan['tasks'][0]['evaluation']['events'] if event['kind'] == 'move']
            self.assertEqual(([move['route'] for move in moves], plan['makespan']), (['open', 'open'], 10))
        self.assertEqual((bounded['transport_attempted'], bounded['transport_truncated']), (32, 1))
        self.assertEqual((exhaustive['transport_attempted'], exhaustive['transport_truncated']), (484, 0))
        verify(tasks, h, (), search(tasks, h, width=2, backbone=bounded))

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

    def test_dma_checkpoint_rearbitrates_inflight_reads_for_sibling_candidates(self):
        profile = Profile.from_spec({'return_latency': [7, 8],
                                     'ddr_ready': [[3, 7, 14]],
                                     'client_ready': [[10, 20, 4094]]})
        capacity = {'slot': 2, 'port': 2}
        rates = {'port': (5, 2)}
        options = dict(issue_rates=rates, dma_profile=profile)
        older = Operation((Phase('data', 1, (('port', 1),), dma_read=Read(0, 0, 1024, 2)),
                           Phase('ack', 2)), holds=(('slot', 1),))
        prefix = replay_branch([older], capacity, previous=ReplayTrace((), checkpoint_stride=2), **options)
        at_four = next(checkpoint for checkpoint in prefix.checkpoints if checkpoint.tick == 4)
        self.assertEqual(dict(at_four.starts), {(0, 0): 0})
        self.assertIsNotNone(at_four.fabric.channels[0].offer.entries[0])

        def compare(address):
            read = Phase('data', 1, (('port', 1),), dma_read=Read(1, address, 512, 2))
            younger = Operation((read,), release=4, holds=(('slot', 1),))
            operations = [older, younger]
            branch = replay_branch(operations, capacity, previous=prefix, **options)
            self.assertTrue(any(checkpoint is at_four for checkpoint in branch.checkpoints))
            self.assertEqual(branch.grants, replay(operations, capacity, **options))
            return branch.grants

        shared = compare(1024)
        independent = compare(2048)
        self.assertNotEqual(shared[0][0].dma_beats, independent[0][0].dma_beats)
        self.assertEqual(compare(1024), shared)
        self.assertEqual(prefix.grants, replay([older], capacity, **options))

    def test_dma_checkpoint_keeps_rotation_across_idle_time(self):
        profile = Profile.from_spec({'ffn_provider': {'mode': 1, 'seed': 25001}})

        def read(client, address, release):
            return Operation((Phase('data', 1, dma_read=Read(client, address, 256, 2)),), release=release)

        operations = [read(3, 0, 0), Operation((Phase('idle', 100),)), read(4, 512, 150)]
        prefix = replay_branch(operations[:2], {}, dma_profile=profile)
        self.assertTrue(any(not checkpoint.fabric.active for checkpoint in prefix.checkpoints))
        branch = replay_branch(operations, {}, previous=prefix, dma_profile=profile)
        self.assertEqual(branch.grants, replay(operations, {}, dma_profile=profile))

    def test_dma_checkpoint_matches_reset_under_mixed_pressure(self):
        cap = {'port': 2, 'slot': 4, 'ack': 1}
        for seed in range(48):
            rng = random.Random(seed)
            spec = ({'return_latency': [5, 8], 'ddr_ready': [[11, 39, 5], [73, 91, 10]]}
                    if seed % 2 else {'ffn_provider': {'mode': seed % 4 // 2, 'seed': seed}})
            spec['client_ready'] = [[19, 44, 0], [75, 123, 2730]]
            options = dict(dma_profile=Profile.from_spec(spec), issue_rates={'port': (4, 3)})
            previous = ReplayTrace((), checkpoint_stride=5)
            operations = []
            for index in range(14):
                address = 4096 * index + 2048 * rng.randrange(2)
                read = Read(rng.randrange(9), address, 128 * rng.randint(1, 12), 2)
                data = Phase('data', 1, (('port', 1),), rng.randrange(3), dma_read=read)
                setup = Phase('setup', rng.randint(1, 5), ready_window=ReadyWindow(7, 3, index % 7))
                ack = Phase('ack', 2, (('ack', 1),))
                phases = (setup, data, ack) if index % 2 else (data, ack)
                deps = frozenset({rng.randrange(index)}) if index and rng.randrange(3) == 0 else frozenset()
                release = 21 * index if seed % 3 else rng.randrange(160)
                operations.append(Operation(phases, deps, release, holds=(('slot', 1),)))
                previous = replay_branch(operations, cap, previous=previous, **options)
                self.assertEqual(previous.grants, replay(operations, cap, **options), (seed, index))
                self.assertLessEqual(len(previous.checkpoints), 16)

    def test_frontier_scores_routes_with_a_live_dma_checkpoint(self):
        requests = (Request(1, 0, 0, 4096), Request(1, 0, 8192, 512))
        tasks, h = event_input(requests, client_stalls=((0, 140, 4094),), alternatives={1: (1,)})
        spec = h['event_model']
        spec['services']['gate'] = {'ticks': 70, 'claims': {}}
        gate = task('gate', {**binding('timer', stage('gate')), 'site': 'P0', 'ticks': 70})
        tasks.insert(0, gate)
        tasks[-1]['after'] = ['gate']
        restored = []

        def check_branch(operations, capacity, *, previous, save_checkpoints=True, **options):
            result = replay_branch(operations, capacity, previous=previous, save_checkpoints=save_checkpoints,
                                   **options)
            self.assertEqual(result.grants, replay(operations, capacity, **options))
            if previous:
                restored.extend(snapshot.tick for snapshot in result.checkpoints
                                if snapshot.starts and any(snapshot is old for old in previous.checkpoints))
            return result

        with patch('event_replay_plan.replay_branch', side_effect=check_branch):
            plan = search(tasks, h, width=1, ready_limit=1)
        verify(tasks, h, (), plan)
        self.assertIn(64, restored)
        row = next(row for row in plan['tasks'] if row['id'] == 'read-01')
        self.assertEqual(row['evaluation']['events'][0]['route'], 'P1.read-1')

    def test_transport_budget_reserves_trials_for_distinct_live_dma_routes(self):
        requests = (Request(1, 0, 0, 4096), Request(1, 0, 8192, 512))
        for blocked, route, ticks in ((0, 'P1.read-1', 206), (1, 'P1.read-0', 87)):
            tasks, h = event_input(requests, client_stalls=((0, 140, 4095 ^ (1 << blocked)),),
                                   alternatives={1: (1,)})
            spec = h['event_model']
            spec['services']['gate'] = {'ticks': 70, 'claims': {}}
            tasks.insert(0, task('gate', {**binding('timer', stage('gate')), 'ticks': 70}))
            tasks[-1]['after'] = ['gate']
            for index in range(36):
                spec['routes'][f'P1.read-0-{index:02}'] = dict(spec['routes']['P1.read-0'])
            bounded = search(tasks, h, width=1, ready_limit=1)
            self.assertEqual((bounded['transport_attempted'], bounded['transport_probed']), (4, 2))
            spec['transport_limit'] = None
            exhaustive = search(tasks, h, width=1, ready_limit=1)
            self.assertEqual(exhaustive['transport_attempted'], 40)
            for plan in (bounded, exhaustive):
                verify(tasks, h, (), plan)
                self.assertEqual(plan['makespan'], ticks)
                self.assertEqual(plan['tasks'][-1]['evaluation']['events'][0]['route'], route)
            if blocked == 0:
                for index in range(36):
                    spec['routes'][f'P1.read-0-{index:02}']['priority'] = index + 1
                spec['transport_limit'] = 2
                diverse = search(tasks, h, width=1, ready_limit=1)
                verify(tasks, h, (), diverse)
                self.assertEqual((diverse['makespan'], diverse['transport_probed']), (206, 2))
                self.assertGreater(diverse['transport_probe_skipped'], 0)

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

    def test_norm_late_operand_delivery_and_replay_keep_window_custody(self):
        h = hardware()
        h['resources']['N.context'] = 1
        spec = h['event_model']
        spec.update(timing='replay', initial_backing=['gamma'], initial_copies={'source': 'x'})
        spec['value_bytes']['gamma'] = 16
        spec['services']['norm'] = {
            'ticks': 9, 'claims': {}, 'hold_claims': {'N.context': 1},
            'phases': [{'kind': 'stats', 'ticks': 2, 'claims': {'S0': 1}},
                       {'kind': 'factor', 'ticks': 3, 'claims': {}},
                       {'kind': 'replay', 'ticks': 1, 'claims': {'S0': 1, 'S1': 1}},
                       {'kind': 'publish', 'ticks': 2, 'claims': {'S1': 1}},
                       {'kind': 'retire', 'ticks': 1, 'claims': {}}],
            'window_phases': {'input_reads': {'source': ['stats', 'replay'], 'input': ['replay', 'replay']},
                              'write': 'publish', 'publish': 'publish', 'result_hold': 'N.context'},
        }
        old = binding('wait', stage('wait-credit'))
        old['ticks'] = 10
        norm = binding('norm', stage('norm', inputs={'source': 'x', 'input': 'gamma'}, outputs={'result': 'y'}))
        norm['ticks'] = 9
        tasks = [task('a-wait', old), task('b-norm', norm),
                 task('c-reuse', binding('reuse', stage('produce', outputs={'source': 'z'})))]
        plan = search(tasks, h, width=1, ready_limit=1)
        verify(tasks, h, (), plan)
        load, row = plan['tasks'][1]['evaluation']['events']
        self.assertEqual((load['start'], load['end']), (10, 14))
        self.assertEqual([(p['start'], p['end']) for p in row['phases']],
                         [(0, 2), (2, 5), (14, 15), (15, 17), (17, 18)])
        self.assertEqual(plan['tasks'][2]['start'], 15)
        bad = deepcopy(plan)
        bad['tasks'][1]['evaluation']['events'][1]['phases'][2].update(start=13, end=14)
        with self.assertRaisesRegex(ValueError, 'stage read precedes move ACK'):
            verify(tasks, h, (), bad)
        bad = deepcopy(plan)
        bad['tasks'][2].update(start=14, end=19)
        bad['tasks'][2]['evaluation']['events'][0].update(start=14, end=19)
        with self.assertRaisesRegex(ValueError, 'outlives source custody'):
            verify(tasks, h, (), bad)
        invalid = spec['services']['norm']['window_phases']['input_reads']
        invalid['source'] = ['replay', 'stats']
        with self.assertRaisesRegex(ValueError, 'invalid SRAM input read phases'):
            search(tasks, h)

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

    def test_ffn_readback_respects_published_words_and_live_ready(self):
        words = ((0, 256), (1, 256))
        published = {'P0:256': 'Mid:0', 'P1:256': 'Mid:128'}
        self.assertEqual(replay_readback(words, 0, 1, published), [(1, 3), (4, 6)])
        self.assertEqual(replay_readback(words, 1, 1, published), [(2, 4), (7, 12)])
        self.assertEqual(replay_readback(words, 1, 3, published), [(3, 5), (7, 12)])
        with self.assertRaisesRegex(ValueError, 'footprint differs'):
            replay_readback(words, 1, 1, {'P0:256': 'Mid:0', 'P1:257': 'Mid:128'})

    def test_m_candidate_reprices_when_reply_snapshot_changes(self):
        h = {'resources': {}, 'sites': {'P0': {'words': 0, 'bytes': 0}}, 'nets': {},
             'event_model': {'kind': 'qualified-event-model-v1', 'timing': 'replay', 'services': {},
                             'value_bytes': {}, 'windows': {}, 'routes': {}}}
        services = h['event_model']['services']

        def service(name, *phases):
            parts = []
            for phase in phases:
                h['resources'].update(phase.claims)
                item = {'kind': phase.name, 'ticks': phase.ticks, 'claims': dict(phase.claims),
                        'priority': phase.priority}
                if phase.ready_window:
                    item['ready_window'] = dict(vars(phase.ready_window))
                parts.append(item)
            services[name] = {'ticks': sum(p.ticks for p in phases), 'claims': {}, 'phases': parts}
            return stage(name)

        def waits(row, producer, source, target):
            row['event_after'] = [{'task': producer, 'from': [0, source], 'to': [0, target]}]
            return row

        exec_choices = task('exec', binding('early', service('early', Phase('offer', 7), Phase('admit', 1))),
                            binding('late', service('late', Phase('offer', 8), Phase('admit', 1))))
        rf = waits(task('rf', binding('rf', service('rf', Phase('prepare', RF_READY),
                                                     reply_phase(0, RF, 4)))), 'exec', 'admit', 'prepare')
        inputs = waits(task('inputs', binding('inputs', service('inputs', Phase('prepare', INPUT_READY),
                                                                 reply_phase(0, INPUT, 2)))),
                       'exec', 'admit', 'prepare')
        stores = waits(task('stores', binding('stores', service('stores', *commit_phases(0, 1, True)))),
                       'rf', 'reply frame', 'select guard head')
        controls = [task(f'control{source}', binding(f'control{source}', service(
            f'control{source}', Phase('prepare', tick), reply_phase(0, source, 2))))
            for tick, source in ((18, 1), (21, 11))]
        base = [exec_choices, rf, inputs, stores]
        for tasks, width, choice, finish in ((base, 8, 'early', 39),
                                             (base + controls, 1, 'early', 42),
                                             (base + controls, 8, 'late', 39)):
            plan = search(tasks, h, width=width)
            verify(tasks, h, (), plan)
            self.assertEqual((next(row['binding'] for row in plan['tasks'] if row['id'] == 'exec'),
                              plan['makespan']), (choice, finish))

    def test_p_binding_can_handoff_a_fill_on_the_older_input_edge(self):
        records = [Record(1, 0, 1, 0, 0, False, 0), Record(2, 0, 1, 0, 1, False, 3)]
        eops = {(FILL, 1): 11, (ALLOC, 2): 14, (INPUT, 1): 35, (FILL, 2): 35}
        self.assertEqual(join_schedule(records, {(1, 0): 10}, eops, {}, lookahead=False), [(16, 1), (36, 2)])
        eops[FILL, 2] += 1
        self.assertEqual(join_schedule(records, {(1, 0): 10}, eops, {}, lookahead=False), [(16, 1), (38, 2)])

    def test_lookahead_pair_waits_for_the_younger_front(self):
        records = [Record(index + 1, 0, 1, 128, index, False, index % 2) for index in range(4)]
        eops = {(FILL, 1): 20, (ALLOC, 2): 20, (INPUT, 1): 40, (FILL, 2): 25,
                (FILL, 3): 50, (ALLOC, 4): 59, (INPUT, 3): 80, (FILL, 4): 61}
        proof, retired = {(1, 128): 10}, {2: 56}
        self.assertEqual(join_schedule(records, proof, eops, retired, lookahead=True),
                         [(22, 1), (41, 2), (64, 3), (81, 4)])
        self.assertEqual(join_schedule(records, proof, eops, retired, lookahead=False),
                         [(22, 1), (41, 2), (61, 3), (81, 4)])

    def test_weight_record_requires_every_distinct_beat(self):
        trace = WeightTrace()
        address, tag = 0x2000000, 1 << 5
        trace.record('install', 1, 0, 1, 2, 0, 1, address)
        for beat in range(17):
            trace.record('request', 2 + beat, 0, address + 64 * beat, tag + beat)
        for beat in range(16, 0, -1):
            trace.record('returned', 40 - beat, 0, tag + beat)
        with self.assertRaisesRegex(ValueError, 'coverage'):
            trace.validate()
        with self.assertRaisesRegex(ValueError, 'repeated'):
            trace.record('returned', 40, 0, tag + 16)
        trace.record('returned', 41, 0, tag)
        trace.validate()
        self.assertEqual(trace.completed[0], [WeightCompletion(42, 1, 2, 0, 1)])

    def test_pending_fill_ack_is_retimed_from_a_command_link_snapshot(self):
        side = [Command(tick, ALLOC_CMD, sequence, sequence, 2)
                for tick, sequence in ((1, 1), (8, 2), (15, 3))]
        pending = [WeightCompletion(29, 3, 3, 2, 1), WeightCompletion(30, 2, 2, 1, 1)]
        joins = [(50, 1), (90, 2), (130, 3)]
        stores = dict.fromkeys(range(1, 4), False)
        snapshot = CommandLink(stores)
        snapshot.run([], side, [], until=31, weight_completions=pending)
        for when, expected in ((31, [(30, 3), (34, 1), (38, 2)]),
                               (34, [(30, 3), (34, 2), (38, 1)])):
            candidate = WeightCompletion(when, 1, 1, 0, 1)
            trace = deepcopy(snapshot).run(joins, [], [], weight_completions=[candidate])
            self.assertEqual(trace, CommandLink(stores).run(joins, side, [], weight_completions=pending + [candidate]))
            self.assertEqual([(reply.ready, reply.sequence) for reply in trace.controls if reply.source == FILL],
                             expected)

    def test_m_link_retimes_old_allocation_when_exec_releases_bank(self):
        side = [Command(tick, ALLOC_CMD, session, sequence, 2)
                for tick, session, sequence in ((1, 1, 1), (8, 2, 2), (15, 3, 3), (22, 4, 4), (41, 6, 5))]
        fills = [Reply(tick, FILL, session, sequence, 2)
                 for tick, session, sequence in ((30, 1, 1), (60, 2, 2), (64, 3, 3), (68, 4, 4), (75, 6, 5))]
        stores = dict.fromkeys(range(1, 6), False)
        snapshot = CommandLink(stores)
        prefix = snapshot.run([], side, fills, until=31)
        self.assertEqual((len(prefix.allocations), snapshot.banks), (4, [1, 2, 3, 4]))
        self.assertEqual((prefix.replies[-1][0], snapshot.tx_open), (30, 33))
        for join, allocation in ((34, 51), (35, 52)):
            joins = [(join, 1), (80, 2), (105, 3), (130, 4), (155, 5)]
            trace = deepcopy(snapshot).run(joins, [], [])
            self.assertEqual(trace, CommandLink(stores).run(joins, side, fills))
            self.assertEqual(trace.bank_waits, {5})
            self.assertEqual(trace.allocations[-1], (allocation, 6, 5, 1))
            self.assertEqual(trace.bank_acks[-1], (allocation + 1, 6, 5, 0, 2))
        with self.assertRaisesRegex(ValueError, 'predates'):
            snapshot.run([(30, 1)], [], [])
        bad_fill = [Reply(2, FILL, 1, 1, 2), *fills[1:]]
        with self.assertRaisesRegex(ValueError, 'matching ALLOC acknowledgement'):
            CommandLink(stores).run([(34, 1)], side, bad_fill)

    def test_m_link_preserves_lookahead_frame_before_exec_push(self):
        fills = [Reply(8, FILL, 1, 1, 2), Reply(30, FILL, 2, 2, 2)]
        for side_ready, push, start in ((9, 13, 17), (13, 15, 19)):
            side = [Command(1, ALLOC_CMD, 1, 1, 2), Command(side_ready, ALLOC_CMD, 2, 2, 2)]
            trace = CommandLink({1: True, 2: False}).run([(12, 1), (40, 2)], side, fills)
            self.assertEqual(trace.pushes[0], (push, 3, 1))
            self.assertEqual(trace.executions[0], (start, 3, 1))

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
