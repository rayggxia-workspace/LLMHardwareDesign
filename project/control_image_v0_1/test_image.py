import copy
import struct
import unittest
import image
import loader

BUNDLES = image.build_bundles()["bundles"]


def bundle(index=2):
    return copy.deepcopy(BUNDLES[index])


def raw(value, target="local0"):
    return bytes.fromhex(value["images_hex"][target])


def replace_header(data, **fields):
    h = image.codec.unpack_record("image_header", data[:128])
    h.update(fields)
    return image.codec.pack_record("image_header", h) + data[128:]


def replace_row(data, section, index=0, **fields):
    h = image.codec.unpack_record("image_header", data[:128])
    size = dict((n, s) for n, s, _ in image.SECTIONS)[section]
    offset = h[section + "_offset"] + index * size
    row = image.codec.unpack_record(section, data[offset:offset+size])
    row.update(fields)
    return data[:offset] + image.codec.pack_record(section, row) + data[offset+size:]


def replace_instruction(data, index, ins):
    return data[:128+index*16] + image.codec.encode_instruction(ins, image.parse_image(data)["role"]).to_bytes(
        16, "little") + data[144+index*16:]


def revise(value, target, data):
    value["images_hex"][target] = data.hex()
    row = value["manifest"]["images"][target]
    row.update(bytes=len(data), sha256=image.digest(data),
               program_image_id=image.parse_image(data)["header"]["program_image_id"])
    value["manifest_sha256"] = image.manifest_digest(value["manifest"])
    return value


def fill(model, value, verify=True):
    for target in value["manifest"]["images"]:
        data = raw(value, target)
        for offset in range(0, len(data), 16):
            model.write16(target, offset, data[offset:offset+16], model.generation)
        if verify:
            model.verify(target, model.generation)


