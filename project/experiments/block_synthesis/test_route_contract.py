"""Contract tests use synthetic ODB references; no physical qualification."""
from copy import deepcopy
import json
from pathlib import Path
import unittest

from route_contract import (VERSION, elaborate, feedback, from_plan, seal,
                            u_link_catalog, verify_feedback, verify_requirements)


def fixture():
    base = {'schema_version': VERSION, 'base_id': 'synthetic-unit-test', 'state': 'candidate', 'dbu_per_micron': 2000,
            'views': {k: {'path': 'synthetic.'+k, 'sha256': '0'*64}
                      for k in ('odb', 'netlist', 'gds')}, 'endpoints': {}}
    for name, role, component in [('a', 'driver', 'a'), ('b', 'sink', 'b'),
                                   ('c', 'driver', 'c'), ('d', 'sink', 'd')]:
        base['endpoints'][name] = {'odb_term': name, 'native_net': component, 'role': role,
                                  'm10_shapes': [{'layer': 'M10', 'object': 'synthetic/'+name,
                                                 'rect_dbu': [0, 0, 4, 4]}]}
    catalog = {'schema_version': VERSION, 'demands': {
        'edge': {'signals': [{'name': 'data', 'width': 1, 'driver': 'a', 'sinks': ['b']}]}}}
    return base, catalog


