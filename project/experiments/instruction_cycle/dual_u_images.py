"""Decode the compact V2 MC and two U_64 LC images from #220 job 100343."""

import hashlib
from pathlib import Path
import re
import struct


VERSION = 2
TOPOLOGY_ID = 0x01930010
NATIVE_ABI_ID = 0x01930001
CAPACITY_PROFILE_ID = 0x17630001
HEADER_BYTES = 128
PM_BYTES = 16
INSTRUCTION_BYTES = 8
TASK_BYTES = 64
EXECUTION_BYTES = 128
IMAGE_IDS = (19300, 19301, 19302)
OPCODES = {0x10: "G_CALL", 0x11: "G_WAIT", 0x1F: "G_END",
           0x41: "L_EXEC", 0x44: "L_WAIT", 0x4F: "L_END"}
NATIVE_OPS = {0x100: "COMMAND", 0x101: "SEND", 0x102: "RECEIVE", 0x103: "RESERVE"}
# #220 current-control/output.sha256 at a326d04e170cb84d273e96e7906bdf23775a0ca8.
MEM_SHA256 = {
    "mother": "057dfc74775eb04abe568a73867ce6b7e950814353fef0715762660b4d113c6e",
    "local0": "3f901227917a1da87221df02763a12a4f96210e9f7002ab86243d4e17f83c6df",
    "local1": "f1c77f374da2455b9ab602423cd63320468f173cca4c7f323c4f372625296a04",
}


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def memory_bytes(source):
    if isinstance(source, str):
        source = source.encode("ascii")
    lines = source.splitlines()
    require(lines and all(re.fullmatch(rb"[0-9a-fA-F]{32}", row) for row in lines),
            "expected one 128-bit hexadecimal word per .mem line")
    return source, b"".join(int(row, 16).to_bytes(PM_BYTES, "little") for row in lines)