class ImageTests(unittest.TestCase):
    def reject(self, data, pattern="."):
        with self.assertRaisesRegex(ValueError, pattern):
            image.parse_image(data)

    def test_seven_complete_images_and_deterministic_artifact(self):
        self.assertEqual([sum(e["bytes"] for e in b["manifest"]["images"].values())
                          for b in BUNDLES], [384, 544, 1152])
        self.assertEqual(sum(len(b["images_hex"]) for b in BUNDLES), 7)
        import json
        checked_in = json.loads((image.HERE / "bundles.json").read_bytes().decode("utf-8"))
        self.assertEqual(checked_in, image.build_bundles())
        for b in BUNDLES:
            parsed = image.validate_bundle(b["manifest"], {k: raw(b, k) for k in b["images_hex"]})
            self.assertTrue(all(p["header"]["total_bytes"] == len(raw(b, k)) for k, p in parsed.items()))

    def test_independent_empty_mother_header_and_words(self):
        # Manual byte offsets from the published header, independent of pack_record.
        h = bytearray(128)
        h[0:8] = b"LBCISA01"
        struct.pack_into("<HBBIII", h, 8, 1, 0, 8, 176, 0, 3)
        struct.pack_into("<I", h, 24, 128)
        struct.pack_into("<IIII", h, 52, 32, 0, 200, 393400001)
        struct.pack_into("<I", h, 68, 65537)
        struct.pack_into("<I", h, 84, 0x17630001)
        words = bytes.fromhex("00000000000000000000000000000010"
                              "00000000010000000000000000000011"
                              "0000000000000000000000000000001f")
        self.assertEqual(raw(bundle(0), "mother"), bytes(h) + words)

    def test_magic_reserved_header_and_reserved_record_bytes(self):
        d = bytearray(raw(bundle(0), "mother"))
        for offset in (0, 88, 127):
            v = bytearray(d)
            v[offset] ^= 1
            self.reject(bytes(v))
        d = bytearray(raw(bundle(0)))
        d[-1] = 1
        self.reject(bytes(d), "reserved")

    def test_wrong_role_length_and_section_ownership(self):
        d = raw(bundle(1))
        with self.assertRaisesRegex(ValueError, "role"):
            image.parse_image(d, "mother")
        self.reject(replace_header(d, role=0))
        self.reject(replace_header(d, total_bytes=len(d)+16), "length")

    def test_truncation_extra_bytes_and_count_overflow(self):
        d = raw(bundle())
        for v in (d[:-1], d[:-16], d+b"\0"*16,
                  replace_header(d, instruction_count=257),
                  replace_header(d, transfer_count=9)):
            self.reject(v)

    def test_canonical_offsets_disallow_overlap_holes_and_empty_offsets(self):
        d = raw(bundle(1))
        for fields in (dict(instruction_offset=144), dict(task_offset=128),
                       dict(task_offset=177), dict(object_offset=176),
                       dict(execution_offset=256)):
            self.reject(replace_header(d, **fields), "offset|overlap")

    def test_capability_identity_parameters_resources(self):
        d = raw(bundle(1))
        for fields in (dict(native_abi_id=65538), dict(topology_id=1),
                       dict(capacity_profile_id=2), dict(scalar_parameter_words=1),
                       dict(resource_mask=128)):
            self.reject(replace_header(d, **fields))

    def test_entry_step_budget_and_task_identity(self):
        d = raw(bundle(1))
        for v in (replace_header(d, entry_pc=3), replace_header(d, max_steps=2),
                  replace_row(d, "task", max_steps=2),
                  replace_row(d, "task", program_image_id=101),
                  replace_row(d, "task", required_resources=0)):
            self.reject(v)

    def test_unsupported_loop_and_early_END(self):
        d = raw(bundle(1))
        self.reject(replace_instruction(d, 0, dict(op="L_END")), "budget")
        d = raw(bundle(0), "mother")
        self.reject(replace_instruction(d, 0, dict(op="G_END")), "unreachable")
        self.reject(replace_instruction(d, 1, dict(op="G_LOOP", a=0, x=0)), "capability")

    def test_native_service_and_descriptor_reference(self):
        d = raw(bundle(1))
        for v in (replace_row(d, "execution", native_op=10),
                  replace_instruction(d, 0, dict(op="L_EXEC", a=0, b=0, c=1)),
                  replace_instruction(d, 1, dict(op="L_WAIT", x=2))):
            self.reject(v)

    def test_object_masks_transfer_bounds_and_open_obligations(self):
        d = raw(bundle())
        for v in (replace_row(d, "task", input_object_mask=0),
                  replace_row(d, "task", retained_object_mask=1),
                  replace_row(d, "transfer", count_bytes=32),
                  replace_row(d, "transfer", count_reg=0),
                  replace_instruction(d, 2, dict(op="L_DROP", a=0))):
            self.reject(v)

    def test_mismatched_peer_or_route_rejected_even_with_new_digest(self):
        for fields in (dict(edge_id=13), dict(peer_block=1)):
            b = bundle()
            data = replace_row(raw(b, "local1"), "transfer", **fields)
            revise(b, "local1", data)  # local fields alone are legal
            with self.assertRaisesRegex(ValueError, "peer|route"):
                image.validate_bundle(b["manifest"], {k: raw(b, k) for k in b["images_hex"]})

    def test_producer_call_before_READY_and_undeployed_target(self):
        for ins in (dict(op="G_MOVI", a=0, x=1), dict(op="G_CALL", a=2, b=1, c=0)):
            b = bundle()
            data = replace_instruction(raw(b, "mother"), 1 if ins["op"] == "G_MOVI" else 2, ins)
            revise(b, "mother", data)
            with self.assertRaisesRegex(ValueError, "READY|target"):
                image.validate_bundle(b["manifest"], {k: raw(b, k) for k in b["images_hex"]})

    def test_manifest_cannot_mix_images_that_reuse_short_image_id(self):
        b = bundle(0)
        self.assertEqual(image.parse_image(raw(b))["header"]["program_image_id"],
                         image.parse_image(raw(bundle(1)))["header"]["program_image_id"])
        with self.assertRaisesRegex(ValueError, "digest"):
            image.validate_bundle(b["manifest"], {"mother": raw(b, "mother"),
                                                  "local0": raw(bundle(1))})


