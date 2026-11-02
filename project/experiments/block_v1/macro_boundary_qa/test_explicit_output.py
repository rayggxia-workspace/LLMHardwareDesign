"""Known RC partition must reject leakage, double-counting and wrong sources."""
import unittest
import test_audit
from audit import Invalid
from explicit_output_rc import partition, validate_partition
from native_control import probe_spef


class ExplicitOutput(unittest.TestCase):
    def test_partition_preserves_full_parent_resistor_and_both_caps(self):
        full = probe_spef(1, 20000)
        core, parent = partition(full)
        proof = validate_partition(full, core, parent)
        self.assertEqual(proof['core_output_wire_capacitance_ff'], 0)
        self.assertIn('1 q macro0:q 20000\n', parent)
        self.assertIn('1 q 1\n2 macro0:q 1\n', parent)
        self.assertFalse('ff:Q' in parent)

    def test_duplicate_cap_and_wrong_parent_connection_rejected(self):
        full = probe_spef(1, 1); core, parent = partition(full)
        for c,p in [(core.replace('1 q 0\n','1 q 1\n'),parent), (core,parent.replace('macro0:q','wrong:q'))]:
            with self.assertRaisesRegex(Invalid, 'partition changed'): validate_partition(full, c, p)

    def test_unexpected_internal_topology_is_not_partitioned(self):
        with self.assertRaisesRegex(Invalid, 'topology'):
            partition(probe_spef(1, 1).replace('2 ff:Q 1\n', '2 ff:Q 2\n'))


if __name__ == '__main__': unittest.main()
