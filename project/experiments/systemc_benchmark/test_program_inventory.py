"""Check backing-allocation lifetime, not merely visible tensor sizes."""
import unittest
from program_inventory import serial_live_peak


class BackingLifetime(unittest.TestCase):
    def fixture(self, retained_view=False):
        nodes = [
            {'id': 'x', 'op': 'Constant', 'inputs': [], 'shape': [16]},
            {'id': 'view', 'op': 'View', 'inputs': ['x'], 'shape': [4]},
            {'id': 'copy', 'op': 'Convert', 'inputs': ['view'], 'shape': [4]},
            {'id': 'last', 'op': 'Convert', 'inputs': ['copy'], 'shape': [4]}]
        outputs = {'last': 'last'}
        if retained_view:
            outputs['view'] = 'view'
        return {'instructions': nodes, 'outputs': outputs}

    def test_small_view_keeps_its_full_backing_until_copy_finishes(self):
        result = serial_live_peak(self.fixture())
        self.assertEqual(result['peak_record_bytes'], 20*16)
        self.assertEqual(result['retained_output_backing_bytes'], 4*16)

    def test_retained_view_keeps_backing_across_later_operations(self):
        result = serial_live_peak(self.fixture(True))
        self.assertEqual(result['peak_record_bytes'], 24*16)
        self.assertEqual(result['retained_output_backing_bytes'], 20*16)

    def test_runtime_state_remains_while_aliased_and_is_counted_once(self):
        program = {'runtime_formats': {'past': {'shape': [2]}}, 'instructions': [
            {'id': 'a', 'op': 'View', 'inputs': ['past'], 'shape': [1]},
            {'id': 'b', 'op': 'View', 'inputs': ['a'], 'shape': [1]}],
            'outputs': {'a': 'a', 'b': 'b'}}
        result = serial_live_peak(program)
        self.assertEqual(result['peak_record_bytes'], 2*16)
        self.assertEqual(result['retained_output_backing_bytes'], 2*16)


if __name__ == '__main__':
    unittest.main()
