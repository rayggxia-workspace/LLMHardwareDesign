"""A metadata exception must never admit unmapped hardware."""
import unittest
from inspect import mapped_inventory


class InventoryTests(unittest.TestCase):
    def test_portless_scope_and_cells(self):
        cells, metadata = mapped_inventory(dict(cells={
            "a": dict(type="DFF_X1", connections={"D": [1]}),
            "b": dict(type="$scopeinfo", connections={})}))
        self.assertEqual(dict(cells), {"DFF_X1": 1})
        self.assertEqual(metadata, 1)

    def test_unmapped_hardware_rejected(self):
        with self.assertRaises(RuntimeError):
            mapped_inventory(dict(cells={"bad": dict(type="$add", connections={})}))

    def test_connected_scope_rejected(self):
        with self.assertRaises(RuntimeError):
            mapped_inventory(dict(cells={"bad": dict(type="$scopeinfo", connections={"A": [1]})}))


if __name__ == "__main__":
    unittest.main()
