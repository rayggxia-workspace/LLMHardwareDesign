"""Bounded independent oracle and actual artifact-mutation tests only."""
from fractions import Fraction
import math
from pathlib import Path
import tempfile
import unittest

from audit_io74 import (checked, descriptor, divided_rne, load_json, lowered_product,
                        rational_rne, replace_artifact_hash, s8_digits, save_json,
                        shift_rne, square_root, verify_manifest, wire_packets)


class IndependentOracleTests(unittest.TestCase):
    def test_signed_ties_and_exact_fraction(self):
        for n in range(-91, 92):
            for d in range(1, 18):
                self.assertEqual(rational_rne(n, d), round(Fraction(n, d)))
                self.assertEqual(divided_rne(n, d, 16), round(Fraction(n, d)))
        self.assertEqual(shift_rne(-3, 1), -2)
        self.assertEqual(shift_rne(-5, 1), -2)

    def test_bit_square_root(self):
        for n in list(range(256)) + [(1 << 127) - 1, (1 << 128) - 1]:
            self.assertEqual(square_root(n), math.isqrt(n))

    def test_native_s8_and_full_domain_products(self):
        for bits, count in ((8, 1), (16, 3), (32, 5), (64, 9)):
            for n in (-(1 << (bits - 1)), -1, 0, 1, (1 << (bits - 1)) - 1):
                self.assertEqual(len(s8_digits(n, bits)), count)
        product, cost = lowered_product(-(1 << 63), -(1 << 31), 64, 32)
        self.assertEqual(product, 1 << 94)
        self.assertEqual(cost, 45)

    def test_full_domain_readout_requires_72_signed_bits(self):
        value = 256 * (-(1 << 31)) * (-(1 << 31))
        self.assertEqual(checked(value, 72), 1 << 70)
        with self.assertRaises(ValueError):
            checked(value, 71)
        with self.assertRaises(ValueError):
            checked(value, 64)

    def test_packet_leading_offsets_and_fifo(self):
        p = wire_packets(15, 7, 1985)
        self.assertEqual(p, {"payload_bytes": 1985, "wire_bytes": 2064,
                             "packets": 2, "src_beats": 126, "dst_beats": 126,
                             "bus_beats": 129, "max_fifo_bytes": 2016})

    def test_mutation_with_rewritten_sha_reaches_semantic_layer(self):
        with tempfile.TemporaryDirectory(prefix="issue74-audit-") as temp:
            root = Path(temp)
            save_json(root / "payload.json", {"code": 1})
            save_json(root / "manifest.json", {"kind": "tiny", "status": "EXECUTED",
                      "artifacts": {"payload.json": descriptor(root / "payload.json")}})
            verify_manifest(root, kind="tiny", statuses=("EXECUTED",))
            save_json(root / "payload.json", {"code": 2})
            with self.assertRaisesRegex(ValueError, "artifact hash"):
                verify_manifest(root)
            replace_artifact_hash(root, "payload.json")
            verify_manifest(root)
            self.assertNotEqual(load_json(root / "payload.json")["code"], 1)

    def test_duplicate_paths_and_escape_rejected(self):
        with tempfile.TemporaryDirectory(prefix="issue74-audit-") as temp:
            root = Path(temp)
            save_json(root / "x.json", {})
            entry = {"path": "x.json", **descriptor(root / "x.json")}
            save_json(root / "manifest.json", {"artifacts": [entry, entry]})
            with self.assertRaisesRegex(ValueError, "duplicate"):
                verify_manifest(root)
            save_json(root / "manifest.json", {"artifacts": {"../x.json": entry}})
            with self.assertRaisesRegex(ValueError, "escape"):
                verify_manifest(root)


if __name__ == "__main__":
    unittest.main()
