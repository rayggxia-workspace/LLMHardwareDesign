"""Ordering and candidate checks for the qualified FFN narrow SRAM service."""
from copy import deepcopy
import unittest

from ffn_a import A_READ, AUX, COPY, Port, replay_tile


class ActivationReadTests(unittest.TestCase):
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