class ContractTest(unittest.TestCase):
    def test_real_two_u_protocol(self):
        root = Path(__file__).resolve().parents[3]
        path = root/'work/YUZE-LU/219/results/mutex-control-v2/current-control/generated/connections.json'
        data = json.loads(path.read_text())
        base = {'schema_version': VERSION, 'base_id': 'unbound', 'state': 'candidate'}
        request = elaborate({n: [] for n in data['all_plan_demands']}, u_link_catalog(data), base, {})
        self.assertEqual(len(request['members']), 306)  # 284 transport + 22 reservation
        self.assertEqual(sum(m['demand_id'] == 'U0->U1' for m in request['members']), 142)
        self.assertEqual(sum(u.get('reason') == 'missing_interface_template'
                             for u in request['unresolved']), 5)  # E.read/write + MC/LC control
        self.assertFalse(request['physical_qualified'])
        self.assertEqual(request['status'], 'unbound')

    def test_bound_is_not_qualified(self):
        b, c = fixture()
        r = elaborate({'edge': []}, c, b, {})
        self.assertEqual(r['status'], 'endpoint_binding_complete')
        self.assertFalse(r['physical_qualified'])
        self.assertEqual(r['nets'][0]['fixed_sinks'], [])

    def test_fanout_and_multiple_users_merge(self):
        b, c = fixture()
        c['demands']['other'] = {'signals': [{'name': 'x', 'width': 1, 'driver': 'a', 'sinks': ['d']}]}
        r = elaborate({'edge': [{'task_id': 't'}, {'task_id': 'u'}], 'other': []}, c, b, {})
        self.assertEqual(len(r['nets']), 1)
        self.assertEqual(r['nets'][0]['sinks'], ['b', 'd'])
        self.assertEqual(len(r['members']), 2)

    def test_native_alias_short_rejected(self):
        b, c = fixture()
        b['endpoints']['d']['native_net'] = 'b'
        c['demands']['other'] = {'signals': [{'name': 'x', 'width': 1, 'driver': 'c', 'sinks': ['d']}]}
        with self.assertRaisesRegex(ValueError, 'multiple drivers'):
            elaborate({'edge': [], 'other': []}, c, b, {})

    def test_occupied_native_net_rejected(self):
        b, c = fixture()
        b['fixed_native_nets'] = {'b': {'driver': 'existing_driver'}}
        with self.assertRaisesRegex(ValueError, 'multiple drivers'):
            elaborate({'edge': []}, c, b, {})

    def test_existing_wire_is_fixed(self):
        b, c = fixture()
        b['endpoints']['b']['native_net'] = 'a'
        self.assertEqual(elaborate({'edge': []}, c, b, {})['nets'][0]['fixed_sinks'], ['b'])

    def test_vector_without_bit_selection_rejected(self):
        b, c = fixture()
        c['demands']['edge']['signals'][0]['width'] = 2
        with self.assertRaisesRegex(ValueError, 'bits alias'):
            elaborate({'edge': []}, c, b, {})

    def test_invalid_m10(self):
        b, c = fixture()
        b['endpoints']['a']['m10_shapes'][0]['layer'] = 'M9'
        with self.assertRaisesRegex(ValueError, 'M10'):
            elaborate({'edge': []}, c, b, {})

    def test_missing_views(self):
        b, c = fixture()
        del b['views']['odb']
        with self.assertRaisesRegex(ValueError, 'references'):
            elaborate({'edge': []}, c, b, {})

    def test_direction_mismatch(self):
        b, c = fixture()
        b['endpoints']['a']['role'] = 'sink'
        with self.assertRaisesRegex(ValueError, 'direction'):
            elaborate({'edge': []}, c, b, {})

    def test_unknown_dependency_remains_unbound(self):
        b, c = fixture()
        c['demands']['edge']['requires'] = ['reservation']
        r = elaborate({'edge': []}, c, b, {})
        self.assertEqual(r['status'], 'unbound')
        self.assertIn('reservation', r['users'])

    def test_dependency_cycle_terminates(self):
        b, c = fixture()
        c['demands']['edge']['requires'] = ['edge']
        self.assertEqual(len(elaborate({'edge': []}, c, b, {})['members']), 1)

    def test_forged_bit_rejected_even_if_resealed(self):
        b, c = fixture()
        r = elaborate({'edge': []}, c, b, {})
        r['members'][0]['sinks'] = ['d']
        with self.assertRaisesRegex(ValueError, 'reconstruction'):
            verify_requirements(seal(r), {'edge': []}, c, b, {})

    def test_feedback_separate_and_context_bound(self):
        b, c = fixture()
        r = elaborate({'edge': []}, c, b, {})
        observation = {'category': 'search_not_found', 'code': 'local_escape', 'phase': 'access',
                       'member_ids': ['edge/data/0'], 'evidence': 'test.log'}
        f = feedback(r, [observation])
        verify_feedback(f, r)
        b['base_id'] = 'moved'
        with self.assertRaisesRegex(ValueError, 'stale'):
            verify_feedback(f, elaborate({'edge': []}, c, b, {}))
        observation['hard_constraint'] = True
        with self.assertRaisesRegex(ValueError, 'hard pruning'):
            feedback(r, [observation])

    def test_foreign_feedback(self):
        b, c = fixture()
        with self.assertRaisesRegex(ValueError, 'foreign'):
            feedback(elaborate({'edge': []}, c, b, {}), [
                {'category': 'geometry_failed', 'code': 'spacing',
                 'net_ids': ['foreign'], 'evidence': 'test.log'}])

    def test_missing_ack_abi_rejected(self):
        data = {'custom_links': [{'id': 'U0->U1', 'src': 'U0', 'dst': 'U1', 'fields': []}]}
        with self.assertRaisesRegex(ValueError, 'ABI'):
            u_link_catalog(data)

    def test_referenced_view_bytes_are_checked(self):
        import tempfile
        import hashlib
        from route_contract import read_base
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'v').write_bytes(b'actual view bytes')
            base = {'schema_version': VERSION, 'base_id': 'test', 'state': 'candidate',
                    'views': {'odb': {'path': 'v', 'sha256': hashlib.sha256(b'actual view bytes').hexdigest()}}}
            (root/'base.json').write_text(json.dumps(base))
            self.assertEqual(read_base(root/'base.json'), base)
            (root/'v').write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError, 'hash differs'):
                read_base(root/'base.json')

    def test_cli_require_bound_writes_diagnostic_then_rejects(self):
        import subprocess
        import sys
        import tempfile
        root = Path(__file__).resolve().parents[3]
        source = root/'work/YUZE-LU/219/results/mutex-control-v2/current-control/generated/connections.json'
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)/'request.json'
            result = subprocess.run([sys.executable, '-B', str(Path(__file__).with_name('route_contract.py')),
                                     '--u-connections', str(source), '--output', str(output), '--require-bound'],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertEqual(json.loads(output.read_text())['status'], 'unbound')

    def test_source_plan_fixed_union_and_bindings(self):
        b, c = fixture()
        ir = {'tasks': [{'id': 't', 'bindings': [{'id': 'b', 'site': 'S', 'ticks': 1,
              'resources': ['r'], 'scratch_words': 1, 'nets': ['edge'],
              'external_read_words': 0, 'external_write_words': 0}]}],
              'hardware': {'sites': {'S': {'words': 8}}, 'resources': {'r': 1},
                           'nets': {'edge': {'cost': 1}, 'fixed-unused': {'cost': 1, 'fixed': True}}}}
        plan = {'status': 'planned', 'tasks': [{'id': 't', 'binding': 'b', 'site': 'S', 'start': 0, 'end': 1}],
                'nets': ['edge'], 'wire_cost': 1, 'external_words': 0, 'makespan': 1}
        request = from_plan(ir, plan, c, b)
        self.assertIn('fixed-unused', request['users'])
        self.assertEqual(request['users']['edge'], [{'task_id': 't', 'binding_id': 'b'}])
        plan['tasks'][0]['binding'] = 'forged'
        with self.assertRaises(ValueError):
            from_plan(ir, plan, c, b)


if __name__ == '__main__':
    unittest.main()
