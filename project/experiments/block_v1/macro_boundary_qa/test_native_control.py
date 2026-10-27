"""Keep the output-wire perturbation independent of input resistance."""
import unittest
import test_audit
from audit import Invalid
from native_control import probe_spef


class WireControl(unittest.TestCase):
    def test_output_wire_changes_only_requested_resistor_and_rejects_invalid(self):
        original = probe_spef(1)
        modified = probe_spef(1, 20000)
        self.assertEqual(modified, original.replace('1 q ff:Q 1\n', '1 q ff:Q 20000\n'))
        for invalid in (float('nan'), float('inf'), -1):
            with self.assertRaisesRegex(Invalid, 'control resistance'): probe_spef(1, invalid)


if __name__ == '__main__': unittest.main()
