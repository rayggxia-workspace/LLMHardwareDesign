"""Compile and audit the real MC/LC/S/feeder/M integration on the project server."""

import argparse
import json
import os
from pathlib import Path
import struct
import sys

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent
CTRL = PROJECT / "control_rtl_min_v0_1"
sys.path.insert(0, str(CTRL))
sys.path.insert(0, str(PROJECT / "control_image_v0_1"))
from image import SECTIONS
import run as common

ABI = 0x00017901
TOPOLOGY = 0x1764A201
CAPACITY = 0x17630001
OP = 0x0080
SENTINEL = b"\xcd" * 16

SOURCES = [
    CTRL / "mc_min_controller.sv", CTRL / "lc_min_controller.sv", CTRL / "tb_network_pm.sv",
    HERE / "lc_m_dot_store_adapter.sv", HERE / "tb_p_compute.sv",
    *(PROJECT / p for p in ("rtl/block_v2/block_v2_m.sv",
                            "rtl/block_local_s/block_local_s_macro.sv",
                            "rtl/block_local_s/block_local_s_arbiter.sv",
                            "rtl/block_feed_v1/block_feed_s16k.sv",
                            "rtl/block_feed_v1/block_feed_loader.sv")),
]


def assemble(role, program, records, image_id, resource_mask):
    """Use the existing codec under the dedicated, bounded experiment ABI."""
    codec = common.codec
    header = dict(role=int(role == "local"), entry_pc=0, resource_mask=resource_mask,
                  max_steps=len(program), program_image_id=image_id, topology_id=TOPOLOGY,
                  native_abi_id=ABI, capacity_profile_id=CAPACITY)
    records = dict(records, instruction=[
        w.to_bytes(16, "little") for w in codec.check_program(program, role)
    ])
    payload = bytearray()
    for section, size, _ in SECTIONS:
        rows = records.get(section, [])
        header[section + "_count"] = len(rows)
        header[section + "_offset"] = 128 + len(payload) if rows else 0
        for row in rows:
            packed = row if section == "instruction" else codec.pack_record(section, row)
            assert len(packed) == size
            payload.extend(packed)
    header["total_bytes"] = 128 + len(payload)
    return codec.pack_record("image_header", header) + payload


def images(a_word, b_word, dst_word, fault):
    mother = assemble("mother", [dict(op="G_CALL", a=0, b=2, c=0),
                                 dict(op="G_WAIT", x=4), dict(op="G_END")], {}, 17901, 0)
    native = a_word | (b_word << 10) | (dst_word << 20)
    if fault == "unaligned":
        native |= 1
    elif fault == "alias":
        native = a_word | (b_word << 10) | ((b_word + 1) << 20)
    elif fault == "reserved":
        native |= 1 << 30
    task = dict(block_type=0, entry_pc=0, max_steps=3, required_resources=1,
                program_image_id=17902, topology_id=TOPOLOGY, native_abi_id=ABI)
    execution = dict(resource=0, service=0, native_op=OP, native_abi_id=ABI, native0=native)
    local = assemble("local", [dict(op="L_EXEC", a=0, b=3, c=0),
                               dict(op="L_WAIT", x=8), dict(op="L_END")],
                     dict(task=[task], execution=[execution]), 17902, 1)
    return mother, local


def seed_job(index):
    operands = (
        ((-7, 3, -2, 5, 9, -11, 8, 1),
         (11, -1, 13, 2, -8, 7, 4, -3), (-3, 4, -5, 9, 1, -7, 11, -6)),
        ((-128, 127, -1, 0, 32, -64, 9, 17),
         (-8, -7, 6, 4, -3, 2, -1, 6), (127, -128, 4, 9, 3, -2, 5, -6)),
    )[index]
    a, b0, b1 = (struct.pack("8b", *v) for v in operands)
    return a.ljust(64, b"\0") + (b0 + b1).ljust(64, b"\0") + SENTINEL


def mem(path, data):
    path.write_text("".join(f"{int.from_bytes(data[i:i+16], 'little'):032x}\n"
                            for i in range(0, len(data), 16)), encoding="ascii")


