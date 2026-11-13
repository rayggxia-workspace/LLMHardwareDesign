"""Exact PR249 LUT257 SiLU and RNE gate multiply; standard-library oracle."""
import json
from pathlib import Path

TABLE = json.loads(Path(__file__).with_name("lut_q16.json").read_text())
LIMIT = 16 << 16


def rne(value, shift):
    q, rem = divmod(int(value), 1 << shift)
    return q + int(shift > 0 and (2*rem > 1 << shift or 2*rem == 1 << shift and q % 2))


def activation(gate):
    if gate <= -LIMIT:
        return 0
    if gate >= LIMIT:
        return gate
    idx, frac = divmod(gate + LIMIT, 8192)
    return TABLE[idx] + rne((TABLE[idx+1]-TABLE[idx])*frac, 13)


def packet(gates, ups, gated, mask):
    """Atomic packet fault: zero mask or any active lane overflow zeros all data."""
    result, error = [0, 0], mask == 0
    for lane in range(2):
        if mask & (1 << lane):
            act = activation(gates[lane])
            value = rne(act*ups[lane], 16) if gated else act
            if not -(1 << 31) <= value < 1 << 31:
                error = True
            else:
                result[lane] = value
    return ([0, 0] if error else result), error
