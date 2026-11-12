import random
import unittest

from event_replay import Operation, Phase, ReplayDeadlock, replay
from cover_frontier import search
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
                              rng.randint(-1, 1))
                operations.append(Operation((phase,), deps, rng.randint(0, 12)))
            expected = self.tick_reference(operations, capacity)
            actual = replay(operations, {'bank': capacity})
            self.assertEqual([(row[0].start, row[0].end) for row in actual], expected, seed)

    def test_reconstructed_checkpoint_matches_reset_replay(self):
        capacity = {'bank': 2, 'credit': 2, 'ack': 1}
        for seed in range(120):
            rng = random.Random(seed)
            operations = []
            previous = ()
            for i in range(16):
                deps = frozenset(rng.sample(range(i), min(i, rng.randrange(3))))
                phases = (
                    Phase('bank', rng.randint(1, 5), (('bank', rng.randint(1, 2)),),
                          rng.randint(-1, 1)),
                    Phase('ack', rng.randint(1, 3), (('ack', 1),)),
                )
                operations.append(Operation(phases, deps, rng.randint(0, 22), (('credit', 1),)))
                resumed = replay(operations, capacity, previous=previous)
                self.assertEqual(resumed, replay(operations, capacity), (seed, i))
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
                if ready <= tick:
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
