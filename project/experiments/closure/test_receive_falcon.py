import copy
from fractions import Fraction
import math
from pathlib import Path
import tempfile
import unittest

import numpy as np

import receive_falcon as receiver


def simple_transactions(length, bits, policy, exponent):
    """Independent tiny all-ones physical recurrence, literal scalar oracle."""
    heads, dim, n = 2, 2, 3
    shape = (heads, dim, n)
    state = np.zeros(shape, np.int64)
    units = [exponent] * heads
    position = epoch = 0
    contract = {"bits": bits, "policy": policy, "heads": heads, "dim": dim, "n": n,
                "injection": "dt20*B12_RNE12_then_x12_RNE(32+state_exp)", "maximum_retries": 8}
    dtype = np.int16 if bits == 16 else np.int32
    tx = {"contract": contract, "tokens": [], "state_sha256": [receiver.array_hash(state.astype(dtype))],
          "rescale_events": [], "checkpoints": []}
    for token in range(length):
        before = receiver.checkpoint(state.astype(dtype), units, epoch, position, contract)
        trial, trial_units = state.copy(), units.copy()
        trial_epoch = epoch
        attempts = []
        committed = False
        for attempt in range(9):
            injection = np.empty(shape, np.int64)
            for h in range(heads):
                value = round(Fraction(1, 2 ** trial_units[h])) if trial_units[h] >= 0 else 1 << -trial_units[h]
                injection[h].fill(value)
            proposal = trial + injection
            counts = np.count_nonzero((proposal < -(1 << (bits - 1))) | (proposal >= 1 << (bits - 1)), axis=(1, 2))
            accepted = not counts.any() or policy == "static_sat"
            attempts.append({"attempt": attempt, "trial_old_sha256": receiver.array_hash(trial),
                             "trial_units": trial_units.copy(), "trial_epoch": trial_epoch,
                             "range_violations": counts.tolist(), "wide_error": None,
                             "stage_hashes": {"dtb_q20_sha256": receiver.array_hash(np.full((heads, n), 1 << 20, np.int32)),
                                              "injection_sha256": receiver.array_hash(injection),
                                              "decay_sha256": receiver.array_hash(trial),
                                              "proposal_sha256": receiver.array_hash(proposal)},
                             "published": accepted, "result": "COMMIT" if accepted else "ABORT"})
            if accepted:
                state = np.clip(proposal, -(1 << (bits - 1)), (1 << (bits - 1)) - 1)
                units, epoch, position = trial_units, trial_epoch, position + 1
                tx["state_sha256"].append(receiver.array_hash(state.astype(dtype)))
                committed = True
                break
            if policy != "guard_rescale":
                break
            for h in np.flatnonzero(counts):
                old = receiver.array_hash(trial[h])
                trial[h] = np.array([[round(Fraction(int(v), 2)) for v in row] for row in trial[h]], np.int64)
                trial_units[h] += 1
                tx["rescale_events"].append({"token": token, "attempt": attempt, "head": int(h),
                                             "old_sha256": old, "new_sha256": receiver.array_hash(trial[h]),
                                             "new_unit_exponent": trial_units[h], "published": False})
            trial_epoch += 1
        after = receiver.checkpoint(state.astype(dtype), units, epoch, position, contract)
        tx["tokens"].append(dict(token=token, before=before, after=after, attempts=attempts, committed=committed))
        if not committed:
            break
    coeff = {"x_q12": np.full((length, heads, dim), 4096, np.int32),
             "b_q12": np.full((length, n), 4096, np.int32),
             "c_q12": np.full((length, n), 4096, np.int32),
             "dt_q20": np.full((length, heads), 1 << 20, np.int32),
             "alpha_q31": np.full((length, heads), 1 << 31, np.uint32)}
    return coeff, tx