def audit(log, seeds, addresses, stall, status):
    events = []
    for line in log.splitlines():
        if line.startswith("A2 "):
            _, cycle, kind, *fields = line.split()
            events.append((int(cycle), kind, fields))
    assert events == sorted(events, key=lambda e: e[0]), "trace order"
    starts = [i for i, event in enumerate(events) if event[1] == "CALL"]
    assert starts and starts[0] == 0 and len(starts) == len(seeds)
    result = []
    a_word, b_word, dst_word = addresses
    for index, (seed, begin, end) in enumerate(zip(seeds, starts, starts[1:] + [len(events)])):
        job = 7 + index
        group = events[begin:end]
        kinds = [kind for _, kind, _ in group if kind not in ("A", "B", "WHELD", "HELD")]
        assert kinds == (["CALL", "EXEC", "LOAD", "FED", "CMD", "NATIVE", "CMD", "NATIVE",
                          "WRITE", "ACK", "RETURN", "TERMINAL", "RESULT", "READBACK"] if not status
                         else ["CALL", "TERMINAL", "RESULT", "READBACK"]), kinds
        fields = lambda kind: [(cycle, data) for cycle, event, data in group if event == kind]
        single = lambda kind: fields(kind)[0]
        nums = lambda kind: list(map(int, single(kind)[1]))
        call_job, epoch, task, mc_token = nums("CALL")
        assert (call_job, epoch, mc_token) == (job, 1, 2) and task > 0
        assert not result or task > result[-1]["task_sequence"]
        read, written = (0, 0) if status else (128, 16)
        assert nums("TERMINAL") == [job, 1, task, 2, status, read, written]
        assert nums("RESULT") == [job, 1, index + 1, status, read, written]
        assert single("TERMINAL")[0] < single("RESULT")[0] < single("READBACK")[0]
        final = single("READBACK")[1]
        assert list(map(int, final[:2])) == [job, dst_word]
        expected = seed[-16:]
        response = dict(job=job, task_sequence=task, status=status, read_bytes=read, write_bytes=written)
        if not status:
            # Decode the original seeded S bytes independently of the DUT arithmetic and trace.
            lhs = struct.unpack("8b", seed[:8])
            sums = [sum(a * b for a, b in zip(lhs, struct.unpack("8b", seed[p:p+8])))
                    for p in (64, 72)]
            expected = struct.pack("<2q", *sums)
            expected_hex = f"{int.from_bytes(expected, 'little'):032x}"
            assert nums("EXEC") == [job, 1, task, 0, 3]
            assert nums("LOAD") == [a_word, b_word] and nums("FED") == [0]
            for kind, raw in (("A", seed[:16]), ("B", seed[64:128])):
                [(cycle, [value])] = fields(kind)
                assert single("LOAD")[0] < cycle < single("FED")[0]
                assert int(value, 16) == int.from_bytes(raw, "little")
            assert [data for _, data in fields("CMD")] == [["10", "9284"], ["3", "0"]]
            assert [data for _, data in fields("NATIVE")] == [["0", "0", "0" * 32], ["0", "0", expected_hex]]
            assert single("WRITE")[1] == [str(dst_word), expected_hex]
            assert single("ACK")[1] == [expected_hex]
            assert nums("RETURN") == [job, 1, task, 0, 3, 0, 128, 16]
            assert len(fields("WHELD")) == stall * 3 and len(fields("HELD")) == stall * 6
            for held, handshake in (("WHELD", "WRITE"), ("HELD", "ACK")):
                for cycle, data in fields(held):
                    assert cycle < single(handshake)[0] and data == single(handshake)[1]
            assert single("WRITE")[0] < single("ACK")[0] < single("RETURN")[0] < single("TERMINAL")[0]
            response.update(s64=sums, write_cycle=single("WRITE")[0], ack_cycle=single("ACK")[0],
                            return_cycle=single("RETURN")[0], terminal_cycle=single("TERMINAL")[0],
                            result_cycle=single("RESULT")[0], write_stall_cycles=stall * 3,
                            ack_stall_cycles=stall * 6)
        else:
            assert len(group) == 4, "rejected descriptor issued provider activity"
        assert int(final[2], 16) == int.from_bytes(expected, "little"), "private S readback"
        result.append(response)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verilator", default="verilator")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    obj = out / "obj_dir"
    cmd = [args.verilator, "--binary", "--timing", "--top-module", "tb_p_compute", "-I" + str(CTRL),
           "--Mdir", obj, "-j", env.get("SLURM_CPUS_PER_TASK", "4"), "-o", "sim", *SOURCES]
    compile_log = out / "compile.log"
    common.run(cmd, out, env, compile_log)
    scenarios = [
        ("single_signed", (4, 8, 12), 0, 1, None),
        ("boundary_reuse_stall", (1012, 1016, 1023), 2, 2, None),
        ("reject_unaligned", (4, 8, 12), 1, 1, "unaligned"),
        ("reject_alias", (4, 8, 12), 1, 1, "alias"),
        ("reject_reserved", (4, 8, 12), 1, 1, "reserved"),
    ]
    results = []
    for name, addresses, stall, jobs, fault in scenarios:
        case = out / name
        case.mkdir()
        mother, local = images(*addresses, fault)
        seeds = [seed_job(i) for i in range(jobs)]
        for stem, data in (("mother", mother), ("local", local), ("seed", b"".join(seeds))):
            (case / (stem + ".bin")).write_bytes(data)
            mem(case / (stem + ".mem"), data)
        expected = 5 if fault else 0
        a, b, d = addresses
        launch = [obj / "sim", f"+MOTHER={case / 'mother.mem'}", f"+LOCAL={case / 'local.mem'}",
                  f"+MWORDS={len(mother)//16}", f"+LWORDS={len(local)//16}", f"+SEED={case / 'seed.mem'}",
                  f"+A={a}", f"+B={b}", f"+DST={d}", f"+STALL={stall}", f"+RUNS={jobs}", f"+EXPECT={expected}"]
        log_path = case / "run.log"
        log = common.run(launch, out, env, log_path)
        assert f"PASS A2 jobs={jobs} status={expected}" in log
        checks = audit(log, seeds, addresses, stall, expected)
        results.append(dict(name=name, expected_status=expected, jobs=checks,
                            command=list(map(str, launch)), files_sha256={
                                f.name: common.sha(f.read_bytes()) for f in sorted(case.iterdir())
                            }))
        print(name, "PASS", checks, flush=True)
    report = dict(schema="control-p-m-dot-store/0.1", cases=results, abi=ABI, topology=TOPOLOGY,
                  compile_command=list(map(str, cmd)), compile_log_sha256=common.sha(compile_log.read_bytes()),
                  source_sha256={p.relative_to(PROJECT).as_posix(): common.sha(p.read_bytes()) for p in SOURCES},
                  python=sys.version, verilator=common.run([args.verilator, "--version"], out, env).strip(),
                  full_P_block=False, G_active=False, production_reset=False, physical=False)
    (out / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("PASS A2", len(results), "RTL scenarios", flush=True)


if __name__ == "__main__":
    main()
