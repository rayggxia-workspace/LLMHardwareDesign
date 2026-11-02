"""Supply-only model conversion and full timing-view binding controls."""
from copy import deepcopy
import unittest

from audit import Invalid, sha, validate_supply_conversion


def conversion():
    raw = 'library(L) { cell(C) { pin("d") { direction : input; }\n'
    edits = []
    for name, kind in (("VDD", "primary_power"), ("VSS", "primary_ground")):
        original = f'pin("{name}") {{ direction : input; capacitance : 0.0000; max_transition : 0.199; }}'
        replacement = f'pg_pin("{name}") {{ voltage_name : "{name}"; pg_type : {kind}; }}'
        raw += original + '\n'
        edits.append({"name": name, "pg_type": kind, "original": original, "replacement": replacement})
    raw += '}}\n'
    corrected = raw
    for edit in edits:
        corrected = corrected.replace(edit["original"], edit["replacement"])
    record = {"schema": "block-v1-supply-model-correction/1", "passed": True,
              "exact_inverse_reconstruction": True, "all_other_model_bytes_unchanged": True,
              "original_sha256": sha(raw.encode()), "corrected_sha256": sha(corrected.encode()), "edits": edits}
    return raw, corrected, record


class SupplyConversionControls(unittest.TestCase):
    def test_exact_supply_only_reconstruction(self):
        validate_supply_conversion(*conversion())

    def test_rehashed_signal_change_rejected(self):
        raw, corrected, record = conversion()
        corrected = corrected.replace('pin("d") { direction : input;', 'pin("d") { direction : output;')
        record["corrected_sha256"] = sha(corrected.encode())
        with self.assertRaisesRegex(Invalid, "non-supply model bytes"):
            validate_supply_conversion(raw, corrected, record)

    def test_supply_group_with_nonzero_load_or_extra_function_rejected(self):
        for old, new in (("capacitance : 0.0000", "capacitance : 0.001"),
                         ("max_transition : 0.199;", 'max_transition : 0.199; function : "d";')):
            raw, corrected, record = conversion()
            record["edits"][0]["original"] = record["edits"][0]["original"].replace(old, new)
            with self.assertRaisesRegex(Invalid, "changed semantics"):
                validate_supply_conversion(raw, corrected, record)

    def test_wrong_power_type_missing_edit_and_false_proof_rejected(self):
        for mutate in (lambda r: r["edits"][0].update(pg_type="primary_ground"),
                       lambda r: r["edits"].pop(), lambda r: r.update(exact_inverse_reconstruction=False)):
            raw, corrected, record = conversion()
            mutate(record)
            with self.assertRaises(Invalid):
                validate_supply_conversion(raw, corrected, record)

    def test_digest_mismatch_rejected(self):
        raw, corrected, record = conversion()
        record["original_sha256"] = "0"*64
        with self.assertRaisesRegex(Invalid, "hashes"):
            validate_supply_conversion(raw, corrected, record)


if __name__ == "__main__":
    unittest.main()
