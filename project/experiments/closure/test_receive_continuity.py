import copy
import hashlib
import json
import unittest

import numpy as np

import receive_continuity as receiver


class ContinuityTests(unittest.TestCase):
    def test_conv_history_full_window_and_initial_padding(self):
        p = np.arange(6 * 16, dtype=np.int32).reshape(6, 16)
        h0 = receiver.history_at(p, 0, 4, 3)
        self.assertEqual(h0.shape, (10, 4))
        self.assertFalse(h0.any())
        h2 = receiver.history_at(p, 2, 4, 3)
        np.testing.assert_array_equal(h2[:, :2], np.zeros((10, 2), np.int32))
        np.testing.assert_array_equal(h2[:, 2:], p[:2, 4:14].T)
        h6 = receiver.history_at(p, 6, 4, 3)
        np.testing.assert_array_equal(h6, p[2:6, 4:14].T)

    def test_complete_owner_units_conv_descriptor_changes(self):
        units = np.array([-8, -7], np.int16)
        history = np.arange(40, dtype=np.int32).reshape(10, 4)
        d = receiver.complete_descriptor("a" * 64, units, history, 4, 8, {"bits": 32})
        for changed in (receiver.complete_descriptor("b" * 64, units, history, 4, 8, {"bits": 32}),
                        receiver.complete_descriptor("a" * 64, units + 1, history, 4, 8, {"bits": 32}),
                        receiver.complete_descriptor("a" * 64, units, history + 1, 4, 8, {"bits": 32}),
                        receiver.complete_descriptor("a" * 64, units, history, 5, 8, {"bits": 32})):
            self.assertNotEqual(d["checksum"], changed["checksum"])
        self.assertEqual(d["owner"], "layer0.mamba.integer")
        self.assertEqual(d["position"], d["version"])
        checksum_input = {k: v for k, v in d.items() if k != "checksum"}
        self.assertEqual(d["checksum"], hashlib.sha256(json.dumps(checksum_input, sort_keys=True, separators=(",", ":")).encode()).hexdigest())


if __name__ == "__main__":
    unittest.main()
