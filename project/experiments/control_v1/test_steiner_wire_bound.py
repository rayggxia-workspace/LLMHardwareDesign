"""Independent exhaustive connected-subgraph oracle, including all511 pin sets."""
import unittest
from steiner_wire_bound import grid_tree_bound


class Bound(unittest.TestCase):
    def test_all_nonempty_subsets_against_exhaustive_grid(self):
        points = [(x, y) for y in range(3) for x in range(3)]
        edges = [(i, j) for i, a in enumerate(points) for j, b in enumerate(points)
                 if i < j and sum(abs(x-y) for x, y in zip(a, b)) == 1]
        exact = [100] * 512
        for mask in range(1 << len(edges)):
            parent = list(range(9))
            def root(i):
                while parent[i] != i:
                    i = parent[i]
                return i
            count = 0
            for k, (i, j) in enumerate(edges):
                if mask & (1 << k):
                    parent[root(i)] = root(j)
                    count += 1
            groups = {}
            for i in range(9):
                groups.setdefault(root(i), []).append(i)
            for group in groups.values():
                covered = sum(1 << i for i in group)
                sub = covered
                while sub:
                    exact[sub] = min(exact[sub], count)
                    sub = (sub - 1) & covered
        for mask in range(1, 512):
            result = grid_tree_bound([p for i, p in enumerate(points) if mask & (1 << i)])
            self.assertLessEqual(result['necessary_wire_grid_edges'], exact[mask], mask)

    def test_distributed_fanout_stronger_than_bbox(self):
        result = grid_tree_bound([(x, y) for x in range(4) for y in range(4)])
        self.assertEqual(result, dict(hpwl_grid_edges=6, metric_mst_grid_edges=15,
                                     necessary_wire_grid_edges=8))

    def test_pair_duplicate_translation_and_invalid_grid(self):
        self.assertEqual(grid_tree_bound([(2, 7), (2, 7), (-4, 9)])['necessary_wire_grid_edges'], 8)
        self.assertEqual(grid_tree_bound([(102, 107), (96, 109)])['necessary_wire_grid_edges'], 8)
        with self.assertRaises(AssertionError):
            grid_tree_bound([(0.0, 1)])


if __name__ == '__main__':
    unittest.main()
