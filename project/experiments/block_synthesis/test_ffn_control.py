from copy import deepcopy
from types import SimpleNamespace
import unittest

from ffn_control import MotherController, ScopeGroup


class MotherControllerTests(unittest.TestCase):
    def test_pending_terminal_and_live_retirement_retime_the_next_call_group(self):
        groups = [ScopeGroup(1, (1, 2, 3), False), ScopeGroup(2, (4, 5, 6), True)]

        def start():
            # The shared terminal arbitration uses physical client priority.
            lanes = {client: SimpleNamespace(retired={}) for client in (2, 1, 0)}
            return MotherController(0, groups, lanes)

        def advance(controller, first, last, p0_retire):
            retirements = {109: (2, 3), 121: (1, 2), p0_retire: (0, 1),
                           200: (0, 4), 201: (1, 5), 209: (2, 6)}
            events = []
            for tick in range(first, last):
                if tick in retirements:
                    client, sequence = retirements[tick]
                    controller.lanes[client].retired[sequence] = tick
                calls, terminals = controller.advance(tick)
                events.extend((tick, 'call', client) for client in calls)
                events.extend((tick, 'terminal', client) for client in terminals)
            return events

        prefix = start()
        first = advance(prefix, 0, 117, 120)
        self.assertEqual(prefix.rx_frame, (2, 119))
        for retirement, next_call, other_terminals in ((120, 153, [(130, 0), (135, 1)]),
                                                       (128, 156, [(131, 1), (138, 0)])):
            with self.subTest(retirement=retirement):
                branch = deepcopy(prefix)
                events = first + advance(branch, 117, 230, retirement)
                self.assertEqual(events, advance(start(), 0, 230, retirement))
                self.assertEqual([(t, p) for t, kind, p in events if kind == 'call'][3],
                                 (next_call, 0))
                terminals = [(t, p) for t, kind, p in events if kind == 'terminal']
                self.assertEqual(terminals, [(119, 2), *other_terminals, (219, 0), (224, 1), (229, 2)])
                branch.validate()


if __name__ == '__main__':
    unittest.main()