def decode_header(data, image_id, local):
    require(len(data) >= HEADER_BYTES, "truncated image header")
    count, = struct.unpack_from("<I", data, 20)
    execution_count, = struct.unpack_from("<H", data, 32)
    if local:
        require(0 < execution_count <= 32 and count == 2 * execution_count + 1,
                "LC requires one EXEC/WAIT pair per native descriptor plus END")
    else:
        require(count == 4 and execution_count == 0, "expected two MC CALLs, WAIT and END")
    instruction_end = HEADER_BYTES + (count + 1) // 2 * PM_BYTES
    task_offset = instruction_end if local else 0
    execution_offset = task_offset + TASK_BYTES if local else 0
    size = execution_offset + execution_count * EXECUTION_BYTES if local else instruction_end
    expected = bytearray(HEADER_BYTES)
    struct.pack_into("<8sHBBIIII", expected, 0, b"LBCISA01", VERSION, local,
                     HEADER_BYTES // PM_BYTES, size, 0, count, HEADER_BYTES)
    struct.pack_into("<4H9I", expected, 28, local, 0, execution_count, 0, task_offset, 0,
                     execution_offset, 0, count, local, image_id, TOPOLOGY_ID, NATIVE_ABI_ID)
    struct.pack_into("<I", expected, 84, CAPACITY_PROFILE_ID)
    require(len(data) == size and data[:HEADER_BYTES] == expected,
            "unsupported image header, sections or deployment identity")
    require(not any(data[HEADER_BYTES + count * INSTRUCTION_BYTES:instruction_end]),
            "nonzero final compact instruction padding")
    return {"image_id": image_id, "instruction_count": count, "instruction_offset": HEADER_BYTES,
            "instruction_end": instruction_end, "instruction_bytes": INSTRUCTION_BYTES,
            "task_count": local, "task_offset": task_offset, "task_bytes": TASK_BYTES if local else 0,
            "execution_count": execution_count, "execution_offset": execution_offset,
            "execution_bytes": EXECUTION_BYTES if local else 0, "total_bytes": size}


def decode_program(data, metadata, local):
    instructions = []
    for pc in range(metadata["instruction_count"]):
        offset = metadata["instruction_offset"] + pc * INSTRUCTION_BYTES
        word, = struct.unpack_from("<Q", data, offset)
        op, a, b, c = ((word >> shift) & 0xFF for shift in (56, 48, 40, 32))
        immediate = word & 0xFFFFFFFF
        require(op in OPCODES, "unsupported compact opcode at PC {}".format(pc))
        instructions.append({"pc": pc, "op": OPCODES[op], "opcode": op, "a": a, "b": b,
                             "c": c, "x": immediate, "offset": offset,
                             "address": offset // PM_BYTES * PM_BYTES})
    if local:
        for index in range(metadata["execution_count"]):
            execute, wait = instructions[2 * index:2 * index + 2]
            require((execute["op"], execute["a"], execute["c"], execute["x"])
                    == ("L_EXEC", 0, index, 0) and execute["b"] < 8,
                    "unsupported LC EXEC operands or descriptor index at PC {}".format(execute["pc"]))
            require((wait["op"], wait["a"], wait["b"], wait["c"], wait["x"])
                    == ("L_WAIT", 0, 0, 0, 1 << execute["b"]),
                    "LC WAIT does not retire the preceding EXEC token")
        end = "L_END"
    else:
        calls = instructions[:2]
        require({row["a"] for row in calls} == {0, 1} and len({row["b"] for row in calls}) == 2
                and all(row["op"] == "G_CALL" and row["b"] < 8 and row["c"] == row["x"] == 0
                        for row in calls), "MC CALLs must allocate distinct targets and tokens")
        wait = instructions[2]
        require((wait["op"], wait["a"], wait["b"], wait["c"], wait["x"])
                == ("G_WAIT", 0, 0, 0, sum(1 << row["b"] for row in calls)),
                "MC WAIT must retire both CALL tokens")
        end = "G_END"
    require(instructions[-1]["op"] == end and not any(instructions[-1][field] for field in ("a", "b", "c", "x")),
            "invalid compact END")
    return instructions


def validate_task(data, metadata):
    task = bytearray(TASK_BYTES)
    struct.pack_into("<H", task, 0, 1)
    struct.pack_into("<4I", task, 16, metadata["instruction_count"], 1, metadata["image_id"], TOPOLOGY_ID)
    struct.pack_into("<I", task, 44, NATIVE_ABI_ID)
    require(data[metadata["task_offset"]:metadata["execution_offset"]] == task,
            "unsupported LC task descriptor or inconsistent deployment identity")


def s_address(block, word, client):
    return {"block": block, "word": word, "byte_address": word * PM_BYTES,
            "bank": word % 4, "row": word // 4, "client": client}


def decode_record(raw, block, index, offset):
    native_op, = struct.unpack_from("<H", raw, 4)
    native0, native1, native2 = struct.unpack_from("<3I", raw, 64)
    require(native_op in NATIVE_OPS, "unsupported native service {}".format(hex(native_op)))
    expected = bytearray(EXECUTION_BYTES)
    struct.pack_into("<3H", expected, 0, 1, 0, native_op)
    expected[8:12] = b"\xff" * 4
    expected[20:26] = b"\xff" * 6
    struct.pack_into("<I", expected, 56, NATIVE_ABI_ID)
    struct.pack_into("<3I", expected, 64, native0, native1, native2)
    require(raw == expected, "unsupported native descriptor flags or reserved fields")
    op = NATIVE_OPS[native_op]
    row = {"index": index, "address": offset, "op": op, "native_op": native_op,
           "native0": native0, "native1": native1, "native2": native2}
    if op == "COMMAND":
        require(native0 >> 15 == 0 and native0 & 0x1F == 0x18 and native1 >> 20 == 0
                and native2 in (0, 2), "unsupported U_64 E command shape or mode")
        row.update(source_addresses=[s_address(block, native1 & 1023, 1),
                                     s_address(block, (native1 >> 10) & 1023, 1)],
                   destination_address=s_address(block, (native0 >> 5) & 1023, 1),
                   e_opcode=native2, e_shift=0)
    elif op == "SEND":
        require(native0 >> 20 == native1 == native2 == 0, "unsupported stored-link SEND fields")
        row.update(source_address=s_address(block, native0 & 1023, 3),
                   destination_address=s_address(1 - block, (native0 >> 10) & 1023, 2))
    elif op == "RESERVE":
        require(native0 >> 10 == native1 == native2 == 0, "unsupported stored-link RESERVE fields")
        row["destination_address"] = s_address(block, native0 & 1023, 2)
    else:
        require(native0 == native1 == native2 == 0, "unsupported stored-link RECEIVE fields")
    return row


def validate_routes(locals_):
    sends, reserves = [[], []], [[], []]
    for block, local in enumerate(locals_):
        reservation = None
        for row in local["execution"]:
            if row["op"] == "SEND":
                sends[1 - block].append(row["destination_address"])
            elif row["op"] == "RESERVE":
                require(reservation is None, "overlapping stored-link reservations")
                reservation = row["destination_address"]
                reserves[block].append(reservation)
            elif row["op"] == "RECEIVE":
                require(reservation is not None, "RECEIVE without a preceding reservation")
                row["destination_address"] = reservation
                reservation = None
        require(reservation is None, "local program ends with a stored-link reservation")
    require(sends == reserves, "stored-link sends and destination reservations disagree")


def decode_images(mother, local0, local1, frozen=False):
    """Decode .mem content; frozen=True also verifies exact archived file hashes."""
    images, binary_sha, mem_sha = [], {}, {}
    for index, (name, source) in enumerate(zip(MEM_SHA256, (mother, local0, local1))):
        try:
            encoded, data = memory_bytes(source)
            mem_sha[name] = hashlib.sha256(encoded).hexdigest()
            binary_sha[name] = hashlib.sha256(data).hexdigest()
            if frozen:
                require(mem_sha[name] == MEM_SHA256[name], "archive .mem SHA-256 mismatch")
            local = int(index > 0)
            metadata = decode_header(data, IMAGE_IDS[index], local)
            metadata["instructions"] = decode_program(data, metadata, local)
            metadata["execution"] = []
            if local:
                validate_task(data, metadata)
                metadata["block"] = index - 1
                for descriptor in range(metadata["execution_count"]):
                    start = metadata["execution_offset"] + descriptor * EXECUTION_BYTES
                    metadata["execution"].append(decode_record(data[start:start + EXECUTION_BYTES], index - 1,
                                                               descriptor, start))
            images.append(metadata)
        except ValueError as exc:
            raise ValueError("{}: {}".format(name, exc)) from exc
    validate_routes(images[1:])
    return {"version": VERSION, "topology_id": TOPOLOGY_ID, "native_abi_id": NATIVE_ABI_ID,
            "capacity_profile_id": CAPACITY_PROFILE_ID, "image_sha256": binary_sha, "mem_sha256": mem_sha,
            "mc": images[0], "locals": images[1:],
            "ports": {"s_word_bytes": PM_BYTES, "s_banks": 4, "s_words_per_bank": 256,
                      "s_arbiter_clients": ["N", "E", "link_rx", "link_tx"],
                      "stored_links": [{"source": 0, "destination": 1}, {"source": 1, "destination": 0}]}}


def read_images(directory, frozen=False):
    """Read mother.mem, local0.mem and local1.mem from a common directory."""
    root = Path(directory)
    return decode_images(*((root / (name + ".mem")).read_bytes() for name in MEM_SHA256), frozen=frozen)
