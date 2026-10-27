"""Residual direction, coverage and canonical constraint negative controls."""
import unittest
from copy import deepcopy
import test_audit
from audit import Invalid
from input_driver_residual import input_delays, components, decompose


class InputResidual(unittest.TestCase):
    def test_canonical_delay_preserves_min_max(self):
        sdc = '\n'.join(f'set_input_delay {value} -clock [get_clocks {{core}}] -{mm} -add_delay [get_ports {{d[0]}}]' for mm, value in [('min', '.2'), ('max', '2')])
        self.assertEqual(input_delays(sdc), {('d[0]', 'min'): .2, ('d[0]', 'max'): 2})
        with self.assertRaisesRegex(Invalid, 'duplicate input delay'): input_delays(sdc+'\n'+sdc)

    def test_unsupported_delay_not_silently_interpreted(self):
        with self.assertRaisesRegex(Invalid, 'syntax'):
            input_delays('set_input_delay 2 -clock core [get_ports d]')

    def test_duplicate_and_nan_component_rejected(self):
        row = 'QA127_DRIVER_COMPONENT\td\t^\tmax\t1e-12'
        with self.assertRaisesRegex(Invalid, 'duplicate'): components(row+'\n'+row)
        with self.assertRaisesRegex(Invalid, 'NaN'): components(row.replace('1e-12', 'nan'))

    def example(self):
        ports = {'d': {'direction': 'input', 'slew_ns': [.01]*4}, 'q': {'direction': 'output', 'slew_ns': [.02]*4}}
        full = {'ports': ports, 'observations': []}
        for mm, slack in [('max', 7), ('min', .1)]:
            full['observations'].append({'key': ['input', 'd', 'rise', mm], 'startpoint': 'd', 'arrival_ns': 0, 'slack_ns': slack})
        macro = deepcopy(full)
        for r in macro['observations']:
            mm = r['key'][-1]
            r['arrival_ns'] = (2 if mm == 'max' else .2)+.006
            r['slack_ns'] += -.002 if mm == 'max' else .002
        native = {('d', 'rise', mm): .004 for mm in ('max', 'min')}
        delays = {('d', 'max'): 2, ('d', 'min'): .2}
        return full, macro, native, delays

    def test_setup_pessimism_hold_optimism_same_driver_difference(self):
        args = self.example()
        before = deepcopy(args)
        result = decompose(*args)
        self.assertLess(result['maximum_unexplained_residual_ps'], 1e-9)
        self.assertAlmostEqual(result['rows'][0]['predicted_slack_delta_ps'], -2)
        self.assertAlmostEqual(result['rows'][1]['predicted_slack_delta_ps'], 2)
        self.assertEqual(args, before)
        self.assertFalse(result['qualified_hard_macro'])

    def test_missing_component_or_delay_rejected(self):
        for index in (2, 3):
            args = list(self.example()); args[index].pop(next(iter(args[index])))
            with self.assertRaisesRegex(Invalid, 'coverage'): decompose(*args)

    def test_wrong_startpoint_rejected(self):
        args = self.example(); args[1]['observations'][0]['startpoint'] = 'unexpected'
        with self.assertRaisesRegex(Invalid, 'start identity'): decompose(*args)


if __name__ == '__main__': unittest.main()
