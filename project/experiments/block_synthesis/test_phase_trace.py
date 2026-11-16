import random
import unittest

from phase_trace import reference
from verify_phase_trace import verify


def cycle_oracle(workers, channels):
    """Deliberately slow independent cycle stepping, rather than event jumps."""
    positions = [0] * len(workers)
    active = {}
    waiting = {}
    rows = []
    for tick in range(10000):
        for i, worker in enumerate(workers):
            j = positions[i]
            if j == len(worker) or i in active or i in waiting:
                continue
            phase = worker[j]
            if phase['channel'] < 0:
                active[i] = [tick, phase['ticks']]
            else:
                waiting[i] = tick
        for c in range(channels):
            if any(workers[i][positions[i]]['channel'] == c for i in active):
                continue
            choices = [i for i in waiting if workers[i][positions[i]]['channel'] == c]
            if choices:
                i = min(choices, key=lambda i: (waiting[i], i))
                active[i] = [tick, workers[i][positions[i]]['ticks']]
                del waiting[i]
        for i in list(active):
            active[i][1] -= 1
            if active[i][1] == 0:
                j = positions[i]
                rows.append((i, j, workers[i][j]['channel'], active[i][0], tick + 1))
                positions[i] += 1
                del active[i]
        if all(positions[i] == len(w) for i, w in enumerate(workers)):
            return {'rows': sorted(rows), 'makespan': tick + 1}
    raise AssertionError('cycle oracle exceeded finite bound')


class TestPhaseTrace(unittest.TestCase):
    def test_event_simulator_matches_independent_cycle_stepping(self):
        for seed in range(100):
            rng = random.Random(seed)
            channels = rng.randint(1, 3)
            workers = []
            for i in range(rng.randint(1, 5)):
                channel = rng.randrange(channels)
                workers.append([{'channel': rng.choice((-1, channel)), 'ticks': rng.randint(1, 9)}
                                for _ in range(rng.randint(1, 15))])
            self.assertEqual(reference(workers, channels), cycle_oracle(workers, channels))

    def test_same_channel_interleaves_only_at_acknowledged_boundaries(self):
        workers = [[{'channel': c, 'ticks': t} for c, t in ((0, 3), (-1, 8), (0, 3))] for _ in range(2)]
        phased = reference(workers, 1)
        whole = reference(workers, 1, whole_service=True)
        self.assertEqual(phased['makespan'], 17)
        self.assertEqual(whole['makespan'], 28)
        for i in range(2):
            rows = [r for r in phased['rows'] if r[0] == i]
            self.assertEqual(rows[1][3], rows[0][4])
            self.assertGreaterEqual(rows[2][3], rows[1][4])
        reference_data = {'whole-service': whole, 'descriptor-phases': phased}
        logs = {mode: ''.join('PHASE ' + ' '.join(map(str, row)) + '\n' for row in result['rows']) +
                'PHASE_COMPLETE ' + str(result['makespan']) + '\n' for mode, result in reference_data.items()}
        self.assertTrue(verify(reference_data, logs)['passed'])
        logs['descriptor-phases'] = logs['descriptor-phases'].replace('PHASE_COMPLETE 17', 'PHASE_COMPLETE 16')
        with self.assertRaises(ValueError):
            verify(reference_data, logs)


if __name__ == '__main__':
    unittest.main()
