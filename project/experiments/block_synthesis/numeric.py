"""Explicit integer layouts and exact native conversion recipes.

Real value = signed raw integer * 2**exponent. Exponents are provided by the
model/quantization producer; merely importing FLOAT never grants this ABI.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Format:
    bits: int
    exponent: int
    lanes: int
    unsigned: bool = False

    def __post_init__(self):
        if self.bits not in (8, 16, 32, 64) or not isinstance(self.exponent, int) or not 1 <= self.lanes <= 128 // self.bits:
            raise ValueError('invalid native record format')

    @classmethod
    def read(cls, value):
        return cls(value['bits'], value['exponent'], value['lanes'], value.get('unsigned', False))


def rne(value, shift):
    if shift < 0:
        raise ValueError('RNE shift must be nonnegative')
    if not shift:
        return value
    q, remainder = divmod(value, 1 << shift)
    half = 1 << (shift - 1)
    return q + (remainder > half or remainder == half and q & 1)


def saturate(value, bits):
    return max(-(1 << (bits - 1)), min((1 << (bits - 1)) - 1, value))


def pack(values, fmt):
    """Explicit compile-time/checkpoint packing, never a free runtime cast."""
    result = []
    for offset in range(0, len(values), fmt.lanes):
        word = 0
        for i, value in enumerate(values[offset:offset + fmt.lanes]):
            low, high = (0, 1 << fmt.bits) if fmt.unsigned else (-(1 << (fmt.bits-1)), 1 << (fmt.bits-1))
            if not low <= value < high:
                raise ValueError('raw value outside declared width')
            word |= (value & ((1 << fmt.bits) - 1)) << (i * fmt.bits)
        result.append(word)
    return result


def unpack(words, fmt, elements):
    if elements < 0 or len(words) != (elements + fmt.lanes - 1) // fmt.lanes:
        raise ValueError('record extent differs')
    result = []
    for word in words:
        if not 0 <= word < 1 << 128:
            raise ValueError('invalid transport word')
        for lane in range(fmt.lanes):
            raw = (word >> (lane * fmt.bits)) & ((1 << fmt.bits) - 1)
            result.append(raw - (1 << fmt.bits) if not fmt.unsigned and raw & (1 << (fmt.bits - 1)) else raw)
    return result[:elements]


def conversion(source, destination):
    """A real E operation, or an explicit rejection; no arbitrary repacker."""
    if source.unsigned or destination.unsigned:
        raise ValueError('unsigned control/data records need their own native operation')
    if source.lanes != destination.lanes:
        raise ValueError('lane reordering/record expansion needs an explicit service')
    shift = destination.exponent - source.exponent
    if source.bits == destination.bits == 16 and abs(shift) <= 31:
        return {'macro': 'E', 'op': 10 if shift >= 0 else 7, 'shift': abs(shift),
                'valid_lanes': source.lanes, 'rounding': 'RNE' if shift >= 0 else 'exact-left-then-saturate'}
    if source.bits == 32 and destination.bits == 16 and source.lanes <= 4 and 0 <= shift <= 31:
        return {'macro': 'E', 'op': 13, 'shift': shift, 'valid_lanes': source.lanes, 'rounding': 'RNE'}
    raise ValueError('no registered native conversion for these formats')


def convert_reference(values, source, destination):
    recipe = conversion(source, destination)
    shift = destination.exponent - source.exponent
    return [saturate(rne(v, shift) if shift >= 0 else v << -shift, destination.bits) for v in values], recipe
