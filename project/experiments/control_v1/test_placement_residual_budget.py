import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from placement_residual_budget import budgets


class ResidualBudgetTest(unittest.TestCase):
    def execute(self, mutate=lambda data: None, bad_hash=False):
        driver = dict(instance='macro_1', pin='out_data[0]', direction='output')
        row = dict(net='net_5', driver=driver, max_capacitance_ff=20,
                   native_ground_cap_ff=3, minimum_input_pin_cap_ff=2)
        data = dict(passed=True, diagnostic_executed=True, whole_system_qualified=False,
                    placements=[dict(placement='a', rows=[row.copy()]), dict(placement='b', rows=[row.copy()])])
        mutate(data)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'native-pin-load.json'
            path.write_text(json.dumps(data))
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            (path.parent/'receipt.json').write_text(json.dumps(dict(passed=True,
                stage='minimum-native-pin-capacitance-failure-only', outputs={path.name: '0'*64 if bad_hash else digest})))
            return budgets(path, {'net_5': dict(driver=driver, physical_driver=dict(max_capacitance_ff=20))})

    def test_subtracts_both_loads_with_source_bindings(self):
        values, bindings = self.execute()
        self.assertEqual(values, {'net_5': 15})
        self.assertEqual(len(bindings), 3)

    def test_original_report_hash_required(self):
        with self.assertRaises(AssertionError):
            self.execute(bad_hash=True)

    def test_disagreement_across_placements_rejected(self):
        with self.assertRaises(AssertionError):
            self.execute(lambda data: data['placements'][1]['rows'][0].update(native_ground_cap_ff=4))

    def test_invalid_or_exhausted_capacitance_rejected(self):
        for load in (-1, 18, 20):
            with self.subTest(load=load), self.assertRaises(AssertionError):
                self.execute(lambda data: data['placements'][0]['rows'][0].update(native_ground_cap_ff=load))

    def test_changed_driver_and_limit_rejected(self):
        for update in [dict(driver=dict(instance='macro_2', pin='out_data[0]', direction='output')),
                       dict(max_capacitance_ff=21)]:
            with self.subTest(update=update), self.assertRaises(AssertionError):
                self.execute(lambda data: data['placements'][0]['rows'][0].update(update))


if __name__ == '__main__':
    unittest.main()
