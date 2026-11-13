import unittest
from energy import integrate


class EnergyAccounting(unittest.TestCase):
    def test_idle_and_activity_are_not_counted_twice(self):
        # 2 W idle for 10 ns plus three 5 nJ increments = 35 nJ.
        c = {'M0': {'idle_w': 2, 'coefficient_class': 'activity_calibrated',
                    'evidence_sha256': 'fixture-idle',
                    'commands': {'execute': {'incremental_j': 5e-9,
                                              'evidence_sha256': 'fixture-active'}}}}
        r = integrate(10000, ['M0'], c, [{'instance': 'M0', 'command': 'execute', 'count': 3}])
        self.assertTrue(r['complete'])
        self.assertAlmostEqual(r['joules'] / 1e-9, 35)

    def test_missing_ddr_prevents_total(self):
        r = integrate(1000, ['M0', 'DDR'], {}, [])
        self.assertIsNone(r['joules'])
        self.assertFalse(r['complete'])
        self.assertIn('DDR:idle', r['missing'])

    def test_unknown_command_is_not_free(self):
        c = {'S0': {'idle_w': 0, 'coefficient_class': 'activity_calibrated', 'evidence_sha256': 'fixture'}}
        r = integrate(1000, ['S0'], c, [{'instance': 'S0', 'command': 'read', 'count': 1}])
        self.assertIsNone(r['joules'])
        self.assertIn('S0:read', r['missing'])

    def test_negative_energy_and_duplicate_instances_fail(self):
        with self.assertRaises(ValueError):
            integrate(1000, ['M0', 'M0'], {}, [])
        with self.assertRaises(ValueError):
            integrate(1000, ['M0'], {'M0': {'idle_w': -1}}, [])


if __name__ == '__main__':
    unittest.main()
