"""Independent integer transport oracle; run on allocated compute node.

This checks B1 K16 packing and tails. It does not claim full-model integer RTL.
"""
import hashlib
import json
import random
import struct
import os

rng = random.Random(250 + int(os.environ.get("SLURM_PROCID", "0")))
cases = []
for length in (1, 7, 8, 9, 15, 16, 17, 127, 128, 129, 2048):
    values = [rng.randrange(-32768, 32768) for _ in range(length)]
    containers = [values[i:i + 8] for i in range(0, length, 8)]
    padded = [struct.pack("<8h", *(container + [0] * (8 - len(container)))) for container in containers]
    beats = []
    for tile in range(0, len(padded), 2):
        pair = padded[tile] + (padded[tile + 1] if tile + 1 < len(padded) else bytes(16))
        beats.extend(struct.unpack("<16h", pair))
    assert beats[:length] == values and all(v == 0 for v in beats[length:])
    # Signed dot result is exactly unchanged for random W8, not merely same bytes.
    weights = [rng.randrange(-128, 128) for _ in values]
    assert sum(a * b for a, b in zip(values, weights)) == sum(a * b for a, b in zip(beats[:length], weights))
    cases.append(dict(elements=length, containers=len(padded), K16_beats=(length + 15) // 16,
                      input_SHA256=hashlib.sha256(b"".join(padded)).hexdigest()))
# Explicit negative guard: row-first 2row format cannot be treated as one rowK16.
rows = [list(range(16)), list(range(100, 116))]
native = [row[tile:tile + 8] for tile in (0, 8) for row in rows]
assert native[0] + native[1] != rows[0]
lease_cases = []
for epoch in range(3):
    for worker in range(3):
        for tile in range(4):
            source = [rng.randrange(-32768, 32768) for _ in range(128)]
            slot = struct.pack("<128h", *source)
            planned = rng.randrange(2, 13)
            completed = 0
            for use in range(planned):
                weights = [[rng.randrange(-128, 128) for _ in source] for _ in range(8)]
                # A K128 tile is loaded once, then32B is replayed8 times/M.
                streamed = []
                for k16 in range(8):
                    streamed.extend(struct.unpack("<16h", slot[k16 * 32:(k16 + 1) * 32]))
                actual = [sum(a * b for a, b in zip(streamed, lane)) for lane in weights]
                expected = [sum(a * b for a, b in zip(source, lane)) for lane in weights]
                assert actual == expected
                completed += 1
                # A temporarilyidle slot cannot be freed before future uses.
                assert (completed == planned) == (use == planned - 1)
            assert completed == planned
            lease_cases.append(dict(epoch=epoch, worker=worker, kk=tile * 128,
                                    planned_uses=planned, completed_uses=completed,
                                    A_copy_B=256, A_replay_B=planned * 256))


class Slot:
    """Independent byte/consumer contract oracle, separate from timing model."""
    def __init__(self, generation, planned):
        self.generation = generation
        self.planned = planned
        self.words = {}
        self.uses = {}
        self.closed = False

    def response(self, generation, word, data):
        assert generation == self.generation and 0 <= word < 16
        assert word not in self.words and len(data) == 16
        self.words[word] = data

    def begin(self, use, w_use):
        assert len(self.words) == 16 and use == w_use
        assert not self.closed and use not in self.uses and len(self.uses) < self.planned
        self.uses[use] = 0

    def consume(self, use, beat):
        assert use in self.uses and self.uses[use] == beat and beat < 8
        self.uses[use] += 1

    def close(self):
        assert len(self.uses) == self.planned
        self.closed = True

    def free(self):
        return self.closed and len(self.uses) == self.planned and all(value == 8 for value in self.uses.values())


def rejected(action):
    try:
        action()
    except AssertionError:
        return
    raise RuntimeError("required contract rejection was not enforced")


slot = Slot(17, 2)
for word in range(3):
    slot.response(17, word, bytes([word] * 16))
rejected(lambda: slot.begin(0, 0))  # partial prefix is not A_READY
rejected(lambda: slot.response(16, 3, bytes(16)))
for word in range(3, 16):
    slot.response(17, word, bytes([word] * 16))
rejected(lambda: slot.response(17, 15, bytes(16)))
rejected(lambda: slot.begin(0, 1))  # stale W record is not a valid JOIN
slot.begin(0, 0)
for beat in range(8):
    slot.consume(0, beat)
assert not slot.free()  # temporarily idle; a planned future use remains
rejected(slot.close)
slot.begin(1, 1)
for beat in range(7):
    slot.consume(1, beat)
slot.close()
assert not slot.free()  # END_USE cannot erase the late final acceptance
slot.consume(1, 7)
assert slot.free()
rejected(lambda: slot.consume(1, 7))
replacement = Slot(18, 1)
rejected(lambda: replacement.response(17, 0, bytes(16)))

print(json.dumps(dict(passed=True, scope="B1 row1 signedS16 transport only", cases=cases,
                     multirow_direct_pairing_rejected=True, tile_lease_cases=lease_cases,
                     protocol_gates=["partial_prefix", "wrong_generation", "duplicate_response", "wrong_W_use",
                                     "planned_future_consumer", "late_last_accept", "duplicate_completion", "late_old_generation"],
                     full_model_numeric=False), indent=2))
