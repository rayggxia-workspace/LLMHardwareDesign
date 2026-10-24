"""Small boundary/causality tests; no model downloads or native model execution."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np

_spec = importlib.util.spec_from_file_location("falcon70", Path(__file__).with_name("falcon.py"))
f = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(f)


class RecurrenceTests(unittest.TestCase):
    def setUp(self):
        self.args = dict(a=np.array([.5, .75, .25, .5]), dt=np.array([.5, .25, .75, .5]),
                         x=np.arange(1, 9, dtype=float).reshape(4, 2) / 4,
                         b=np.array([[1, -1, 2], [1, 2, 1], [-1, 1, 2], [2, 1, -1]], dtype=float),
                         c=np.ones((4, 3)), skip=.25)

    def test_hand_reference(self):
        result = f.recurrence(**{k: v[:1] if hasattr(v, "shape") else v for k, v in self.args.items()})
        expected = np.array([[.125, -.125, .25], [.25, -.25, .5]])
        np.testing.assert_array_equal(result["states"][0], expected)
        np.testing.assert_array_equal(result["output"][0], [0.3125, .625])

    def test_continuous_checkpoint(self):
        for bits, unit in ((None, None), (16, .01), (32, .0001)):
            full = f.recurrence(**self.args, storage_bits=bits, unit=unit)
            first_args = {k: v[:2] if hasattr(v, "shape") else v for k, v in self.args.items()}
            last_args = {k: v[2:] if hasattr(v, "shape") else v for k, v in self.args.items()}
            one = f.recurrence(**first_args, storage_bits=bits, unit=unit)
            two = f.recurrence(**last_args, storage_bits=bits, unit=unit,
                               checkpoint=one["checkpoint"], position=2)
            np.testing.assert_array_equal(full["states"], np.concatenate((one["states"], two["states"])))
            np.testing.assert_array_equal(full["output"], np.concatenate((one["output"], two["output"])))

    def test_chunk_reset_is_detected(self):
        full = f.recurrence(**self.args)
        last_args = {k: v[2:] if hasattr(v, "shape") else v for k, v in self.args.items()}
        reset = f.recurrence(**last_args)
        self.assertGreater(f.metric(reset["states"], full["states"][2:])["max_abs"], .01)

    def test_stale_epoch_rejected(self):
        checkpoint = f.recurrence(**self.args)["checkpoint"]
        with self.assertRaisesRegex(ValueError, "epoch"):
            f.recurrence(**self.args, checkpoint=checkpoint, position=4, epoch=1)

    def test_wrong_position_rejected(self):
        checkpoint = f.recurrence(**self.args)["checkpoint"]
        with self.assertRaisesRegex(ValueError, "position"):
            f.recurrence(**self.args, checkpoint=checkpoint, position=3)

    def test_wrong_unit_rejected(self):
        checkpoint = f.recurrence(**self.args, storage_bits=16, unit=.1)["checkpoint"]
        with self.assertRaisesRegex(ValueError, "format/unit"):
            f.recurrence(**self.args, storage_bits=16, unit=.2, checkpoint=checkpoint, position=4)

    def test_ties_even_and_saturation(self):
        args = dict(a=np.zeros(1), dt=np.ones(1), x=np.ones((1, 1)),
                    b=np.array([[.5, 1.5, 2.5, -.5, -1.5, 40000, -40000]]),
                    c=np.ones((1, 7)), skip=0)
        result = f.recurrence(**args, storage_bits=16, unit=1)
        np.testing.assert_array_equal(result["codes"][0], [[0, 2, 2, 0, -2, 32767, -32768]])
        self.assertEqual(result["saturations"].tolist(), [2])

    def test_future_inputs_do_not_change_published_prefix(self):
        result = f.recurrence(**self.args, storage_bits=16, unit=.01)
        other = copy.deepcopy(self.args)
        other["x"][-1] *= 100
        future = f.recurrence(**other, storage_bits=16, unit=.01)
        np.testing.assert_array_equal(result["codes"][:-1], future["codes"][:-1])

    def test_frozen_calibration_unit(self):
        unit = f.calibrated_unit(np.array([.25, -.125]), 16)
        self.assertEqual(unit, 2 ** -16)
        a = f.recurrence(**self.args, storage_bits=16, unit=unit)
        self.assertGreater(a["saturations"].sum(), 0)
        self.assertEqual(a["checkpoint"]["unit"], unit)

    def test_bad_chunks_and_domains(self):
        for chunks in ([1, 2], [0, 4], [2, -1, 3]):
            with self.assertRaises(ValueError):
                f.recurrence(**self.args, chunks=chunks)
        bad = copy.deepcopy(self.args)
        bad["a"][0] = 1.1
        with self.assertRaisesRegex(ValueError, "domain"):
            f.recurrence(**bad)
        bad["a"][0] = np.nan
        with self.assertRaisesRegex(ValueError, "non-finite"):
            f.recurrence(**bad)


class ProjectionAndCostTests(unittest.TestCase):
    def test_complete_k_int32_and_scale_contract(self):
        cal = np.array([[1, 2, 3, 4], [-2, -1, 1, 2]], dtype=float)
        evaluation = np.array([[100, 2, 1, 4], [1, -2, -3, 4]], dtype=float)
        w = np.array([[1, 2, -1, 3], [1, 1, 1, 1]], dtype=float)
        results, arrays = f._w8a8(cal, evaluation, w)
        self.assertGreater(results[0]["activation_saturations"], 0)
        self.assertEqual(results[1]["activation_saturations"], 0)
        for scheme in ("cal_static_tensor", "eval_dynamic_row"):
            qx = arrays[scheme + "_input_code"].astype(np.int64)
            qw = arrays["weight_code"].astype(np.int64)
            expected = np.array([[sum(int(v) * int(z) for v, z in zip(row, col)) for col in qw] for row in qx])
            np.testing.assert_array_equal(expected, arrays[scheme + "_accumulator"])

    def test_config_inventory_no_fp32_divide_four(self):
        cfg = dict(mamba_n_heads=32, mamba_d_head=128, mamba_d_state=256, mamba_d_ssm=4096,
                   mamba_n_groups=1, mamba_d_conv=4, hidden_size=2560, num_hidden_layers=32,
                   num_key_value_heads=2, head_dim=128)
        s32, s16 = f.costs(cfg, 72), f.costs(cfg, 72, state_bits=16)
        self.assertEqual(s32["state_payload_per_layer"], 4 * 1024 * 1024)
        self.assertEqual(s32["state_payload_all_layers"], 128 * 1024 * 1024)
        self.assertEqual(s32["conv_payload_per_layer"], 73728)
        self.assertEqual(s32["kv_payload_per_layer"], 147456)
        self.assertEqual(s16["state_units_per_layer"], 64)
        self.assertEqual(s16["conv_payload_per_layer"], s32["conv_payload_per_layer"])
        self.assertEqual(s32["mamba_gated_norm_raw_gate_gamma_payload_fp32"], 49152)
        self.assertEqual(f.costs(cfg, 72, state_format="S32")["state_units_per_layer"], 64)

    def test_nonfinite_config_is_explicit_string(self):
        value = f._finite_json({"limits": (0, float("inf"))})
        self.assertEqual(json.dumps(value, allow_nan=False), '{"limits": [0, "inf"]}')


if __name__ == "__main__":
    unittest.main()
