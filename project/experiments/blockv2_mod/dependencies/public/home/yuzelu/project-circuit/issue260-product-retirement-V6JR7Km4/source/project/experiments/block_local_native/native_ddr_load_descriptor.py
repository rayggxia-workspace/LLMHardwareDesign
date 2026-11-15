"""Encode a selected 512-byte or 8 KiB DDR-to-S128 COPY receive command."""

import struct
import zlib


SCHEMA = int.from_bytes(b"DRL8", "little")
PROVIDER_ABI = 0x02500002
OPERATION = 1
PAYLOAD_BYTES = 8192
S_WORD_BYTES = 16
S_BYTES = 16384


def ddr_load_provider(*, topology, site, route, regions, payload_bytes=PAYLOAD_BYTES):
    """Bind the COPY's selected backing address and destination SRAM window."""
    if type(topology) is not int or not 0 < topology < 2**32:
        raise ValueError("invalid native DDR load topology")
    if type(payload_bytes) is not int or payload_bytes not in (512, PAYLOAD_BYTES):
        raise ValueError("DDR load provider requires one qualified payload length")
    schema = int.from_bytes(b"DRL1", "little") if payload_bytes == 512 else SCHEMA
    regions = tuple(regions)
    if not regions or any(type(base) is not int or type(size) is not int or
                          base < 0 or base % 64 or size < payload_bytes or base + size > 2**64
                          for base, size in regions):
        raise ValueError("DDR load needs declared, aligned source regions")

    def encode(command):
        if (command["op"] != "COPY" or command["route"] != route or
                tuple(command["roles"]) != ("receive",) or
                command["required_completion"] != "destination_commit_ack" or
                len(command["read"]) != 1 or len(command["write"]) != 1):
            raise ValueError("DDR load needs a selected receive COPY with commit ACK")
        source, = command["read"]
        destination, = command["write"]
        source_address, destination_address = source["address"], destination["address"]
        if (source["site"] != "DDR" or destination["site"] != site or
                source["value"] != destination["value"] or
                source["bytes"] != payload_bytes or destination["bytes"] != payload_bytes or
                type(source_address) is not int or source_address % 64 or
                not any(base <= source_address <= base + size - payload_bytes for base, size in regions) or
                type(destination_address) is not int or not 0 <= destination_address <= S_BYTES - payload_bytes or
                destination_address % S_WORD_BYTES):
            raise ValueError("DDR load needs a declared finite DDR backing and an aligned local S128 window")
        record = bytearray(128)
        struct.pack_into("<IHHIIH6xQ", record, 0, schema, len(record), OPERATION, PROVIDER_ABI,
                         topology, destination_address // S_WORD_BYTES, source_address)
        struct.pack_into("<I", record, 124, zlib.crc32(record[:124]))
        return bytes(record)

    return "destination_commit_ack", encode
