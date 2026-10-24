"""Boundary tests use only bounded synthetic arrays; real model is server-only."""
import importlib.util
from pathlib import Path
import unittest
import numpy as np

spec = importlib.util.spec_from_file_location('granite', Path(__file__).with_name('granite.py'))
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)


class GraniteTests(unittest.TestCase):
    def test_error_identity(self):
        self.assertEqual(g.error([1., 2.], [1., 2.]), {'relative_l2': 0., 'max_abs': 0.})

    def test_nonfinite_rejected(self):
        with self.assertRaises(ValueError):
            g.error([np.nan], [0.])

    def test_shape_rejected(self):
        with self.assertRaises(ValueError):
            g.error([1., 2.], [[1., 2.]])

    def test_fixed_texts_separate(self):
        self.assertNotEqual(g.TEXTS['calibration'], g.TEXTS['evaluation'])


if __name__ == '__main__':
    unittest.main()
