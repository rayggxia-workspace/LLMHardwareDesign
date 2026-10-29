"""Native graph retention and actual data/ready direction controls."""
import json
from pathlib import Path
import tempfile
import unittest

from interconnect_experiment import fixture
from interconnect_spef import audit_native, link_spef, paired_links, prepare, wrapper


class NativeJoinTest(unittest.TestCase):
    def test_nonuniform_lengths_and_mixed_drivers_preserve_native_graph(self):
        with tempfile.TemporaryDirectory() as temporary:
            out=Path(temporary);native,links=fixture(out/'inputs',vector=True)
            meta=prepare(native,out/'prepared',links)
            cells=dict(tx='BUF_X8',mid='BUF_X8',rx='BUF_X2')
            lengths={'f000':568.,'f001':1688.}
            data=link_spef(meta,out/'links.spef','relay',lengths,cell=cells)
            self.assertEqual(data['links'][0]['costs'][2]['length_um'],284.)
            self.assertEqual(data['links'][1]['costs'][2]['length_um'],844.)
            self.assertTrue(audit_native(meta,out/'prepared/common-relay.spef',out/'links.spef')['passed'])
            text=wrapper(meta,native,'relay',cell=cells)
            self.assertIn('BUF_X8 ic_f000_mid',text)
            self.assertIn('BUF_X2 ic_f000_rx',text)
            spef=(out/'links.spef').read_text()
            self.assertIn('*D BUF_X8',spef)
            self.assertIn('*D BUF_X2',spef)
            with self.assertRaises(AssertionError):
                link_spef(meta,out/'bad.spef','relay',{'f000':568.},cell=cells)

    def test_real_float32_unit_readback_and_wrong_unit_rejection(self):
        from interconnect_experiment import read_results
        with tempfile.TemporaryDirectory() as temporary:
            out = Path(temporary)
            text = ('setup_count\t0\nhold_count\t0\n'
                    'time_unit_seconds\t9.999999717180685e-10\n'
                    'cap_unit_farads\t1.0000000036274937e-15\n'
                    'capacitance\t0\t1\t100\nslew\t0\t1\t1\nfanout\t0\t1\t1\n')
            (out/'summary.tsv').write_text(text)
            (out/'links.tsv').write_text('f000\tmax\t1.2\tleft/Q\tright/D\nf000\tmin\t0.1\tleft/Q\tright/D\n')
            (out/'annotation-connectivity.tsv').write_text('left/QN\t0\n')
            (out/'check-setup.rpt').write_text('1\n')
            (out/'sta.log').write_text('')
            self.assertTrue(read_results(out, 1)['declared_model_passed'])
            for bad in [text.replace('9.999999717180685e-10', '1e-12'),
                        text.replace('1.0000000036274937e-15', '1e-12')]:
                (out/'summary.tsv').write_text(bad)
                with self.assertRaises(AssertionError):
                    read_results(out, 1)

    def test_remote_manifest_paths_are_posix_and_budget_shared(self):
        from interconnect_stage import generate
        with tempfile.TemporaryDirectory() as temporary:
            out = Path(temporary)
            generate(out, 'block-v1-20261029-902')
            queue = json.loads((out / 'node-queue.json').read_text())
            manifest = json.loads((out / 'manifest.json').read_text())
            self.assertEqual(len(queue['tasks']), 39)
            self.assertEqual(queue['node_cpus'], 96)
            self.assertEqual(manifest['max_nodes'], 8)
            for task in queue['tasks']:
                self.assertEqual(task['cpus'], 16)
                self.assertNotIn('\\', task['cwd'])
                self.assertTrue(task['source'].startswith('/public/home/yuzelu/'))
            self.assertNotIn('\\', manifest['tasks'][0]['argv'][1])

    def test_vector_ports_are_real_buses_and_native_protection_is_preserved(self):
        with tempfile.TemporaryDirectory() as temporary:
            out=Path(temporary);native,links=fixture(out/'inputs',vector=True)
            meta=prepare(native,out/'prepared',links)
            text=wrapper(meta,native,'direct')
            self.assertIn('input [1:0] left_d;',text)
            self.assertIn('output [1:0] right_q;',text)
            self.assertNotIn('\\left_d[',text)
            observations=link_spef(meta,out/'links.spef','direct',568)
            self.assertIn('u_right/protect/A',observations['links'][0]['first_native_loads'])
            self.assertTrue(audit_native(meta,out/'prepared/common-direct.spef',out/'links.spef')['passed'])

    def test_full_native_graph_and_coupling_retained(self):
        with tempfile.TemporaryDirectory() as temporary:
            out = Path(temporary)
            native, links = fixture(out / 'inputs')
            # A native coupling term referencing the joined boundary from
            # another net must follow that boundary onto its internal node.
            for row in native.values():
                p = Path(row['spef'])
                text = p.read_text().replace('2 *4:Q 0.006\n', '2 *4:Q 0.006\n3 q d 0.0001\n')
                p.write_text(text)
            meta = prepare(native, out / 'prepared', links)
            for topology in ('direct', 'endpoints', 'relay'):
                p = out / (topology + '.spef')
                measured = link_spef(meta, p, topology, 568., 1.5)
                proof = audit_native(meta, out / ('prepared/common-' + topology + '.spef'), p)
                self.assertTrue(proof['passed'])
                self.assertEqual(measured['added_buffer_count'], dict(direct=0, endpoints=2, relay=3)[topology])
                v = wrapper(meta, native, topology)
                self.assertIn('fixture_left u_left', v)
                self.assertIn('fixture_right u_right', v)
                self.assertNotIn('.d(left_q)', v)
                self.assertIn('*10000004 u_left/ff', p.read_text())
            p = out / 'relay.spef'
            positive = p.read_text()
            controls = [positive.replace('0.006', '0.007', 1),
                        positive.replace('2 *10000004:Q 0.006\n', ''),
                        positive.replace('*10000003:199000000 left_d 0.0001',
                                         'left_q left_d 0.0001', 1)]
            for i, bad in enumerate(controls):
                self.assertNotEqual(positive, bad)
                p.write_text(bad)
                with self.assertRaises(AssertionError):
                    audit_native(meta, out / 'prepared/common-relay.spef', p)
                p.write_text(positive)

    def test_real_pair_all_bits_and_reverse_ready(self):
        for pair in [('m', 't'), ('t', 's')]:
            links = paired_links(*pair)
            self.assertEqual(len(links), 130)
            self.assertEqual([p['bit'] for p in links if p['role'] == 'data'], list(range(128)))
            ready = next(p for p in links if p['role'] == 'ready')
            self.assertEqual(ready['source'][0], 'right')
            self.assertEqual(ready['sink'][0], 'left')

    def test_non_native_units_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            out = Path(temporary)
            native, links = fixture(out / 'inputs')
            p = Path(native['right']['spef'])
            p.write_text(p.read_text().replace('*C_UNIT 1 PF', '*C_UNIT 1 FF'))
            with self.assertRaises(AssertionError):
                prepare(native, out / 'prepared', links)


if __name__ == '__main__':
    unittest.main()
