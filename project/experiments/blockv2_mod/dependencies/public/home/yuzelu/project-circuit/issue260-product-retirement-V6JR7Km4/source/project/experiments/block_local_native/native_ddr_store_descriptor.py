"""Encode a selected finite S128-to-DDR COPY send command."""

import struct
import zlib

from native_ddr_load_descriptor import PAYLOAD_BYTES, PROVIDER_ABI, S_BYTES, S_WORD_BYTES


SCHEMAS = {PAYLOAD_BYTES: int.from_bytes(b"DWS8", "little"), 512: int.from_bytes(b"DWS1", "little")}
SCHEMA = SCHEMAS[PAYLOAD_BYTES]
OPERATION = 1
BURSTS = PAYLOAD_BYTES // 64


def ddr_store_provider(*, topology, site, route, regions, payload_bytes=PAYLOAD_BYTES):
    """Bind an acknowledged send COPY to its declared DDR region and burst tags."""
    if type(topology) is not int or not 0 < topology < 2**32:
        raise ValueError("invalid native DDR store topology")
    if type(payload_bytes) is not int or payload_bytes not in SCHEMAS:
        raise ValueError("unsupported native DDR store size")
    regions = tuple(regions)
    if not regions or any(
        type(base) is not int or type(size) is not int or type(tag) is not int or
        base < 0 or base % 64 or size < payload_bytes or size % payload_bytes or base + size > 2**64 or
        tag < 0 or tag + size//64 > 2**64
        for base, size, tag in regions
    ):
        raise ValueError("DDR store needs declared aligned whole-row backing and burst tags")
    for ranges in ([(base, base+size) for base, size, _ in regions],
                   [(tag, tag+size//64) for _, size, tag in regions]):
        ordered = sorted(ranges)
        if any(left[1] > right[0] for left, right in zip(ordered, ordered[1:])):
            raise ValueError("DDR store regions or burst tags overlap")

    def encode(command):
        if (command["op"] != "COPY" or command["route"] != route or
                tuple(command["roles"]) != ("send",) or
                command["required_completion"] != "destination_commit_ack" or
                len(command["read"]) != 1 or len(command["write"]) != 1):
            raise ValueError("DDR store needs a selected send COPY with commit ACK")
        source, = command["read"]
        destination, = command["write"]
        source_address, address = source["address"], destination["address"]
        if (source["site"] != site or destination["site"] != "DDR" or source["value"] != destination["value"] or
                source["bytes"] != payload_bytes or destination["bytes"] != payload_bytes or
                type(source_address) is not int or not 0 <= source_address <= S_BYTES-payload_bytes or
                source_address % S_WORD_BYTES or type(address) is not int):
            raise ValueError("DDR store needs a complete S128-aligned row")
        region = next(((base, tag) for base, size, tag in regions
                       if base <= address <= base+size-payload_bytes and (address-base) % payload_bytes == 0), None)
        if region is None:
            raise ValueError("DDR store destination lacks a declared full-row backing")
        base, first_tag = region
        record = bytearray(128)
        struct.pack_into("<IHHIIH6xQQ", record, 0, SCHEMAS[payload_bytes], len(record), OPERATION, PROVIDER_ABI, topology,
                         source_address//S_WORD_BYTES, address, first_tag+(address-base)//64)
        struct.pack_into("<I", record, 124, zlib.crc32(record[:124]))
        return bytes(record)

    return "destination_commit_ack", encode
