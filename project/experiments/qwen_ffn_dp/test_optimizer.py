"""Repeatable optimizer and feedback contract regression."""
import copy
import json
from pathlib import Path
import random
import unittest

from compile_slice import apply_feedback, dp, exhaustive, program
from images import encode_images
from route_feedback import feedback as route_feedback


class OptimizerTest(unittest.TestCase):
    def setUp(self):
        self.manifest = json.loads(Path(__file__).with_name("manifest.json").read_bytes())

    def feedback(self, result="penalty"):
        return {
            "base_id": self.manifest["base_id"],
            "bundle_id": self.manifest["cross_bundle"]["id"],
            "evidence_sha256": "0" * 64,
            "kind": "fixture",
            "result": result,
            "incremental_cost": 100000,
        }

    def test_random_costs(self):
        rng = random.Random(192)
        for _ in range(4096):
            m = copy.deepcopy(self.manifest)
            m["projection_cycles"] = {op: rng.randint(1, 65535) for op in ("gate", "up")}
            m["cross_bundle"].update(estimated_cycles=rng.randrange(65536),
                                     incremental_cost=rng.randrange(65536),
                                     prewired=rng.choice((True, False)))
            self.assertEqual(dp(m), exhaustive(m))

    def test_feedback_reemits_all_outputs(self):
        old = program(dp(self.manifest)[0], self.manifest)
        self.assertEqual(old["plan"]["up_owner"], 1)
        apply_feedback(self.manifest, self.feedback())
        new = program(dp(self.manifest)[0], self.manifest)
        self.assertEqual(new["plan"]["up_owner"], 0)
        self.assertEqual(new["bundles"], [])
        self.assertNotEqual(encode_images(old), encode_images(new))
        self.assertTrue(all(word == 0 for word in encode_images(new)["lc1"]))

    def test_coverage_threshold(self):
        bundle = self.manifest["cross_bundle"]
        coupon = {"base_id": self.manifest["base_id"], "bundle_id": bundle["id"],
                  "scope": "128-bit payload only", "expected_nets": 128}
        for missing, expected_owner in ((0, 1), (21, 1), (22, 0), (128, 0)):
            with self.subTest(missing=missing):
                rows = [f"- up_data_{i} ( P1 A ) ( P0 B )"
                        + (" + ROUTED metal11 ( 1 1 ) ( 1 2 )" if i >= missing else "") + " ;"
                        for i in range(128)]
                raw = ("NETS 128 ;\n" + "\n".join(rows) + "\nEND NETS\n").encode()
                m = copy.deepcopy(self.manifest)
                apply_feedback(m, route_feedback(coupon, raw, 1000))
                self.assertEqual(dp(m)[0].up_owner, expected_owner)

    def test_unproven_failure_is_not_exclusion(self):
        with self.assertRaises(ValueError):
            apply_feedback(self.manifest, self.feedback("proven_impossible"))

    def test_wrong_base_is_rejected(self):
        with self.assertRaises(ValueError):
            apply_feedback(self.manifest, dict(self.feedback(), base_id="other-base"))


if __name__ == "__main__":
    unittest.main()
