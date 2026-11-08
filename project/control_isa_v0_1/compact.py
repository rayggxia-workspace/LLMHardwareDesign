"""Fixed 64-bit ISA encoding and the versioned instruction section."""
from __future__ import annotations

import codec

LEGACY_VERSION = 1
COMPACT_VERSION = 2
VERSIONS = (LEGACY_VERSION, COMPACT_VERSION)
BRANCH_OPS = {"G_BRANCH", "L_BRANCH"}
PC_MAX = 0xffff


def encode(instruction, role):
    """Use the existing ISA for operand legality, then pack the narrower word."""
    legacy = codec.encode_instruction(instruction, role)
    opcode = (legacy >> 120) & 0xff
    if instruction["op"] in BRANCH_OPS:
        reg = (legacy >> 104) & 7
        true_pc, false_pc = (legacy >> 32) & 0xffffffff, legacy & 0xffffffff
        if max(true_pc, false_pc) > PC_MAX:
            raise ValueError("Compact branch target exceeds 16 bits")
        return opcode << 56 | reg << 53 | true_pc << 32 | false_pc << 16
    return opcode << 56 | ((legacy >> 88) & 0xffffff) << 32 | ((legacy >> 32) & 0xffffffff)


def decode(word, role):
    value = codec.integer(word)
    if not 0 <= value < (1 << 64):
        raise ValueError("Compact word must fit in 64 bits")
    opcode = value >> 56
    if opcode in (0x15, 0x4b):
        if value & 0x001f00000000ffff:
            raise ValueError("Nonzero compact branch reserved bits")
        legacy = (opcode << 120 | ((value >> 53) & 7) << 104 |
                  ((value >> 32) & PC_MAX) << 32 | ((value >> 16) & PC_MAX))
    else:
        legacy = opcode << 120 | ((value >> 32) & 0xffffff) << 88 | (value & 0xffffffff) << 32
    return codec.decode_instruction(legacy, role)


def instruction_bytes(version):
    if version not in VERSIONS:
        raise ValueError("Unknown instruction image version")
    return 8 if version == COMPACT_VERSION else 16


def section_size(count, version):
    size = count * instruction_bytes(version)
    return (size + 15) & ~15


def pack_program(program, role, version):
    words = codec.check_program(program, role)
    width = instruction_bytes(version)
    if version == COMPACT_VERSION:
        words = [encode(ins, role) for ins in program]
    payload = b"".join(word.to_bytes(width, "little") for word in words)
    return payload.ljust(section_size(len(program), version), b"\0")


def unpack_program(data, count, role, version):
    width = instruction_bytes(version)
    if len(data) != section_size(count, version) or any(data[count * width:]):
        raise ValueError("Wrong instruction section size or nonzero padding")
    decoder = decode if version == COMPACT_VERSION else codec.decode_instruction
    program = [decoder(int.from_bytes(data[offset:offset + width], "little"), role)
               for offset in range(0, count * width, width)]
    codec.check_program(program, role)
    return program


def pack_header(values, version):
    instruction_bytes(version)
    legacy = codec.pack_record("image_header", values)
    return legacy[:8] + version.to_bytes(2, "little") + legacy[10:]


def unpack_header(data):
    if len(data) != 128:
        raise ValueError("Wrong image header length")
    version = int.from_bytes(data[8:10], "little")
    instruction_bytes(version)
    fields = codec.unpack_record("image_header", data[:8] + b"\x01\x00" + data[10:])
    return dict(fields, version=version)
