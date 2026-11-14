"""Decode the frozen single-P A2 subset of the 128-bit control-image ABI.

Format and native descriptor rules come from the #179 run at
6ab1271409d7824480cd05326094bb5d515167d6, specifically
project/control_isa_v0_1/isa.json and
project/control_rtl_min_v0_1/m_dot_store_desc.svh. The A2 bench and
block_local_s_macro.sv bind the decoded addresses to the physical ports.
"""

import hashlib
from pathlib import Path
import struct


VERSION = 1
ABI = 0x00017901
TOPOLOGY = 0x1764A201
CAPACITY_PROFILE = 0x17630001
NATIVE_OP = 0x0080
WORD_BYTES = 16
HEADER_BYTES = 128
PROGRAM_BYTES = 3 * WORD_BYTES
TASK_BYTES = 64
DESCRIPTOR_BYTES = 128


def require(condition, message):
    if not condition:
        raise ValueError(message)


def image_header(image, role):
    local = role == 1
    task_offset = HEADER_BYTES + PROGRAM_BYTES if local else 0
    exec_offset = task_offset + TASK_BYTES if local else 0
    image_bytes = HEADER_BYTES + PROGRAM_BYTES + (TASK_BYTES + DESCRIPTOR_BYTES if local else 0)
    name = "LC" if local else "MC"
    require(len(image) == image_bytes, name + " image length disagrees with the A2 layout")
    image_id, = struct.unpack_from("<I", image, 60)
    require(image_id == 17901 + role, name + " image ID does not match the frozen A2 deployment")

    expected = bytearray(HEADER_BYTES)
    struct.pack_into("<8sHBBIIII", expected, 0, b"LBCISA01", VERSION, role, HEADER_BYTES // WORD_BYTES,
                     image_bytes, 0, 3, HEADER_BYTES)
    struct.pack_into("<4H9I", expected, 28, int(local), 0, int(local), 0, task_offset, 0,
                     exec_offset, 0, 3, int(local), image_id, TOPOLOGY, ABI)
    struct.pack_into("<I", expected, 84, CAPACITY_PROFILE)
    require(image[:HEADER_BYTES] == expected, name + " header has an unsupported version, layout or binding")
    return image_id, task_offset, exec_offset


def program(image, names, opcodes):
    decoded = []
    for pc, (name, opcode) in enumerate(zip(names, opcodes)):
        word = int.from_bytes(image[HEADER_BYTES + pc * WORD_BYTES:HEADER_BYTES + (pc + 1) * WORD_BYTES],
                              "little")
        a, b, c = ((word >> shift) & 0xFF for shift in (104, 96, 88))
        x = (word >> 32) & 0xFFFFFFFF
        # Both CALL and EXEC admit only the resident target/resource and table entry 0.
        canonical = opcode << 120
        if pc == 0:
            require(b < 8, name + " token exceeds the eight hardware slots")
            canonical |= b << 96
        elif pc == 1:
            canonical |= (1 << decoded[0]["b"]) << 32
        require(word == canonical, name + " at PC {} has unsupported operands or opcode".format(pc))
        decoded.append({"op": name, "a": a, "b": b, "c": c, "x": x})
    return decoded


def task_record(raw, image_id):
    expected = bytearray(TASK_BYTES)
    struct.pack_into("<H", expected, 0, VERSION)
    struct.pack_into("<4I", expected, 16, 3, 1, image_id, TOPOLOGY)
    struct.pack_into("<I", expected, 44, ABI)
    require(raw == expected, "LC task record disagrees with the A2 image identity or resource binding")


def execution_record(raw):
    native, = struct.unpack_from("<I", raw, 64)
    a_word, b_word, dst_word = ((native >> shift) & 0x3FF for shift in (0, 10, 20))
    expected = bytearray(DESCRIPTOR_BYTES)
    struct.pack_into("<H", expected, 0, VERSION)
    struct.pack_into("<H", expected, 4, NATIVE_OP)
    expected[8:12] = b"\xff" * 4
    expected[20:26] = b"\xff" * 6
    struct.pack_into("<I", expected, 56, ABI)
    struct.pack_into("<I", expected, 64, native & ((1 << 30) - 1))
    require(raw == expected, "LC native execution record has unsupported fields or reserved bits")
    require(a_word % 4 == b_word % 4 == 0, "A2 feeder source address is not line aligned")
    require(len({a_word // 4, b_word // 4, dst_word // 4}) == 3,
            "A2 operand lines and destination must not alias")
    return a_word, b_word, dst_word


def decode_images(mother, local):
    """Validate two A2 binary images and return instructions and port binding."""
    mother_id, _, _ = image_header(mother, 0)
    local_id, task_offset, exec_offset = image_header(local, 1)
    mc_program = program(mother, ("G_CALL", "G_WAIT", "G_END"), (0x10, 0x11, 0x1F))
    lc_program = program(local, ("L_EXEC", "L_WAIT", "L_END"), (0x41, 0x44, 0x4F))
    task_record(local[task_offset:exec_offset], local_id)
    a_word, b_word, dst_word = execution_record(local[exec_offset:])

    return {"version": VERSION, "abi": ABI, "topology": TOPOLOGY, "capacity_profile": CAPACITY_PROFILE,
            "target": mc_program[0]["a"], "mc_token": mc_program[0]["b"], "lc_token": lc_program[0]["b"],
            "service": 0, "native_op": NATIVE_OP, "a_word": a_word, "b_word": b_word, "dst_word": dst_word,
            "mc_instruction_offset": HEADER_BYTES, "lc_instruction_offset": HEADER_BYTES,
            "instruction_bytes": WORD_BYTES, "task_offset": task_offset, "task_bytes": TASK_BYTES,
            "execution_offset": exec_offset, "execution_bytes": DESCRIPTOR_BYTES,
            "mc_program": mc_program, "lc_program": lc_program,
            "image_id": {"mother": mother_id, "local": local_id},
            "image_sha256": {"mother": hashlib.sha256(mother).hexdigest(),
                             "local": hashlib.sha256(local).hexdigest()},
            "ports": {"word_bytes": WORD_BYTES, "banks": 4, "words_per_bank": 256,
                      "wide": {"read_order": ["b", "a"], "b_line": b_word // 4, "a_line": a_word // 4,
                               "banks": [0, 1, 2, 3]},
                      "narrow": {"write_client": 0, "host_client": 3, "dst_bank": dst_word % 4,
                                 "dst_row": dst_word // 4}}}


def read_images(directory):
    """Read mother.bin and local.bin from an A2 case directory."""
    root = Path(directory)
    return decode_images((root / "mother.bin").read_bytes(), (root / "local.bin").read_bytes())
