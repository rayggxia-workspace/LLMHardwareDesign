"""Assemble the first two-block native program from its address/operation plan."""
import argparse
from pathlib import Path
import sys

from stage import ABI, TOPOLOGY

COMMAND, SEND, RECEIVE, RESERVE = range(0x100, 0x104)


def command(lane, meta, source=(), dst=None):
    fields = lane | len(source) << 2
    if dst is not None:
        fields |= 16 | dst << 5
    return dict(native_op=COMMAND, native0=fields,
                native1=sum(addr << (10*i) for i, addr in enumerate(source)), native2=meta)


def build(assemble, fault=False, kind=-1):
    c_in, u_in, u_gamma, u_eps, u_out, c_return, c_result = 40, 40, 20, 21, 41, 41, 42
    ops = [
        [dict(native_op=RESERVE, native0=c_return),
         dict(native_op=SEND, native0=c_in | u_in << 10),
         dict(native_op=RECEIVE),
         command(0, 15 if fault else 0, (c_in, c_return), c_result),
         command(2, 0, (43,)), command(2, 2, (), 44)],
        [dict(native_op=RESERVE, native0=u_in),
         dict(native_op=RECEIVE),
         command(1, 0x100, (u_eps,)), command(1, 0x81, (u_in,)),
         command(1, 2), command(1, 0x85, (u_in, u_gamma), u_out),
         dict(native_op=SEND, native0=u_out | c_return << 10)],
    ]
    mother_program = [dict(op="G_CALL", a=0, b=2, c=0),
                                 dict(op="G_CALL", a=1, b=3, c=0),
                                 dict(op="G_WAIT", x=12), dict(op="G_END")]
    if kind >= 0:
        programs = {
            1: [command(1, 9, (12, 13), 14), command(0, 0, (14, 13), 15)],
            3: [dict(native_op=0x110, native0=34 | 4 << 21),
                dict(native_op=0x111, native0=10, native1=0x9214),
                dict(native_op=0x111, native0=10, native1=0x9210),
                dict(native_op=0x111, native0=5 | 1 << 10 | 8 << 12, native1=0x101),
                dict(native_op=0x112, native0=12 | 13 << 10 | 14 << 20)],
            4: [dict(native_op=0x120, native0=12 | 1 << 10, native1=0x01000007),
                dict(native_op=0x121)],
        }
        ops[0] = programs[kind]
        mother_program = [mother_program[0], dict(op="G_WAIT", x=4), mother_program[-1]]
    topology = TOPOLOGY if kind < 0 else TOPOLOGY + kind + 1
    mother = assemble("mother", mother_program, {}, 19300, 0, ABI, topology)
    local = []
    for block, rows in enumerate(ops):
        program = []
        for i, row in enumerate(rows):
            program += [dict(op="L_EXEC", a=0, b=0, c=i), dict(op="L_WAIT", x=1)]
            row.update(resource=0, service=0, native_abi_id=ABI)
        program += [dict(op="L_END")]
        block_type = (2 if kind < 0 else kind) if block == 0 else 0
        task = dict(block_type=block_type, entry_pc=0, max_steps=len(program), required_resources=1,
                    program_image_id=19301+block, topology_id=topology, native_abi_id=ABI)
        local.append(assemble("local", program, dict(task=[task], execution=rows),
                              19301+block, 1, ABI, topology))
    return (mother, *local)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("staged", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--fault", action="store_true")
    parser.add_argument("--kind", type=int, choices=(-1, 1, 3, 4), default=-1)
    args = parser.parse_args()
    sys.path.insert(0, str(args.staged / "project/control_p_compute_v0_1"))
    from run_a2 import assemble, mem
    args.output.mkdir(parents=True, exist_ok=True)
    for name, image in zip(("mother", "local0", "local1"), build(assemble, args.fault, args.kind), strict=True):
        mem(args.output / f"{name}.mem", image)
        print(len(image)//16)


if __name__ == "__main__":
    main()
