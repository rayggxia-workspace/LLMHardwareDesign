import functools
import random
import unittest
from pin_escape_bound import inspect, maximum_matching


class PinEscapeBoundTest(unittest.TestCase):
    def fixture(self):
        nets = {'a': [(9,10),(30,30)], 'b': [(11,10),(32,32)]}
        blockers = [(8,10),(9,9),(9,11),(12,10),(11,9),(11,11)]
        nets.update({str(i): [v, (34+2*(i%3),34+2*(i//3))] for i,v in enumerate(blockers)})
        return nets

    def test_shared_only_exit_is_impossible(self):
        r = inspect(self.fixture(),48,48)
        self.assertFalse(r['necessary_condition_satisfied'])
        self.assertEqual((r['hall_witness']['demand_groups'],r['hall_witness']['available_first_step_vertices']),(2,1))

    def test_second_exit_removes_necessary_failure(self):
        nets = self.fixture();del nets['0']
        self.assertTrue(inspect(nets,48,48)['necessary_condition_satisfied'])

    def test_same_net_may_share_exit(self):
        nets = self.fixture();nets['a'] += nets.pop('b')
        r = inspect(nets,48,48)
        self.assertTrue(r['necessary_condition_satisfied'])
        self.assertEqual(r['demand_components'],1)

    def test_matching_against_independent_subset_dp(self):
        rng = random.Random(190)
        for _ in range(200):
            n, m = rng.randrange(9), rng.randrange(1,9)
            edges = [sorted(rng.sample(range(m),rng.randrange(min(4,m)+1))) for i in range(n)]
            @functools.lru_cache(None)
            def optimum(i,used):
                if i == n:return 0
                return max([optimum(i+1,used)] + [1+optimum(i+1,used|(1<<v)) for v in edges[i] if not used&(1<<v)])
            left,right = maximum_matching(edges)
            self.assertEqual(len(right),optimum(0,0))
            self.assertEqual(len(right),sum(v is not None for v in left))
            for i,v in enumerate(left):
                if v is not None:self.assertIn(v,edges[i]);self.assertEqual(right[v],i)


if __name__ == '__main__':unittest.main()
