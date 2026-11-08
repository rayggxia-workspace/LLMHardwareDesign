"""Compile and audit the real MC/LC/S/feeder/M integration on the project server."""

import argparse
import json
import math
import os
from pathlib import Path
import struct
import sys

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent
CTRL = PROJECT / "control_rtl_min_v0_1"
sys.path.insert(0, str(CTRL))
sys.path.insert(0, str(PROJECT / "control_image_v0_1"))
from image import pack_image
import run as common

ABI = 0x00017901
TOPOLOGY = 0x1764A201
CAPACITY = 0x17630001
OP = 0x0080
SILU_ABI = 0x00017902
SILU_TOPOLOGY = 0x1764A202
SILU_OP = 0x0081
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


def assemble(role, program, records, image_id, resource_mask, abi, topology, *, instruction_version=1):
    """Use the versioned image assembler under the dedicated experiment ABI."""
    header = dict(entry_pc=0, resource_mask=resource_mask, max_steps=len(program),
                  program_image_id=image_id, topology_id=topology,
                  native_abi_id=abi, capacity_profile_id=CAPACITY)
    return pack_image(role, program, records, header, instruction_version=instruction_version)


def images(a_word, b_word, dst_word, fault, silu=False):
    abi, topology, op = (SILU_ABI, SILU_TOPOLOGY, SILU_OP) if silu else (ABI, TOPOLOGY, OP)
    local_id = 17904 if silu else 17902
    resources = 0x29 if silu else 1  # M, G, private S for the composite service.
    mother = assemble("mother", [dict(op="G_CALL", a=0, b=2, c=0),
                                 dict(op="G_WAIT", x=4), dict(op="G_END")], {},
                      local_id - 1, 0, abi, topology)
    native = a_word | (b_word << 10) | (dst_word << 20)
    if fault == "unaligned":
        native |= 1
    elif fault == "alias":
        native = a_word | (b_word << 10) | ((b_word + 1) << 20)
    elif fault == "reserved":
        native |= 1 << 30
    elif fault == "wrong_operation":
        op = OP
    task = dict(block_type=0, entry_pc=0, max_steps=3, required_resources=resources,
                program_image_id=local_id, topology_id=topology, native_abi_id=abi)
    execution = dict(resource=0, service=0, native_op=op, native_abi_id=abi, native0=native)
    local = assemble("local", [dict(op="L_EXEC", a=0, b=3, c=0),
                               dict(op="L_WAIT", x=8), dict(op="L_END")],
                     dict(task=[task], execution=[execution]), local_id, resources, abi, topology)
    return mother, local


def seed_job(index):
    operands = (
        ((-7, 3, -2, 5, 9, -11, 8, 1),
         (11, -1, 13, 2, -8, 7, 4, -3), (-3, 4, -5, 9, 1, -7, 11, -6)),
        ((-128, 127, -1, 0, 32, -64, 9, 17),
         (-8, -7, 6, 4, -3, 2, -1, 6), (127, -128, 4, 9, 3, -2, 5, -6)),
        ((-128,) * 8, (-128,) * 8, (127,) * 8),
        ((64,) * 8, (-64,) * 8, (64,) * 8),
    )[index]
    a, b0, b1 = (struct.pack("8b", *v) for v in operands)
    return a.ljust(64, b"\0") + (b0 + b1).ljust(64, b"\0") + SENTINEL


def mem(path, data):
    path.write_text("".join(f"{int.from_bytes(data[i:i+16], 'little'):032x}\n"
                            for i in range(0, len(data), 16)), encoding="ascii")


def rne(value, shift):
    quotient, remainder = divmod(value, 1 << shift)
    half = 1 << (shift - 1)
    return quotient + int(remainder > half or remainder == half and quotient & 1)


def silu_reference(value):
    """Recreate the specified quantized interpolation from the SiLU formula."""
    if value < -8192:
        return 0
    if value > 8192:
        return value

    def knot(x):
        return round(x / (1 + math.exp(-x / 1024)))

    low = value // 32 * 32
    base = knot(low)
    return base + rne((knot(min(low + 32, 8192)) - base) * (value - low), 5)


