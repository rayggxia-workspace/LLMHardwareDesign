"""Emit the real MC v3 image and LC native kernel for a three-P FFN bundle."""

import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys
import zlib


def emit(scopes, descriptor_words, assembler, expand, kernel):
    if len(scopes) not in (6, 174, 192) or len(descriptor_words) != len(scopes):
        raise ValueError("expected the two-stripe, complete Gate/Up, or complete FFN bundle")
    base = scopes[0]["address"]
    generation, job, epoch, first_sequence = scopes[0]["scope_owner"]
    if not (generation and job and first_sequence == 1 and base % 128 == 0):
        raise ValueError("invalid deployment identity, sequence, or DDR base")

    expected = []
    for i, (scope, word) in enumerate(zip(scopes, descriptor_words, strict=True)):
        target = i % 3
        address = base + i * 128
        owner = [generation, job, epoch, i // 3 + 1]
        descriptor = int(word, 16).to_bytes(128, "little")
        if (scope["p"] != target or scope["address"] != address or scope["scope_owner"] != owner
                or hashlib.sha256(descriptor).hexdigest() != scope["sha256"]
                or zlib.crc32(descriptor[:124]) != int.from_bytes(descriptor[124:], "little")):
            raise ValueError(f"descriptor {i} differs from the expected order or checksum")
        expected.append(dict(target=target, token=target, reference=address))

    registers = [base & 0xFFFFFFFF, base >> 32, 0x00010080, 0x02510001, 25001, 0x02500002, 0, len(scopes) // 3]
    program = [("MOVI", index, 0, 0, value) for index, value in enumerate(registers)]
    loop_start = len(program)
    for target in range(3):
        program.extend((assembler.call(target), ("ADDI64", 0, 0, 0, 128)))
    program.extend((assembler.wait(7), ("LOOP", 7, 0, 0, loop_start), assembler.END))
    actual, steps = expand(program, 2048)
    if actual != expected:
        raise ValueError("expanded MC v3 program disagrees with the descriptor arena")
    mother = bytearray(assembler.image(program, max_steps=steps + 1))
    struct.pack_into("<I", mother, 64, 25001)
    local = bytes(kernel())
    return bytes(mother), local, dict(
        schema="issue250-three-P-ffn-program/1", generation=generation, job=job, epoch=epoch,
        topology=25001, calls=len(expected), wait_mask=7, loop_iterations=len(scopes) // 3,
        dynamic_instructions=steps, static_instructions=len(program),
        mother_bytes=len(mother), local_bytes_each=len(local), local_crc32=f"{zlib.crc32(local):08x}",
        mother_sha256=hashlib.sha256(mother).hexdigest(), local_sha256=hashlib.sha256(local).hexdigest(),
        expected_terminal_read_bytes=sum(s["records"] * 1088 + 128 for s in scopes),
        expected_terminal_write_bytes=sum(s["committed_words_per_way"] * s["ways"] * 16 for s in scopes),
        descriptor_base=base, calls_in_order=actual,
    )


def hex_image(path, payload):
    path.write_text("".join(f"{int.from_bytes(payload[i:i + 16], 'little'):032x}\n"
                            for i in range(0, len(payload), 16)), encoding="ascii")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--fixture", required=True, type=Path)
    args = p.parse_args()
    experiments = Path(__file__).resolve().parents[1]
    sys.path[:0] = [str(experiments / "mother_control_native"), str(experiments / "shared_x_control")]
    import assemble_cases
    from compile_scope_loops import expand
    from make_lc_kernel import kernel

    path = args.fixture
    oracle = json.loads((path / "oracle.json").read_text(encoding="utf-8"))
    mother, local, manifest = emit(oracle["first_descriptors"], (path / "scopes.hex").read_text().splitlines(),
                                   assemble_cases, expand, kernel)
    hex_image(path / "mother.hex", mother)
    hex_image(path / "local.hex", local)
    (path / "program.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
