"""Bounded reference configuration state model, not hardware or PC execution."""
import copy
import string
import image

ACTIVITY_KEYS = ("tasks", "data", "returns", "contexts", "untagged")


class Loader:
    def __init__(self):
        self.state = "UNLOADED"
        self.valid = {k: False for k in image.TARGETS}
        # A deterministic stand-in for retained/uninitialized program RAM.
        self._ram = {k: bytearray([0xcd] * image.LIMIT_BYTES[r])
                     for k, (r, _) in image.TARGETS.items()}
        self.activity = {k: 0 for k in ACTIVITY_KEYS}
        self.needs_reset_ack = False
        self.generation = 0
        self.manifest = None
        self.expected_digest = None
        self.received = {}
        self.verified = set()

    def _invalidate(self):
        self.valid = {k: False for k in image.TARGETS}
        self.state = "INVALID"

    def _fail(self, message):
        self._invalidate()
        raise ValueError(message)

    def _idle(self):
        image.need(not self.needs_reset_ack and not any(self.activity.values()),
                   "cohort not quiescent/reset acknowledged")

    def begin(self, manifest, expected_manifest_sha256):
        image.need(self.state not in ("RUNNING", "DRAINING", "LOADING"),
                   "BEGIN while active/loading")
        self._idle()
        image.need(image.manifest_digest(manifest) == expected_manifest_sha256,
                   "manifest digest differs from trusted host expectation")
        image.need(set(manifest) == {"schema", "bundle", "topology_id", "native_abi_id",
                    "capacity_profile_id", "images"} and
                   manifest["schema"] == "control-image-bundle/0.1" and
                   isinstance(manifest["bundle"], str) and 1 <= len(manifest["bundle"]) <= 64 and
                   manifest["topology_id"] == image.TOPOLOGY and
                   manifest["native_abi_id"] == image.ABI and
                   manifest["capacity_profile_id"] == image.PROFILE_ID, "BEGIN manifest capability")
        entries = manifest["images"]
        image.need(isinstance(entries, dict) and "mother" in entries and
                   2 <= len(entries) <= 3 and set(entries) <= set(image.TARGETS), "BEGIN targets")
        for target, row in entries.items():
            role = image.TARGETS[target][0]
            image.need(set(row) == {"bytes", "sha256", "program_image_id"} and
                       type(row["bytes"]) is int and 144 <= row["bytes"] <= image.LIMIT_BYTES[role]
                       and row["bytes"] % 16 == 0 and type(row["program_image_id"]) is int
                       and 0 <= row["program_image_id"] < 1 << 32 and
                       isinstance(row["sha256"], str) and len(row["sha256"]) == 64
                       and all(c in string.hexdigits.lower()[:16] for c in row["sha256"]),
                       "BEGIN image declaration")
        # A valid BEGIN is the single-bank cutover: every old slot becomes invalid.
        self._invalidate()
        self.manifest = copy.deepcopy(manifest)
        self.expected_digest = expected_manifest_sha256
        self.received = {k: 0 for k in entries}
        self.verified = set()
        self.generation += 1
        self.state = "LOADING"

    def write16(self, target, offset, data, generation):
        image.need(self.state == "LOADING", "WRITE outside LOADING; committed RAM unchanged")
        if (generation != self.generation or target not in self.received or
            type(offset) is not int or offset != self.received.get(target) or
            not isinstance(data, bytes) or len(data) != 16 or target in self.verified or
            offset < 0 or offset % 16 or
            offset + 16 > self.manifest["images"][target]["bytes"]):
            self._fail("WRITE sequence/target/range/generation")
        self._ram[target][offset:offset+16] = data
        self.received[target] += 16

    def _images(self):
        return {k: bytes(self._ram[k][:r["bytes"]]) for k, r in self.manifest["images"].items()}

    def verify(self, target, generation):
        image.need(self.state == "LOADING", "VERIFY outside LOADING")
        if generation != self.generation or target not in self.received:
            self._fail("VERIFY generation/target")
        row = self.manifest["images"][target]
        if self.received[target] != row["bytes"] or target in self.verified:
            self._fail("VERIFY incomplete/duplicate")
        try:
            data = self._images()[target]
            image.need(image.digest(data) == row["sha256"], "image SHA mismatch")
            parsed = image.parse_image(data, image.TARGETS[target][0])
            image.need(parsed["header"]["program_image_id"] == row["program_image_id"],
                       "verified image ID differs from manifest")
        except ValueError as error:
            self._fail(str(error))
        self.verified.add(target)

    def commit(self, generation):
        image.need(self.state == "LOADING", "COMMIT outside LOADING")
        try:
            image.need(generation == self.generation and self.verified == set(self.received),
                       "COMMIT missing verification/generation")
            self._idle()
            image.need(image.manifest_digest(self.manifest) == self.expected_digest,
                       "manifest changed after BEGIN")
            image.validate_bundle(self.manifest, self._images())
        except ValueError as error:
            self._fail(str(error))
        for target in self.received:
            self.valid[target] = True
        self.state = "READY"

    def start(self, expected_manifest_sha256):
        image.need(self.state == "READY", "START requires READY")
        self._idle()
        image.need(expected_manifest_sha256 == self.expected_digest, "START wrong bundle identity")
        try:
            image.need(image.manifest_digest(self.manifest) == self.expected_digest,
                       "manifest changed after COMMIT")
            image.need(all(self.valid[k] for k in self.received), "START invalid slot")
            image.validate_bundle(self.manifest, self._images())
        except ValueError as error:
            self._fail(str(error))
        self.state = "RUNNING"
        return dict(entry_admitted=True, generation=self.generation, instructions_executed=False,
                    rtl_tested=False)

    def observe_activity(self, **counts):
        image.need(set(counts) == set(ACTIVITY_KEYS) and
                   all(type(v) is int and 0 <= v <= 8 for v in counts.values()),
                   "activity observation needs all five finite counters")
        self.activity = dict(counts)
        if any(counts.values()) and self.state not in ("RUNNING", "DRAINING"):
            self.needs_reset_ack = True
            self._fail("unexpected idle/late-provider activity; cohort reset required")

    def quiesce(self):
        image.need(self.state in ("RUNNING", "READY"), "QUIESCE state")
        self.state = "DRAINING"

    def drained(self):
        image.need(self.state == "DRAINING", "DRAIN_ACK state")
        self._idle()
        self.state = "READY"

    def reset(self):
        # RAM payload and observed activity are deliberately preserved.
        self._invalidate()
        self.needs_reset_ack = True
        self.verified = set()

    def ack_cohort_reset(self, all_providers_reset):
        image.need(self.state == "INVALID" and self.needs_reset_ack
                   and all_providers_reset is True, "cohort RESET_ACK fact required")
        self.activity = {k: 0 for k in ACTIVITY_KEYS}
        self.needs_reset_ack = False

    def abort(self):
        image.need(self.state == "LOADING", "ABORT outside LOADING")
        self._invalidate()


def load_reference(bundle):
    model = Loader()
    manifest = bundle["manifest"]
    model.begin(manifest, bundle["manifest_sha256"])
    generation = model.generation
    for target, raw in bundle["images_hex"].items():
        data = bytes.fromhex(raw)
        for offset in range(0, len(data), 16):
            model.write16(target, offset, data[offset:offset+16], generation)
        model.verify(target, generation)
    model.commit(generation)
    return model