class FalconReceiptTests(unittest.TestCase):
    def test_independent_signed_rne_vector(self):
        replay = receiver.Replay()
        values = np.arange(-101, 102, dtype=np.int64)
        for shift in (0, 1, 2, 7, 64):
            answer = replay.shift(values, shift)
            self.assertEqual(answer.tolist(), [round(Fraction(int(v), 1 << shift)) for v in values])

    def test_operand_signedness_and_alpha_one(self):
        e = receiver.Replay()
        np.testing.assert_array_equal(e.multiply(np.array([3], np.int32), np.array([1 << 31], np.uint32)),
                                      np.array([3 << 31], np.int64))
        with self.assertRaisesRegex(ValueError, "left operand width"):
            e.multiply(np.array([1 << 31], np.int64), np.array([1], np.int32))

    def test_full_integer_norm_matches_rational_definition(self):
        x = np.array([[4096, 0, -8192, 4096]], np.int32)
        gamma = np.array([1 << 20, 1 << 19, 1 << 20, 1 << 21], np.int32)
        denominator = math.isqrt((sum(int(v) ** 2 for v in x[0]) // 4 + 17) << 40)
        expected = [round(Fraction(int(v) * int(g) << 12, denominator)) for v, g in zip(x[0], gamma)]
        result = receiver.Replay().norm(x, gamma, 17)
        self.assertEqual(result.tolist(), [expected])

    def test_complete_linear_minimal_integer_scale(self):
        x = np.array([[4096, -4096]], np.int32)
        w = np.array([[127, -127]], np.int8)
        y, a, delta, acc = receiver.Replay().linear(x, w, np.array([1 << 30], np.int32), np.array([1], np.int16))
        self.assertEqual(a.tolist(), [[64, -64]])
        self.assertEqual(delta.tolist(), [6])
        self.assertEqual(acc.tolist(), [[16256]])
        self.assertEqual(y.tolist(), [[1040384]])

    def test_continuous_complete_state_and_epoch_negative(self):
        coeff, transaction = simple_transactions(3, 32, "guard_rescale", 0)
        actual = receiver.scan(receiver.Replay(), coeff, np.zeros(2, np.int16),
                               np.zeros(2, np.int32), 32, "guard_rescale", transaction)
        self.assertEqual(actual["output"].tolist(), [[12288] * 4, [24576] * 4, [36864] * 4])
        self.assertEqual(actual["committed"], 3)
        bad = copy.deepcopy(transaction)
        bad["tokens"][1]["after"]["epoch"] += 1
        with self.assertRaisesRegex(ValueError, "publication"):
            receiver.scan(receiver.Replay(), coeff, np.zeros(2, np.int16),
                          np.zeros(2, np.int32), 32, "guard_rescale", bad)

    def test_guard_retries_atomic_units_and_no_saturation(self):
        coeff, transaction = simple_transactions(3, 16, "guard_rescale", -15)
        actual = receiver.scan(receiver.Replay(), coeff, np.full(2, -15, np.int16),
                               np.zeros(2, np.int32), 16, "guard_rescale", transaction)
        self.assertEqual(actual["output"].tolist(), [[12288] * 4, [24576] * 4, [36864] * 4])
        self.assertEqual(actual["epoch"], 2)
        self.assertEqual(actual["rescale_events"], 4)
        self.assertEqual(actual["saturations"], 0)
        self.assertEqual(actual["units"].tolist(), [[-15, -15], [-14, -14], [-13, -13], [-13, -13]])

    def test_guard_abort_leaves_initial_state_unchanged(self):
        coeff, transaction = simple_transactions(3, 16, "static_guard", -15)
        actual = receiver.scan(receiver.Replay(), coeff, np.full(2, -15, np.int16),
                               np.zeros(2, np.int32), 16, "static_guard", transaction)
        self.assertEqual(actual["committed"], 0)
        self.assertFalse(actual["final"].any())

    def test_runtime_float_bridges_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / "runtime.py"
            for code in ("def f(): return 1 / 2", "def f(): return 0.5", "def f(x): return np.exp(x)", "def f(x): return float(x)"):
                p.write_text(code)
                with self.assertRaises(ValueError):
                    receiver.audit_runtime_source(p)
            p.write_text("def f(x): return math.isqrt(x)\n")
            self.assertTrue(receiver.audit_runtime_source(p)["ast_no_float_bridge"])


if __name__ == "__main__":
    unittest.main()
