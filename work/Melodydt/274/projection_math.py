"""Optional native host arithmetic with the archived projection's event timing."""
import argparse
import ctypes as C
from pathlib import Path
from random import Random
from struct import pack

import native_tlm_projection as projection


Tile = C.c_int16 * 128
Prefix = C.c_int32 * 8


class NativeAccumulator:
    def __init__(self, library):
        self.lib = C.CDLL(str(library))
        self.run = self.lib.accumulate_projection
        self.run.argtypes = [C.c_char_p, C.POINTER(C.c_int16), C.c_int, C.POINTER(C.c_int32), C.c_bool]
        self.run.restype = C.c_int
        self.activation = self.tile = None

    def __call__(self, weights, activation, shift, prefix, head16):
        if activation is not self.activation:
            self.activation = activation
            self.tile = Tile(*activation)
        active = Prefix(*prefix)
        status = self.run(weights, self.tile, shift, active, head16)
        if status:
            raise ValueError(("nonzero ordinary projection record padding", "invalid projection weight scale",
                              "native projection overflow")[status-1])
        prefix[:] = list(active)


def verify(library):
    rng = Random(274)
    candidate = NativeAccumulator(library)
    ref = projection.accumulate

    def result(which, weights, tile, shift, prefix, head16):
        try:
            which(weights, tile, shift, prefix, head16)
        except ValueError as e:
            return str(e)
        return prefix

    for head16 in (False, True):
        count = 64 if head16 else 8
        for i in range(2048):
            tile = tuple(rng.randint(-32768, 32767) for _ in range(128))
            w = bytes(rng.randrange(256) for _ in range(1024))
            scale = [rng.randint(1, 0x7bff if i % 2 else 0x4300) for _ in range(count)]
            if i % 127 == 0:
                scale[0] = 0
            padding = b"" if head16 else bytes([int(i % 257 == 0)]) + bytes(47)
            weights = w + pack(f"<{count}H", *scale) + padding
            shift = rng.randrange(18)
            start = [rng.randint(-100000, 100000) for _ in range(8)]
            expected = result(ref, weights, tile, shift, start.copy(), head16)
            actual = result(candidate, weights, tile, shift, start.copy(), head16)
            if expected != actual:
                raise ValueError(f"projection arithmetic mismatch: head16={head16}, case={i}")
    print("4096 W8A16 and HEAD16 cases matched the archived Python arithmetic", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("library", type=Path)
    verify(parser.parse_args().library)
