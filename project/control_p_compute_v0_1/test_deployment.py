"""Keep the A2-G trial snapshot from being promoted to a production binding."""

import json
import subprocess
import sys
import unittest

from check_deployment import HERE, check


class DeploymentReviewTests(unittest.TestCase):
    def setUp(self):
        self.manifest = json.loads((HERE / "deployment_a1.json").read_bytes())

    def test_trial_evidence(self):
        result = check(self.manifest)
        self.assertEqual(result["trial_source_blobs_verified"], 12)
        self.assertEqual(result["trial_write_ack_sequences_verified"], 5)
        self.assertFalse(result["production_ready"])

    def test_production_preflight_exits_two(self):
        result = subprocess.run(
            [sys.executable, "-B", str(HERE / "check_deployment.py"), "--require-production"],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("cross_block_ack", json.loads(result.stdout)["pending_production"])

    def test_unverified_bindings_are_rejected(self):
        cases = (
            ("Git blob mismatch", ("a2g", "git_blobs", "project/rtl/block_v2/block_v2_m.sv"), "0" * 40),
            ("native_abi_id mismatch", ("a2g", "native_abi_id"), "0x00017901"),
            ("16 KiB A2-G address contract", ("a2g", "private_s", "bytes"), 32768),
            ("completion must precede", ("a2g", "completion"),
             ["g_request_cycle", "g_response_cycle", "write_cycle", "return_cycle",
              "ack_cycle", "terminal_cycle", "result_cycle"]),
            ("production gates are missing", ("production", "cross_block_ack"), None),
            ("without a production review", ("production", "cross_block_data", "binding"), "test fixture"),
        )
        for error, path, value in cases:
            with self.subTest(error=error):
                candidate = json.loads((HERE / "deployment_a1.json").read_bytes())
                field = candidate
                for key in path[:-1]:
                    field = field[key]
                if value is None:
                    del field[path[-1]]
                else:
                    field[path[-1]] = value
                with self.assertRaisesRegex(ValueError, error):
                    check(candidate)


if __name__ == "__main__":
    unittest.main()
