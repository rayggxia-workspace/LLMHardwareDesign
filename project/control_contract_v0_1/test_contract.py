"""Independent field/byte-address vectors, not macro numerical tests."""
import copy
import json
import pathlib
import unittest
import contract

HERE = pathlib.Path(__file__).resolve().parent
EXAMPLES = json.loads((HERE / "examples.json").read_text(encoding="utf-8"))["cases"]


def sample(index):
    return copy.deepcopy(EXAMPLES[index]["request"])


def obj(oid, base, size, fmt):
    return dict(object_id=oid, base_bytes=base, capacity_bytes=size,
                length_bytes=size, format=fmt, native_abi_id=65537)


class ContractTests(unittest.TestCase):
    def reject(self, request, phrase):
        with self.assertRaisesRegex(ValueError, phrase):
            contract.check_request(request)

    def test_independent_M_wire_vectors(self):
        vectors = [(3, 59, 0), (4, 0, 0x1ffffd), (5, 57, 0x13f),
                   (6, 0, 0), (10, 32, 0x44884), (11, 1, 0), (12, 11, 0)]
        names = set()
        for op, index, data in vectors:
            readout = op in (3, 5, 12)
            req = dict(profile="P16_M_ONLY", execution=dict(
                resource=0, service=2 if readout else 0, native_op=op,
                completion=1 if readout else 0, native_abi_id=65537,
                native0=index, native1=data & 0xffffffff, native2=data >> 32,
                count=1 if readout else 0, stride_bytes=16 if readout else 0))
            if readout:
                req["execution"]["dst"] = 0
                req["objects"] = [obj(0, 0, 16, 4)]
            result = contract.check_request(req)
            for key, expected in [("cmd_op", op), ("cmd_index", index), ("cmd_data", data)]:
                self.assertEqual(result["proposed_wire_mapping"][key], expected)
            self.assertFalse(result["deployable"])
            names.add(result["service"])
        self.assertEqual(len(names), 7)

    def test_all_four_G_functions(self):
        names = set()
        for fn in range(4):
            req = sample(3)
            req["execution"]["native_op"] = fn
            result = contract.check_request(req)
            self.assertEqual(result["proposed_wire_mapping"]["in_fn"], fn)
            self.assertEqual(result["proposed_wire_mapping"]["in_gated"], 1)
            names.add(result["service"])
        self.assertEqual(len(names), 4)

    def test_feeder_uses_16byte_word_addresses(self):
        req = sample(4)
        wire = contract.check_request(req)["proposed_wire_mapping"]
        self.assertEqual(wire, dict(load_bank=1, load_rows=8, load_tiles=4,
                                   load_a_wide=1, load_b_wide=1, load_reuse_b=0,
                                   load_a_base=0, load_b_base=32))

    def test_B_reuse_needs_no_B_object_but_runtime_state(self):
        req = sample(4)
        req["execution"].update(native3=7, src1=255)
        result = contract.check_request(req)
        self.assertEqual(result["proposed_wire_mapping"]["load_b_base"], 0)
        self.assertEqual(result["proposed_wire_mapping"]["load_reuse_b"], 1)
        self.assertTrue(any("preloaded" in x for x in result["runtime_checks_pending"]))
        self.assertFalse(result["deployable"])

    def test_topology_is_distinct_from_control_resource_mask(self):
        req = sample(3)
        req["profile"] = "P16_M_ONLY"
        self.assertTrue(contract.PROFILES[req["profile"]]["resource_mask"] & (1 << 3))
        self.reject(req, "unconnected route")

    def test_unknown_ABI_service_and_32KiB_profile_reject(self):
        req = sample(0)
        req["execution"]["native_abi_id"] = 1
        self.reject(req, "unregistered native ABI")
        req = sample(0)
        req["execution"].update(resource=1, native_op=0)
        self.reject(req, "unregistered resource/service")
        req = sample(0)
        req["profile"] = "P32_VIA_S"
        self.reject(req, "unregistered profile")

    def test_M_reserved_bits_and_geometry_reject(self):
        for field, value in [("native0", 33), ("native1", 0x4488c),
                             ("native1", 0x44804), ("native1", 0x40884),
                             ("native1", 0x44894), ("native2", 1),
                             ("native3", 1)]:
            req = sample(1)
            req["execution"][field] = value
            self.reject(req, "invalid M|unused native")
        req = sample(0)
        req["execution"]["native1"] = 1 << 21
        self.reject(req, "scale")

    def test_readout_format_and_unsupported_completion_reject(self):
        req = sample(2)
        req["execution"]["completion"] = 0
        self.reject(req, "completion strength")
        req = sample(0)
        req["execution"]["completion"] = 1
        self.reject(req, "completion strength")
        req = sample(2)
        req["execution"]["native1"] = 0x300
        self.reject(req, "rounded read")
        req = sample(2)
        req["objects"][0]["format"] = 1
        self.reject(req, "format mismatch")

    def test_M_RNE_can_preserve_S32_containers_for_G(self):
        req = sample(2)
        req["objects"][0]["format"] = 2
        result = contract.check_request(req)
        self.assertTrue(result["static_fields_valid"])
        self.assertTrue(any("Q5.10" in x for x in result["runtime_checks_pending"]))
        self.assertTrue(any("real S" in x for x in result["runtime_checks_pending"]))

    def test_G_packet_granularity_and_gate_refs(self):
        req = sample(3)
        req["execution"]["count"] = 1
        self.reject(req, "whole S words")
        req = sample(3)
        req["execution"]["native0"] = 0
        self.reject(req, "unused object reference")
        req["execution"]["src1"] = 255
        self.assertTrue(contract.check_request(req)["static_fields_valid"])
        req = sample(3)
        req["execution"]["native1"] = 1
        self.reject(req, "unused native")

    def test_object_capacity_overlap_alias_and_dynamic_reject(self):
        req = sample(3)
        req["objects"][1]["base_bytes"] = 16384
        self.reject(req, "S capacity")
        req = sample(3)
        req["objects"][1]["base_bytes"] = 0
        self.reject(req, "overlap")
        req = sample(3)
        req["execution"]["dst"] = 0
        self.reject(req, "aliased")
        req = sample(3)
        req["objects"][0]["base_reg"] = 0
        self.reject(req, "dynamic objects")
        req = sample(3)
        req["execution"]["count_reg"] = 0
        self.reject(req, "dynamic fields")

    def test_feeder_alignment_extent_and_reserved_reject(self):
        req = sample(4)
        req["objects"][0]["base_bytes"] = 16
        req["objects"][1]["base_bytes"] = 1024
        self.reject(req, "64-byte aligned")
        req = sample(4)
        req["objects"][0]["length_bytes"] = 496
        self.reject(req, "window exceeds")
        req = sample(4)
        req["execution"]["native1"] = 9
        self.reject(req, "feeder fields")
        req = sample(4)
        req["execution"]["native4"] = 1
        self.reject(req, "feeder fields")

    def test_L_EXEC_identity_and_context(self):
        req = sample(0)
        req["instruction"]["a"] = 3
        self.reject(req, "resource mismatch")
        req = sample(0)
        req["instruction"]["c"] = 1
        self.reject(req, "descriptor index mismatch")
        req = sample(0)
        req["execution"]["context_id"] = 1
        self.reject(req, "context0")

    def test_codec_reserved_and_unknown_container_fields(self):
        req = sample(0)
        req["execution"]["flags"] = 1
        self.reject(req, "constant")
        req = sample(0)
        req["execution"]["imaginary_port"] = 1
        self.reject(req, "Unknown")
        req = sample(0)
        req["execution"]["native1"] = -1
        self.reject(req, "Record field width")

    def test_examples_never_claim_hardware_execution(self):
        self.assertEqual(len(contract.SERVICES), 12)
        for case in EXAMPLES:
            result = contract.check_request(case["request"])
            self.assertTrue(result["static_fields_valid"])
            self.assertFalse(result["deployable"])
            self.assertTrue(result["runtime_checks_pending"])


if __name__ == "__main__":
    unittest.main()
