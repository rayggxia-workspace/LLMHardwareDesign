"""Build the 64-bit mother and two P16 local test images."""
import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "control_p_compute_v0_1"))
from run_a2 import assemble, mem

ABI = 0x01790160
TOPOLOGY = 0x01790161
SRAM_WORD = 20


def build():
    sender = [
        dict(native_op=0x110, native0=34 | 4 << 21),
        dict(native_op=0x111, native0=10, native1=0x9214),
        dict(native_op=0x111, native0=10, native1=0x9210),
        dict(native_op=0x111, native0=5 | 1 << 10 | 8 << 12, native1=0x101),
        dict(native_op=0x112, native0=12 | 13 << 10 | 14 << 20),
        dict(native_op=0x101, native0=14 | SRAM_WORD << 10),
    ]
    receiver = [dict(native_op=0x103, native0=SRAM_WORD), dict(native_op=0x102)]
    mother_program = [
        dict(op="G_CALL", a=1, b=3, c=0),
        dict(op="G_CALL", a=0, b=2, c=0),
        dict(op="G_WAIT", x=12), dict(op="G_END"),
    ]
    yield "mother", assemble("mother", mother_program, {}, 179160, 0, ABI, TOPOLOGY,
                             instruction_version=2)
    for block, rows in enumerate((sender, receiver)):
        program = []
        for index, row in enumerate(rows):
            program.extend([dict(op="L_EXEC", a=0, b=0, c=index), dict(op="L_WAIT", x=1)])
            row.update(resource=0, service=0, native_abi_id=ABI)
        program.append(dict(op="L_END"))
        image_id = 179161 + block
        task = dict(block_type=0, entry_pc=0, max_steps=len(program), required_resources=1,
                    program_image_id=image_id, topology_id=TOPOLOGY, native_abi_id=ABI)
        records = dict(task=[task], execution=rows)
        yield f"local{block}", assemble("local", program, records, image_id, 1, ABI, TOPOLOGY,
                                       instruction_version=2)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    for name, image in build():
        mem(args.output / f"{name}.mem", image)
        print(len(image) // 16)
