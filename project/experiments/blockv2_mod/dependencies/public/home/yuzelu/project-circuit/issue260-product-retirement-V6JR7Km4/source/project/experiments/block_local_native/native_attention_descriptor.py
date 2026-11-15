"""Encode a bounded, single-head native causal AttentionCore invocation."""

import struct
import zlib

SCHEMA = int.from_bytes(b"ATT1", "little")
ABI = 0x02500002
ROW_BYTES = 512
WORD_BYTES = 16
S_BYTES = 16384
MAX_CONTEXT = 639


def attention_provider(*, topology, site, query, output, context, position, coefficient,
                       key_base, value_base, score_byte, work_byte):
    if any(type(x) is not int for x in (topology, context, position, coefficient, key_base,
                                       value_base, score_byte, work_byte)):
        raise ValueError("AttentionCore bounds and addresses must be integers")
    if (not 0 < topology < 2**32 or not 1 <= context <= MAX_CONTEXT or position != context - 1
            or not 0 < coefficient <= 2**30 or query == output):
        raise ValueError("AttentionCore requires one causal prefix and an explicit Q30 scale")
    span = context * ROW_BYTES
    if (any(base % 64 or not 0 <= base <= 2**64 - span for base in (key_base, value_base))
            or abs(key_base - value_base) < span):
        raise ValueError("AttentionCore KV regions must be 64-byte aligned and disjoint")

    def encode(command):
        if command["op"] != "EXEC" or len(command["read"]) != 1 or len(command["write"]) != 1:
            raise ValueError("AttentionCore requires one resident Q row and one committed output row")
        read, = command["read"]
        write, = command["write"]
        for operand, name in ((read, query), (write, output)):
            if operand["value"] != name or operand["site"] != site or operand["bytes"] != ROW_BYTES:
                raise ValueError("AttentionCore operand differs from the registered binding")
        windows = ((read["address"], ROW_BYTES), (write["address"], ROW_BYTES),
                   (score_byte, ((context + 127) // 128) * ROW_BYTES), (work_byte, 4096))
        if any(type(base) is not int or base % WORD_BYTES or not 0 <= base <= S_BYTES - size
               for base, size in windows):
            raise ValueError("invalid AttentionCore S128 window")
        ordered = sorted(windows)
        if any(a + width > b for (a, width), (b, _) in zip(ordered, ordered[1:])):
            raise ValueError("AttentionCore operand and scratch windows overlap")
        record = bytearray(128)
        struct.pack_into("<IHHII6HIQQ", record, 0, SCHEMA, len(record), 1, ABI, topology,
                         context, position, read["address"] // WORD_BYTES, score_byte // WORD_BYTES,
                         work_byte // WORD_BYTES, write["address"] // WORD_BYTES,
                         coefficient, key_base, value_base)
        struct.pack_into("<I", record, 124, zlib.crc32(record[:124]))
        return bytes(record)

    return "service_done", encode
