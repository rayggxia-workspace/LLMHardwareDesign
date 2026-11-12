from copy import deepcopy
import unittest

from dma_read import Profile
from ffn_w_dma import WeightDma, WeightOwner


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


if __name__ == '__main__':
    unittest.main()