def audit(log, seeds, addresses, stall, status, silu=False):
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
        ignored = {"A", "B", "WHELD", "HELD", "GHOLD_IN", "GHOLD_OUT", "SVC_SAT", "LC_SAT", "MC_SAT"}
        kinds = [kind for _, kind, _ in group if kind not in ignored]
        ran_service = status in (0, 9)
        expected_kinds = ["CALL"]
        if ran_service:
            expected_kinds += ["EXEC", "LOAD", "FED", "CMD", "NATIVE", "CMD", "NATIVE"]
            if silu:
                expected_kinds += ["GIN", "GOUT"]
            if not status:
                expected_kinds += ["WRITE", "ACK"]
            expected_kinds += ["RETURN"]
        assert kinds == expected_kinds + ["TERMINAL", "RESULT", "READBACK"], kinds
        fields = lambda kind: [(cycle, data) for cycle, event, data in group if event == kind]
        single = lambda kind: fields(kind)[0]
        nums = lambda kind: list(map(int, single(kind)[1]))
        call_job, epoch, task, mc_token = nums("CALL")
        assert (call_job, epoch, mc_token) == (job, 1, 2) and task > 0
        assert not result or task > result[-1]["task_sequence"]
        read, written = (128 if ran_service else 0), (0 if status else 16)
        assert nums("TERMINAL") == [job, 1, task, 2, status, read, written]
        assert nums("RESULT") == [job, 1, index + 1, status, read, written]
        assert single("TERMINAL")[0] < single("RESULT")[0] < single("READBACK")[0]
        final = single("READBACK")[1]
        assert list(map(int, final[:2])) == [job, dst_word]
        expected = seed[-16:]
        response = dict(job=job, task_sequence=task, status=status, read_bytes=read, write_bytes=written)
        saturated = 0
        if ran_service:
            # Decode the original seeded S bytes independently of the DUT arithmetic and trace.
            lhs = struct.unpack("8b", seed[:8])
            sums = [sum(a * b for a, b in zip(lhs, struct.unpack("8b", seed[p:p+8])))
                    for p in (64, 72)]
            assert nums("EXEC") == [job, 1, task, 0, 3]
            assert nums("LOAD") == [a_word, b_word] and nums("FED") == [0]
            for kind, raw in (("A", seed[:16]), ("B", seed[64:128])):
                [(cycle, [value])] = fields(kind)
                assert single("LOAD")[0] < cycle < single("FED")[0]
                assert int(value, 16) == int.from_bytes(raw, "little")
            assert [data for _, data in fields("CMD")] == [["10", "9284"], ["5", "102"] if silu else ["3", "0"]]
            assert fields("NATIVE")[0][1] == ["0", "0", "0" * 32]
            holds = []
            if silu:
                rounded = [rne(value, 2) for value in sums]
                quantized = [min(32767, max(-32768, value)) for value in rounded]
                saturated = int(rounded != quantized)
                packed_m = struct.pack("<4i", *quantized, 0, 0)
                assert fields("NATIVE")[1][1] == ["0", str(saturated),
                                                  f"{int.from_bytes(packed_m, 'little'):032x}"]
                x = struct.pack("<2h", *quantized)
                y = [silu_reference(value) for value in quantized] if not status else [0, 0]
                packed_g = struct.pack("<2h", *y)
                assert single("GIN")[1] == ["7" if status else "0", f"{int.from_bytes(x, 'little'):08x}"]
                assert single("GOUT")[1] == [str(int(bool(status))), "0", f"{int.from_bytes(packed_g, 'little'):08x}"]
                assert fields("NATIVE")[1][0] < single("GIN")[0] < single("GOUT")[0] < single("RETURN")[0]
                holds += [("GHOLD_IN", "GIN", stall * 2), ("GHOLD_OUT", "GOUT", stall * 4)]
                response.update(m_q5_10=quantized, g_q5_10=y, saturated=bool(saturated),
                                g_request_cycle=single("GIN")[0], g_response_cycle=single("GOUT")[0],
                                g_input_stall_cycles=stall * 2, g_output_stall_cycles=stall * 4)
                if not status:
                    expected = packed_g.ljust(16, b"\0")
            else:
                expected = struct.pack("<2q", *sums)
                assert fields("NATIVE")[1][1] == ["0", "0", f"{int.from_bytes(expected, 'little'):032x}"]
                response.update(s64=sums)
            assert nums("RETURN") == [job, 1, task, 0, 3, status, read, written]
            assert single("RETURN")[0] < single("TERMINAL")[0]
            response.update(return_cycle=single("RETURN")[0], terminal_cycle=single("TERMINAL")[0],
                            result_cycle=single("RESULT")[0])
            if not status:
                expected_hex = f"{int.from_bytes(expected, 'little'):032x}"
                assert single("WRITE")[1] == [str(dst_word), expected_hex]
                assert single("ACK")[1] == [expected_hex]
                assert single("WRITE")[0] < single("ACK")[0] < single("RETURN")[0]
                if silu:
                    assert single("GOUT")[0] < single("WRITE")[0]
                holds += [("WHELD", "WRITE", stall * 3), ("HELD", "ACK", stall * 6)]
                response.update(write_cycle=single("WRITE")[0], ack_cycle=single("ACK")[0],
                                write_stall_cycles=stall * 3, ack_stall_cycles=stall * 6)
            else:
                assert not fields("WHELD") and not fields("HELD"), "write offered after native error"
            for held, handshake, count in holds:
                assert len(fields(held)) == count
                for cycle, data in fields(held):
                    assert cycle < single(handshake)[0] and data == single(handshake)[1]
        else:
            allowed = {"CALL", "TERMINAL", "RESULT", "READBACK", "LC_SAT", "MC_SAT"}
            assert all(event in allowed for _, event, _ in group), "rejected descriptor issued provider activity"
        if silu:
            for marker, handshake in [("LC_SAT", "TERMINAL"), ("MC_SAT", "RESULT"),
                                      *([("SVC_SAT", "RETURN")] if ran_service else [])]:
                assert fields(marker) == [(single(handshake)[0], [str(saturated)])]
        assert int(final[2], 16) == int.from_bytes(expected, "little"), "private S readback"
        result.append(response)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verilator", default="verilator")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--silu", action="store_true", help="exercise the separate real G profile")
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    obj = out / "obj_dir"
    g_dir = PROJECT / "rtl/block_v2"
    sources = SOURCES + ([g_dir / "block_v2_g.sv"] if args.silu else [])
    flags = ["-DTB_P_SILU", "-I" + str(g_dir)] if args.silu else []
    cmd = [args.verilator, "--binary", "--timing", "--top-module", "tb_p_compute", "-I" + str(CTRL),
           "--Mdir", obj, "-j", env.get("SLURM_CPUS_PER_TASK", "4"), "-o", "sim", *flags, *sources]
    compile_log = out / "compile.log"
    common.run(cmd, out, env, compile_log)
    scenarios = [
        ("single_signed", (4, 8, 12), 0, (0,), None),
        ("boundary_reuse_stall", (1012, 1016, 1023), 2, (0, 1), None),
        ("reject_unaligned", (4, 8, 12), 1, (0,), "unaligned"),
        ("reject_alias", (4, 8, 12), 1, (0,), "alias"),
        ("reject_reserved", (4, 8, 12), 1, (0,), "reserved"),
    ]
    if args.silu:
        scenarios += [
            ("saturation_propagates", (4, 8, 12), 1, (2,), None),
            ("silu_table_edges", (4, 8, 12), 0, (3,), None),
            ("reject_wrong_operation", (4, 8, 12), 1, (0,), "wrong_operation"),
            ("g_error_no_write", (4, 8, 12), 2, (0,), "native_error"),
        ]
    results = []
    for name, addresses, stall, seed_ids, fault in scenarios:
        case = out / name
        case.mkdir()
        mother, local = images(*addresses, fault, args.silu)
        seeds = [seed_job(i) for i in seed_ids]
        jobs = len(seeds)
        for stem, data in (("mother", mother), ("local", local), ("seed", b"".join(seeds))):
            (case / (stem + ".bin")).write_bytes(data)
            mem(case / (stem + ".mem"), data)
        expected = 9 if fault == "native_error" else 5 if fault else 0
        a, b, d = addresses
        launch = [obj / "sim", f"+MOTHER={case / 'mother.mem'}", f"+LOCAL={case / 'local.mem'}",
                  f"+MWORDS={len(mother)//16}", f"+LWORDS={len(local)//16}", f"+SEED={case / 'seed.mem'}",
                  f"+A={a}", f"+B={b}", f"+DST={d}", f"+STALL={stall}", f"+RUNS={jobs}", f"+EXPECT={expected}"]
        if fault == "native_error":
            launch.append("+GFAULT")
        log_path = case / "run.log"
        log = common.run(launch, out, env, log_path)
        assert f"PASS A2 jobs={jobs} status={expected}" in log
        checks = audit(log, seeds, addresses, stall, expected, args.silu)
        results.append(dict(name=name, expected_status=expected, jobs=checks,
                            command=list(map(str, launch)), files_sha256={
                                f.name: common.sha(f.read_bytes()) for f in sorted(case.iterdir())
                            }))
        print(name, "PASS", checks, flush=True)
    if args.silu:
        sources += [g_dir / "block_v2_g_tables.svh"]
    report = dict(schema="control-p-m-silu-store/0.1" if args.silu else "control-p-m-dot-store/0.1",
                  cases=results, abi=SILU_ABI if args.silu else ABI,
                  topology=SILU_TOPOLOGY if args.silu else TOPOLOGY,
                  compile_command=list(map(str, cmd)), compile_log_sha256=common.sha(compile_log.read_bytes()),
                  source_sha256={p.relative_to(PROJECT).as_posix(): common.sha(p.read_bytes()) for p in sources},
                  python=sys.version, verilator=common.run([args.verilator, "--version"], out, env).strip(),
                  full_P_block=False, G_active=args.silu, production_reset=False, physical=False)
    (out / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("PASS A2", len(results), "RTL scenarios", flush=True)


if __name__ == "__main__":
    main()
