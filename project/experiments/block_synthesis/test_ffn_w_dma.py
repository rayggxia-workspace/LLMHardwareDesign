from copy import deepcopy
import unittest

from dma_read import Profile
from ffn_join import JoinController
from ffn_m import Record
from ffn_m_issue import ALLOC_CMD, Command, CommandLink, FILL, WeightCompletion
from ffn_w_dma import WeightCommandLinks, WeightDma, WeightOwner


class WeightDmaTests(unittest.TestCase):
    def test_candidate_retimes_existing_weight_and_descriptor_from_live_state(self):
        profile = Profile.from_spec({'ffn_provider': {'mode': 1, 'seed': 25001}})
        old = ((0, 1, 1, 0, 1, 0x2000000), (1, 1, 2, 0, 1, 0x2100000))
        candidate = (2, 1, 3, 0, 1, 0x2200000)
        prefix = WeightDma(profile)
        for tick in range(6):
            prefix.step(tick, old if tick == 0 else ())
        self.assertEqual([port.outstanding for port in prefix.ports], [4, 4, 0])

        def run(service, start, launch):
            done = {}
            for tick in range(start, 56):
                if tick == 9:
                    service.submit_descriptor(0, 1, 4096)
                installs = old if tick == 0 else (candidate,) if tick == launch else ()
                _, completed = service.step(tick, installs)
                done.update(completed)
            self.assertFalse(service.fabric.active)
            return done

        keys = WeightOwner(*old[1][:-1]), (0, 1), WeightOwner(*candidate[:-1])
        for launch, ends in ((6, (49, 27, 53)), (7, (46, 24, 54))):
            with self.subTest(launch=launch):
                branch = run(deepcopy(prefix), 6, launch)
                self.assertEqual(branch, run(WeightDma(profile), 0, launch))
                self.assertEqual(tuple(max(beat.delivered for beat in branch[key]) for key in keys), ends)

    def test_allocation_candidate_retimes_an_old_fill_through_shared_ddr(self):
        profile = Profile.from_spec({'ffn_provider': {'mode': 1, 'seed': 25001}})
        addresses = {client: {client + 1: 0x2000000 + client * 0x100000} for client in range(3)}
        links = {client: CommandLink({client + 1: False}) for client in range(3)}
        for client in (0, 1):
            sequence = client + 1
            links[client].run([(100, sequence)], [Command(1, ALLOC_CMD, 1, sequence, 2)], (), until=0)
        dma, coupled = WeightDma(profile), WeightCommandLinks(links, addresses)

        def advance(dma, coupled, start, end):
            for tick in range(start, end):
                if tick == 16:
                    dma.submit_descriptor(0, 1, 4096)
                _, completed = dma.step(tick, coupled.advance(tick))
                for owner, _ in completed:
                    if isinstance(owner, WeightOwner):
                        coupled.complete(owner.client,
                                         WeightCompletion(tick + 1, owner.session, owner.sequence,
                                                          owner.bank, owner.generation))

        advance(dma, coupled, 0, 13)
        self.assertEqual([port.outstanding for port in dma.ports], [7, 7, 0])
        for launch, expected in ((13, (47, 50, 60)), (16, (43, 48, 61))):
            with self.subTest(launch=launch):
                branch_dma, branch = deepcopy((dma, coupled))
                branch.links[2].run([(100, 3)], [Command(launch, ALLOC_CMD, 1, 3, 2)], (), until=13)
                advance(branch_dma, branch, 13, 125)
                traces = branch.finish()
                self.assertEqual(traces[2].bank_acks, [(launch + 3, 1, 3, 0, 1)])
                self.assertEqual(tuple(next(reply.ready for reply in traces[p].controls if reply.source == FILL)
                                       for p in range(3)), expected)
                self.assertFalse(branch_dma.fabric.active)

    def test_copy_candidate_retimes_live_binding_and_retirement_from_snapshot(self):
        profile = Profile.from_spec({'ffn_provider': {'mode': 0, 'seed': 25002}})
        records = {0: [Record(1, 70, 1, 0, 0, False, 0)]}
        tiles = [(1, 0, 100, False)]

        def start(allocation, delay):
            driver = JoinController(records, tiles, 0, lookahead=True, copy_delay_epoch=delay)
            link = CommandLink({1: False})
            link.run((), [Command(allocation, ALLOC_CMD, 1, 1, 2)], (), until=0)
            return WeightDma(profile), WeightCommandLinks({0: link}, {0: {1: 0x2000000}}, join_driver=driver)

        def advance(state, first, last):
            dma, coupled = state
            for tick in range(first, last):
                _, completed = dma.step(tick, coupled.advance(tick))
                for owner, _ in completed:
                    coupled.complete(owner.client, WeightCompletion(tick + 1, owner.session, owner.sequence,
                                                                     owner.bank, owner.generation))

        def result(state):
            dma, coupled = state
            self.assertFalse(dma.fabric.active)
            issue = coupled.finish()[0]
            lane = coupled.join_driver.lanes[0]
            return (coupled.join_driver.proofs[1, 0], lane.eops[FILL, 1],
                    lane.joined[0][0], issue.executions[0][0], lane.retired[1])

        prefix = start(80, 0)
        advance(prefix, 0, 90)
        self.assertGreater(prefix[0].ports[0].outstanding, 0)
        results = []
        for delay in (0, 1):
            branch = deepcopy(prefix)
            branch[1].join_driver.copy_delay_epoch = delay
            advance(branch, 90, 400)
            cold = start(80, delay)
            advance(cold, 0, 400)
            results.append(result(branch))
            self.assertEqual(results[-1], result(cold))
        self.assertEqual(results[0][:3], (218, results[1][1], 220))
        self.assertEqual(tuple(new - old for old, new in zip(*results)), (1, 0, 1, 1, 1))

        late = start(220, 0)
        advance(late, 0, 400)
        proof, fill, binding, _, _ = result(late)
        self.assertLess(proof, fill)
        self.assertEqual(binding, fill + 2)


if __name__ == '__main__':
    unittest.main()
