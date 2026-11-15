"""Encode a local E32 ADD2 scope over three S128 word ranges."""

import struct
import zlib


def encode_add(*, schema, provider_abi, operation, topology, left, right, destination, words):
    if any(type(value) is not int or not 0 < value < 2**bits for value, bits in (
            (schema, 32), (provider_abi, 32), (operation, 16), (topology, 32))):
        raise ValueError("invalid native ADD2 route identity")
    if type(words) is not int or not 0 < words <= 1024:
        raise ValueError("invalid ADD2 range length")
    sources = (left, right)
    if any(type(start) is not int or not 0 <= start <= 1024 - words
           for start in (*sources, destination)):
        raise ValueError("ADD2 operand exceeds its local SRAM")
    if any(start != destination and abs(start - destination) < words for start in sources):
        raise ValueError("ADD2 output partially overlaps a live input")
    record = bytearray(128)
    struct.pack_into("<IHHIIHHHH", record, 0, schema, 128, operation, provider_abi, topology,
                     left, right, destination, words)
    struct.pack_into("<I", record, 124, zlib.crc32(record[:124]))
    return bytes(record)


def add_provider(*, schema, provider_abi, operation, topology, site):
    """Construct a catalogue provider for a local, same-exponent S32 ADD2 recipe."""
    def encode(command):
        operands = (*command["read"], *command["write"])
        if command["op"] != "EXEC" or len(command["read"]) != 2 or len(command["write"]) != 1:
            raise ValueError("native ADD2 needs two inputs and one output")
        size = operands[0]["bytes"]
        if (type(size) is not int or size <= 0 or size % 16 or
                any(entry["site"] != site or entry["bytes"] != size or entry["address"] % 16
                    for entry in operands)):
            raise ValueError("native ADD2 needs equally sized local S128 ranges")
        left, right, destination = (entry["address"] // 16 for entry in operands)
        return encode_add(schema=schema, provider_abi=provider_abi, operation=operation,
                          topology=topology, left=left, right=right,
                          destination=destination, words=size // 16)

    return "service_done", encode