class LoaderTests(unittest.TestCase):
    def start_loading(self, index=2):
        b = bundle(index)
        m = loader.Loader()
        m.begin(b["manifest"], b["manifest_sha256"])
        return m, b

    def rejected(self, m, action, pattern="."):
        with self.assertRaisesRegex(ValueError, pattern):
            action()
        self.assertEqual(m.state, "INVALID")
        self.assertFalse(any(m.valid.values()))

    def test_all_cohort_slots_commit_atomically_and_START_is_not_execution(self):
        for b in BUNDLES:
            m = loader.load_reference(b)
            self.assertEqual(m.state, "READY")
            self.assertEqual({k for k,v in m.valid.items() if v}, set(b["images_hex"]))
            r = m.start(b["manifest_sha256"])
            self.assertTrue(r["entry_admitted"])
            self.assertFalse(r["instructions_executed"])
            self.assertFalse(r["rtl_tested"])

    def test_partial_image_cannot_verify_or_start(self):
        m, b = self.start_loading(0)
        m.write16("mother", 0, raw(b, "mother")[:16], m.generation)
        with self.assertRaisesRegex(ValueError, "READY"):
            m.start(b["manifest_sha256"])
        self.rejected(m, lambda: m.verify("mother", m.generation), "incomplete")

    def test_verified_one_image_does_not_make_cohort_READY(self):
        m, b = self.start_loading(0)
        d = raw(b, "mother")
        for i in range(0, len(d), 16):
            m.write16("mother", i, d[i:i+16], m.generation)
        m.verify("mother", m.generation)
        self.assertFalse(any(m.valid.values()))
        self.rejected(m, lambda: m.commit(m.generation), "missing")

    def test_wrong_SHA_invalidates_whole_candidate(self):
        m, b = self.start_loading()
        fill(m, b, verify=False)
        m._ram["local0"][128] ^= 1  # fault injection, not a configuration command
        self.rejected(m, lambda: m.verify("local0", m.generation), "SHA")

    def test_write_order_size_target_and_generation_fail_closed(self):
        actions = [lambda m,b: m.write16("mother", 16, b"\0"*16, m.generation),
                   lambda m,b: m.write16("mother", 0, b"\0"*15, m.generation),
                   lambda m,b: m.write16("local2", 0, b"\0"*16, m.generation),
                   lambda m,b: m.write16("mother", 0, b"\0"*16, m.generation-1)]
        for action in actions:
            m, b = self.start_loading()
            self.rejected(m, lambda: action(m,b), "WRITE")

    def test_duplicate_or_post_verify_write_and_duplicate_verify_fail(self):
        m, b = self.start_loading(0)
        m.write16("mother", 0, raw(b,"mother")[:16], m.generation)
        self.rejected(m, lambda: m.write16("mother", 0, raw(b,"mother")[:16], m.generation))
        for action in (lambda m: m.write16("mother", m.received["mother"], b"\0"*16, m.generation),
                       lambda m: m.verify("mother", m.generation)):
            m, b = self.start_loading(0)
            fill(m, b)
            self.rejected(m, lambda: action(m))

    def test_bad_BEGIN_does_not_destroy_READY_cohort(self):
        for fields in (dict(capacity_profile_id=0), dict(bundle="")):
            b = bundle(0)
            m = loader.load_reference(b)
            bad = copy.deepcopy(b["manifest"])
            bad.update(fields)
            with self.assertRaises(ValueError):
                m.begin(bad, image.manifest_digest(bad))
            self.assertEqual(m.state, "READY")
        with self.assertRaisesRegex(ValueError, "trusted"):
            m.begin(b["manifest"], "0"*64)
        self.assertEqual(m.state, "READY")

    def test_valid_BEGIN_is_single_bank_cutover_without_rollback(self):
        b = bundle(0)
        m = loader.load_reference(b)
        m.begin(b["manifest"], b["manifest_sha256"])
        self.assertFalse(any(m.valid.values()))
        m.abort()
        self.assertEqual(m.state, "INVALID")
        with self.assertRaisesRegex(ValueError, "READY"):
            m.start(b["manifest_sha256"])

    def test_running_write_BEGIN_and_wrong_START_do_not_modify_committed_RAM(self):
        b = bundle(0)
        m = loader.load_reference(b)
        before = m._images()
        with self.assertRaisesRegex(ValueError, "identity"):
            m.start("0"*64)
        self.assertEqual(m.state, "READY")
        m.start(b["manifest_sha256"])
        for action in (lambda: m.write16("mother", 0, b"\0"*16, m.generation),
                       lambda: m.begin(b["manifest"], b["manifest_sha256"])):
            with self.assertRaises(ValueError):
                action()
        self.assertEqual(m.state, "RUNNING")
        self.assertEqual(m._images(), before)

    def test_each_drain_obligation_independently_blocks_reload(self):
        for key in loader.ACTIVITY_KEYS:
            b = bundle(0)
            m = loader.load_reference(b)
            m.start(b["manifest_sha256"])
            facts = {k: int(k == key) for k in loader.ACTIVITY_KEYS}
            m.observe_activity(**facts)
            m.quiesce()
            with self.assertRaisesRegex(ValueError, "quiescent"):
                m.drained()
            with self.assertRaises(ValueError):
                m.begin(b["manifest"], b["manifest_sha256"])
            m.observe_activity(**{k: 0 for k in loader.ACTIVITY_KEYS})
            m.drained()
            self.assertEqual(m.state, "READY")

    def test_reset_retains_RAM_but_requires_cohort_ack_and_full_reload(self):
        b = bundle(0)
        m = loader.load_reference(b)
        before = m._images()
        old = m.generation
        m.reset()
        self.assertEqual(m._images(), before)
        self.assertFalse(any(m.valid.values()))
        with self.assertRaisesRegex(ValueError, "acknowledged"):
            m.begin(b["manifest"], b["manifest_sha256"])
        with self.assertRaises(ValueError):
            m.ack_cohort_reset(False)
        m.ack_cohort_reset(True)  # external reset fact, not a synthesized ACK
        with self.assertRaises(ValueError):
            m.start(b["manifest_sha256"])
        m.begin(b["manifest"], b["manifest_sha256"])
        self.rejected(m, lambda: m.write16("mother",0,raw(b,"mother")[:16],old), "generation")

    def test_reset_reload_can_admit_again(self):
        b = bundle(0)
        m = loader.load_reference(b)
        m.reset()
        m.ack_cohort_reset(True)
        m.begin(b["manifest"], b["manifest_sha256"])
        fill(m,b)
        m.commit(m.generation)
        self.assertEqual(m.generation, 2)
        self.assertTrue(m.start(b["manifest_sha256"])["entry_admitted"])

    def test_late_untagged_provider_in_IDLE_requires_reset(self):
        b = bundle(0)
        m = loader.load_reference(b)
        self.rejected(m, lambda: m.observe_activity(tasks=0,data=0,returns=0,contexts=0,untagged=1),
                      "late-provider")
        with self.assertRaisesRegex(ValueError, "quiescent"):
            m.begin(b["manifest"],b["manifest_sha256"])
        m.ack_cohort_reset(True)
        self.assertEqual(m.activity["untagged"],0)

    def test_commit_rechecks_RAM_and_manifest_after_verification(self):
        for fault in ("ram", "manifest"):
            m,b = self.start_loading()
            fill(m,b)
            if fault == "ram":
                m._ram["local1"][128] ^= 1
            else:
                m.manifest["bundle"] = "changed"
            self.rejected(m, lambda: m.commit(m.generation), "digest|changed")

    def test_start_rechecks_RAM_and_manifest_after_commit(self):
        for fault in ("ram", "manifest"):
            b = bundle()
            m = loader.load_reference(b)
            if fault == "ram":
                m._ram["mother"][128] ^= 1
            else:
                m.manifest["bundle"] = "changed"
            self.rejected(m, lambda: m.start(b["manifest_sha256"]), "digest|changed")

    def test_unobserved_activity_is_not_an_implicit_drain(self):
        m,b = self.start_loading(0)
        with self.assertRaisesRegex(ValueError, "all five"):
            m.observe_activity(tasks=0)
        m.abort()
        with self.assertRaisesRegex(ValueError, "state"):
            m.drained()


if __name__ == "__main__":
    unittest.main()
