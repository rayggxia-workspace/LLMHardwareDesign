"""Ordering and candidate checks for the qualified FFN narrow SRAM service."""
from copy import deepcopy
import unittest

from benchmark_ffn_activation_dp import problem
from cover_frontier import search
from event_replay import Operation, Phase, ReplayTrace, replay, replay_branch
from ffn_a import A_READ, AUX, COPY, ActivationWindow, Port, replay_tile
from verify_cover_frontier import verify


class ActivationReadTests(unittest.TestCase):
    def test_live_activation_checkpoint_reprices_a_retirement_under_new_contention(self):
        capacity = {'retire': 1, 'S': 1}
        parents = [Operation((Phase('P0', 20, (('retire', 1),)),), release=95),
                   Operation((Phase('P1', 110),)), Operation((Phase('P2', 115),))]
        window = ActivationWindow(0, 3, 512, 0, (-2, -2, -2))
        activate = Operation((Phase('activation', 1, (('S', 1),), activation=window),), release=20,
                             activation_after=((0, 0), (1, 0), (2, 0)))
        operations = [*parents, activate]
        before = replay_branch(operations, capacity, previous=ReplayTrace((), checkpoint_stride=16))
        self.assertTrue(any((3, 0) in dict(checkpoint.starts) for checkpoint in before.checkpoints))
        competition = Operation((Phase('older work', 40, (('retire', 1),), priority=-1),), release=95)
        operations.append(competition)
        after = replay_branch(operations, capacity, previous=before)
        self.assertEqual(after.grants, replay(operations, capacity))
        self.assertEqual((before.grants[3][0].start, after.grants[3][0].start), (20, 20))
        self.assertGreater(after.grants[3][0].end, before.grants[3][0].end)

    def test_frontier_uses_each_retirement_for_the_next_activation(self):
        tasks, hardware = problem(1, 17172, 'U', 576, (-2, -2, -2),
                                  retirements=(17267, 17260, 17263))
        plan = search(tasks, hardware, width=8)
        verify(tasks, hardware, (), plan)
        row = next(row for row in plan['tasks'] if row['id'] == 'activation')
        receipt = row['evaluation']['events'][0]['activation']
        self.assertEqual((row['start'], receipt['loads'], receipt['proof']),
                         (17172, [17269, 17262, 17265], 17364))
        bad = deepcopy(plan)
        row = next(row for row in bad['tasks'] if row['id'] == 'activation')
        row['evaluation']['events'][0]['activation']['loads'][0] -= 1
        with self.assertRaisesRegex(ValueError, 'activation handshakes or proof'):
            verify(tasks, hardware, (), bad)
        delayed, changed_hardware = problem(1, 17172, 'U', 576, (-2, -2, -2),
                                            retirements=(17271, 17260, 17263))
        changed = search(delayed, changed_hardware, width=8)
        verify(delayed, changed_hardware, (), changed)
        choice = next(row for row in changed['tasks'] if row['id'] == 'activation')
        self.assertEqual((choice['binding'], changed['makespan']), ('on-time', 17370))
        activation = next(task for task in tasks if task['id'] == 'activation')
        activation['event_after'].pop()
        with self.assertRaisesRegex(ValueError, 'all three retirement lanes'):
            search(tasks, hardware, width=8)

    def test_frontier_propagates_activation_proof_to_consumer(self):
        tasks, hardware = problem(1, 17172, 'U', 576, (97, 90, 93))
        for width in (1, 8):
            plan = search(tasks, hardware, width=width)
            verify(tasks, hardware, (), plan)
            self.assertEqual(plan['tasks'][1]['binding'], 'one-tick-later')
            self.assertEqual(plan['tasks'][2]['start'], 17365)

        bad = deepcopy(plan)
        activation = bad['tasks'][1]['evaluation']['events'][0]['activation']
        activation['write_acks'][0][0] -= 1
        with self.assertRaisesRegex(ValueError, 'activation handshakes or proof'):
            verify(tasks, hardware, (), bad)

        bad = deepcopy(plan)
        consumer = bad['tasks'][2]
        consumer['start'] -= 1
        consumer['evaluation']['events'][0]['start'] -= 1
        with self.assertRaisesRegex(ValueError, 'interval or prerequisite'):
            verify(tasks, hardware, (), bad)

        spec = hardware['event_model']
        spec['services']['one-tick-later']['claims'] = {'U.S.port': 1}
        with self.assertRaisesRegex(ValueError, 'private port ownership'):
            search(tasks, hardware, width=1)

    def test_full_port_cannot_bypass_a_response_owner(self):
        port = Port()
        copy, read, aux = (880, 1), (880, 2), (256, 3)
        self.assertEqual(port.step(0, {COPY: copy}, True, True), ((COPY, copy), None))
        self.assertEqual(port.step(1, {A_READ: read}, True, True), ((A_READ, read), None))
        self.assertEqual(port.step(3, {AUX: aux}, True, False), (None, None))
        self.assertEqual(port.step(4, {AUX: aux}, True, True), ((AUX, aux), (COPY, copy)))
        self.assertEqual(port.step(5, {}, True, True), (None, (A_READ, read)))
        self.assertEqual(port.step(6, {}, True, True), (None, (AUX, aux)))

    def test_candidate_can_delay_an_existing_unaccepted_read(self):
        port = Port()
        read, copy, aux = (880, 1), (881, 2), (257, 3)
        port.step(4, {AUX: aux}, True, True)
        port.step(6, {}, True, True)
        candidate = deepcopy(port)
        self.assertEqual(port.step(7, {A_READ: read}, True, True), ((A_READ, read), None))
        self.assertEqual(candidate.step(7, {A_READ: read, COPY: copy}, True, True), ((COPY, copy), None))
        self.assertEqual(candidate.step(8, {A_READ: read}, True, True), ((A_READ, read), None))
        self.assertEqual(port.step(9, {}, True, True), (None, (A_READ, read)))
        self.assertEqual(candidate.step(9, {}, True, True), (None, (COPY, copy)))
        self.assertEqual(candidate.step(10, {}, True, True), (None, (A_READ, read)))

    def test_later_copy_can_complete_a_proof_earlier_under_pressure(self):
        cases = (
            (False, 17172, 2, 512, 21, (17269, 17262, 17265), 11, 17368),
            (True, 681417, 59, 3200, 954, (681512, 681513, 681515), 477, 681618),
        )
        for down, start, scope, k, epoch, loads, generation, expected in cases:
            with self.subTest(scope=scope, k=k):
                before, proof = replay_tile(1, start, scope, k, epoch, epoch, loads, generation, down=down)
                after, delayed_proof = replay_tile(1, start + 1, scope, k, epoch, epoch, loads, generation, down=down)
                self.assertEqual((proof, delayed_proof), (expected, expected - 4))
                self.assertEqual(after['done'][0][0] - before['done'][0][0], 3)
                self.assertEqual(after['load'], before['load'])


if __name__ == '__main__':
    unittest.main()
