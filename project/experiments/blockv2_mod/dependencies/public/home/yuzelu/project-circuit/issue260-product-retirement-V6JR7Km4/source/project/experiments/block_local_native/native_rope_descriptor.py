"""Encode one selected resident RoPE row with an explicit E32 numerical contract."""

import struct
import zlib


SCHEMA = int.from_bytes(b"RPE1", "little")
ABI = 0x02500002
OPERATION = 1
ROW_BYTES = 512
WORD_BYTES = 16
S_BYTES = 16384


def rope_provider(*, topology, site, operands, result, shifts, source_exponent, native_exponent, output_exponent):
    """Bind selected S128 addresses for ordered activation, cosine, sine, and output."""
    operands, shifts = tuple(operands), tuple(shifts)
    if (type(topology) is not int or not 0 < topology < 2**32 or len(operands) != 3
            or len(set((*operands, result))) != 4):
        raise ValueError("invalid RoPE route or tensor identities")
    exponents = (source_exponent, output_exponent, native_exponent, -14)
    if (len(shifts) != 6 or any(type(shift) is not int or not -63 <= shift <= 63 for shift in shifts)
            or any(type(exponent) is not int or not -128 <= exponent < 128 for exponent in exponents)):
        raise ValueError("RoPE shift or exponent exceeds the typed service format")
    cos, neg, neg_align, sin, sin_align, out = shifts
    if (source_exponent - 14 + cos != native_exponent or neg + neg_align != 0
            or source_exponent - 14 + sin + sin_align != native_exponent
            or native_exponent + out != output_exponent):
        raise ValueError("inconsistent RoPE fixed-point exponents")

    def word(operand):
        address = operand["address"]
        if (operand["site"] != site or operand["bytes"] != ROW_BYTES or type(address) is not int
                or not 0 <= address <= S_BYTES - ROW_BYTES or address % WORD_BYTES):
            raise ValueError("RoPE requires an aligned 512-byte row in the selected S128 instance")
        return address // WORD_BYTES

    def encode(command):
        if command["op"] != "EXEC" or len(command["read"]) != 3 or len(command["write"]) != 1:
            raise ValueError("RoPE requires three resident reads and one resident write")
        by_value = {operand["value"]: operand for operand in command["read"]}
        output, = command["write"]
        if by_value.keys() != set(operands) or output["value"] != result:
            raise ValueError("RoPE execution operands differ from the registered graph binding")
        windows = [word(by_value[name]) for name in operands] + [word(output)]
        ordered = sorted(windows)
        if any(high - low < ROW_BYTES // WORD_BYTES for low, high in zip(ordered, ordered[1:])):
            raise ValueError("RoPE execution windows overlap")
        record = bytearray(128)
        struct.pack_into("<IHHII4H10b", record, 0, SCHEMA, len(record), OPERATION, ABI, topology,
                         *windows, *shifts, *exponents)
        struct.pack_into("<I", record, 124, zlib.crc32(record[:124]))
        return bytes(record)

    return "service_done", encode
