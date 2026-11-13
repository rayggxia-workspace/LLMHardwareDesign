import tempfile
import unittest
from pathlib import Path

from true_iterm_inventory import (Terminal, bound_file, connected_native_access, covered,
                                  file_hash, leaf_resistor_path, net_patches, prepare_members,
                                  require_terminal)


class TrueITermInventoryTests(unittest.TestCase):
    def setUp(self):
        self.term = Terminal('instance', 'Z', 'BUF', 'CORE', 'OUTPUT', 'source',
                             'SIGNAL', 'PLACED', 'R0', 0, 0)
        self.term.members = [('instance', 'Z', 'OUTPUT')]
        self.term.shapes = [('metal9', 'iterm-pin', (0, 0, 2, 2)),
                            ('metal9', 'wire', (1, 1, 4, 4)),
                            ('via9', 'wire-via', (2, 2, 3, 3)),
                            ('metal10', 'wire-via', (1, 1, 4, 4))]

    def test_alias_and_second_driver_rejected(self):
        require_terminal(self.term, 'driver')
        self.term.aliases.append('boundary')
        with self.assertRaisesRegex(ValueError, 'fixture BTerm alias'):
            require_terminal(self.term, 'driver')
        self.term.aliases.clear()
        self.term.members.append(('other', 'Z', 'OUTPUT'))
        with self.assertRaisesRegex(ValueError, 'unexpected physical drivers'):
            require_terminal(self.term, 'driver')

    def test_disconnected_or_partial_copper_cannot_cover_claimed_access(self):
        patches = [('metal10', 'def-rect', (3, 1, 5, 4)),
                   ('metal10', 'def-rect', (7, 1, 8, 4))]
        copper = [rect for layer, _, rect in connected_native_access(self.term, patches) if layer == 'metal10']
        self.assertTrue(covered((1, 1, 5, 4), copper))
        self.assertFalse(covered((1, 1, 8, 4), copper))
        self.assertFalse(covered((7, 1, 8, 4), copper))

    def test_edge_touching_cut_does_not_connect_adjacent_metal(self):
        self.term.shapes[2] = ('via9', 'wire-via', (4, 2, 5, 3))
        with self.assertRaisesRegex(ValueError, 'no native copper path'):
            connected_native_access(self.term, [])

    def test_exact_cut_members_and_bit_order(self):
        catalog = {'schema_version': 'route-contract/1', 'demands': {'link': {'signals': [
            {'name': 'payload', 'width': 2, 'driver': 'a/Z{bit}', 'sinks': ['b/A{bit}']}]}}}
        cuts = {f'link/payload/{i}': {'driver': f'a/Z{i}', 'sinks': [f'b/A{i}']} for i in range(2)}
        self.assertEqual(len(prepare_members(catalog, {'link': []}, cuts)[1]), 4)
        cuts['link/payload/0']['sinks'] = ['b/A1']
        with self.assertRaisesRegex(ValueError, 'catalog differs'):
            prepare_members(catalog, {'link': []}, cuts)
        del cuts['link/payload/1']
        with self.assertRaisesRegex(ValueError, 'cut coverage differs'):
            prepare_members(catalog, {'link': []}, cuts)

    def test_leaf_resistance_requires_exact_odb_iterm_and_real_resistor(self):
        text = ('*DELIMITER :\n*NAME_MAP\n*1 real\n*2 input\n*D_NET *2 0.1\n'
                '*CONN\n*I *1:A I\n*P *2 I\n*CAP\n1 *2 1\n*RES\n1 *2 *1:A 0.5\n*END\n')
        with tempfile.TemporaryDirectory() as scratch:
            path = Path(scratch) / 'leaf.spef'
            path.write_text(text, encoding='utf-8')
            self.assertTrue(leaf_resistor_path(path, 'input', 'INPUT', {('real', 'A')}))
            self.assertFalse(leaf_resistor_path(path, 'input', 'INPUT', {('wrong', 'A')}))
            for replacement in ('*2 other 0.5', '*2 *1:A inf', '*2 *1:A -0.5'):
                path.write_text(text.replace('*2 *1:A 0.5', replacement), encoding='utf-8')
                self.assertFalse(leaf_resistor_path(path, 'input', 'INPUT', {('real', 'A')}))

    def test_route_patches_and_source_fingerprint(self):
        text = ('NETS 2 ;\n - source\n   NEW metal10 ( 12 -3 ) RECT ( -2 -2 2 2 ) ;\n'
                ' - other\n   NEW metal10 ( 12 -3 ) RECT ( -2 -2 2 2 ) ;\nEND NETS\n')
        with tempfile.TemporaryDirectory() as scratch:
            path = Path(scratch) / 'source.def'
            path.write_text(text, encoding='utf-8')
            record = {'path': str(path), 'sha256': file_hash(path)}
            self.assertEqual(bound_file(record), path)
            self.assertEqual(net_patches(path, {'source'}), {'source': [('metal10', 'def-rect', (10, -5, 14, -1))]})
            path.write_text(text.replace('source', 'alias'), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'source fingerprint differs'):
                bound_file(record)


if __name__ == '__main__':
    unittest.main()
