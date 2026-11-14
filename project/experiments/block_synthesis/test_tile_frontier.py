"""Regression checks across generic access graphs and capacity bounds."""
import unittest

from tile_frontier import Access, Axis, Frontier, Group, Hardware, Offer, Operator, Progress


class RangeSearchTest(unittest.TestCase):
    def test_bounded_reduction_keeps_ordinary_fallback(self):
        axis = Axis(8, 1)
        graph = (Operator('source', axis, 16, ()),
                 Operator('sink', Axis(2, 1), 16, (Access('source', 'reduction'),), axis))
        services = {'source': Offer(8, 1, 8), 'sink': Offer(2, 1, 8, 8, 4)}
        hardware = Hardware(80, 16, 64, 16)

        def solve(depth, *, width=None):
            return Frontier(graph, services, hardware, depth=depth, width=width, objective='ddr').solve()

        baseline, depth_one, range_plan = (solve(depth) for depth in range(3))
        self.assertEqual(baseline['ddr_bytes'], 288)
        self.assertGreater(depth_one['ddr_bytes'], range_plan['ddr_bytes'])
        self.assertEqual(range_plan['ddr_bytes'], 32)
        self.assertLessEqual(range_plan['sram_peak'], hardware.sram_bytes)
        self.assertEqual(solve(2, width=8)['ddr_bytes'], 32)

    def test_fork_join_without_reduction(self):
        axis = Axis(6, 2)
        graph = (Operator('in0', axis, 4, ()),
                 Operator('left', axis, 4, (Access('in0', 'output'),)),
                 Operator('right', axis, 4, (Access('in0', 'output'),)),
                 Operator('join', axis, 4, (Access('left', 'output'), Access('right', 'output'))))
        services = dict.fromkeys((n.value for n in graph), Offer(3, 1, 4))
        hardware = Hardware(32, 8, 32, 8)
        baseline = Frontier(graph, services, hardware, depth=0, objective='ddr').solve()
        tiled = Frontier(graph, services, hardware, depth=3, objective='ddr').solve()
        self.assertEqual(tiled['ddr_bytes'], 24)
        self.assertGreater(baseline['ddr_bytes'], 24)
        self.assertLessEqual(tiled['sram_peak'], 32)
        self.assertEqual({a['operator'] for a in tiled['actions']}, {'in0', 'left', 'right', 'join'})

    def test_exported_intermediate_can_be_read_locally(self):
        axis = Axis(4, 1)
        graph = (Operator('exposed', axis, 8, (), export=True),
                 Operator('tail', axis, 8, (Access('exposed', 'output'),)))
        services = dict.fromkeys((n.value for n in graph), Offer(4, 1, 4))
        plan = Frontier(graph, services, Hardware(64, 8, 32), depth=2, objective='ddr').solve()
        self.assertEqual(plan['ddr_bytes'], 64)
        self.assertEqual(sum(a['write_bytes'].get('exposed', 0) for a in plan['actions']), 32)
        self.assertEqual(sum(a['read_bytes'].get('exposed', 0) for a in plan['actions']), 0)

    def test_two_output_groups_share_one_activation_stream(self):
        axis = Axis(4, 1)
        graph = (Operator('producer', axis, 8, ()),
                 Operator('consumer', Axis(4, 1), 8, (Access('producer', 'reduction'),), axis))
        hardware = Hardware(16, 8, 64, partial_bank_bytes=32, partial_bank_bytes_per_tick=64)

        def solve(groups, target):
            services = {'producer': Offer(4, 1, 8),
                        'consumer': Offer(4, 1, 8, 8, 2, groups, 2)}
            return Frontier(graph, services, target, depth=2, objective='ddr').solve()

        one = solve(1, hardware)
        two = solve(2, hardware)
        self.assertGreater(one['ddr_bytes'], two['ddr_bytes'])
        self.assertEqual(two['ddr_bytes'], 32)
        self.assertEqual(two['max_active_output_groups'], 2)
        self.assertEqual(two['partial_peak'], 32)
        smaller_bank = Hardware(16, 8, 64, partial_bank_bytes=16, partial_bank_bytes_per_tick=64)
        self.assertGreater(solve(2, smaller_bank)['ddr_bytes'], 32)

    def test_out_of_order_publication_preserves_unconsumed_output(self):
        output = Axis(2, 1)
        k = Axis(2, 1)
        graph = (Operator('source', k, 8, ()),
                 Operator('reduce', output, 16, (Access('source', 'reduction'),), k),
                 Operator('sink', output, 16, (Access('reduce', 'output'),)))
        services = {'source': Offer(2, 1, 4), 'reduce': Offer(2, 1, 4, 8, 1, 2),
                    'sink': Offer(2, 1, 4)}
        frontier = Frontier(graph, services, Hardware(64, 8, 32), depth=3)

        # Output 1 is published while output 0 still has an outstanding K cell.
        progress = (Progress(2, 3), Progress(2, 2, (Group(0, 1, 1),)), Progress())
        self.assertEqual(frontier.live(0, progress), 2)
        self.assertEqual(frontier.live(1, progress), 3)
        progress = (*progress[:2], Progress(1, 1))
        self.assertEqual(frontier.live(1, progress), 2)

    def test_full_access_cannot_read_a_prefix(self):
        axis = Axis(8, 2)
        graph = (Operator('u', axis, 8, ()), Operator('v', Axis(2, 1), 4, (Access('u', 'full'),)))
        services = {'u': Offer(2, 1, 8), 'v': Offer(2, 1, 8)}
        plan = Frontier(graph, services, Hardware(64, 8, 32), depth=2).solve()['actions']
        uses = next(i for i, a in enumerate(plan) if a['operator'] == 'v')
        self.assertEqual(uses, 2)
        self.assertEqual(plan[uses - 1]['output'][1], axis.extent)


if __name__ == '__main__':
    unittest.main()
