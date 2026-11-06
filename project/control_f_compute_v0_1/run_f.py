"""Exercise real MC, F LC, G, E and S; independently audit the RTL trace."""
import argparse
from collections import defaultdict
import json
import os
from pathlib import Path
import struct
import sys

from f_images import ABI, TOPOLOGY, images, validate_pair, validate_sources
from run_a2 import CTRL, PROJECT, SOURCES, SENTINEL, common, mem, silu_reference

HERE = Path(__file__).resolve().parent
SCENARIOS = [
    ("g_only", False, (5, 0, 19), 0, (0,), None),
    ("g_only_stall", False, (3, 0, 1023), 2, (0, 1), None),
    ("g_e_add", True, (5, 11, 19), 0, (0,), None),
    ("g_e_saturate_stall", True, (0, 1022, 1023), 2, (1, 2), None),
    ("reject_config_then_load", True, (5, 11, 19), 1, (0,), "BADCFG"),
    ("reject_address_alias", True, (5, 11, 19), 1, (0,), "alias"),
    ("reject_reserved_address", False, (5, 0, 19), 1, (0,), "reserved"),
    ("reject_unknown_operation", True, (5, 11, 19), 1, (0,), "operation"),
    ("reject_wrong_resource", True, (5, 11, 19), 1, (0,), "resource"),
    ("g_error_zero_write", True, (5, 11, 19), 2, (0,), "GFAULT"),
    ("e_error_zero_write", True, (5, 11, 19), 2, (0,), "EFAULT"),
]
RUNTIME_REJECT = {"alias", "reserved", "operation", "resource"}
NATIVE_ERROR = {"GFAULT", "EFAULT"}


def vectors(index):
    return [((-1567, 2863), (-1979, 3121)),
            ((-1388, 9000), (-32760, 32760)),
            ((0, -8192), (171, -78))][index]


def packed(lanes):
    return int.from_bytes(struct.pack("<2h", *lanes), "little")


def seed_words(index):
    x, b = vectors(index)
    # Unused high lanes are deliberately nonzero in S; the adapter must zero
    # them at E's inputs and in the result word.
    return (struct.pack("<2h", *x) + bytes.fromhex("a1" * 12) + bytes(48)
            + struct.pack("<2h", *b) + bytes.fromhex("b2" * 12) + bytes(48) + SENTINEL)


def mutate_descriptor(local, fault):
    data = bytearray(local)
    if fault == "alias":
        native = int.from_bytes(data[304:308], "little")
        native = (native & ~(1023 << 20)) | ((native & 1023) << 20)
        data[304:308] = native.to_bytes(4, "little")
    elif fault == "reserved":
        data[307] |= 0x40
    elif fault == "operation":
        data[244] = 0x84
    elif fault == "resource":
        data[242] = 0
    return bytes(data)


def audit(log, addresses, use_add, stall, seed_ids, fault, status):
    rows = []
    for line in log.splitlines():
        fields = line.split()
        if fields and fields[0] in ("A2", "F73"):
            rows.append((int(fields[1]), fields[2], fields[3:]))
    calls = [i for i, (_, kind, _) in enumerate(rows) if kind == "CALL"]
    assert len(calls) == len(seed_ids)
    cfg = [data for _, kind, data in rows[:calls[0]] if kind == "CONFIG_READBACK"]
    assert cfg == [["23"]]
    assert sum(kind == "BAD_ABI_REJECTED" for _, kind, _ in rows[:calls[0]]) == (fault == "BADCFG")

    results = []
    for j, seed_id in enumerate(seed_ids):
        records = defaultdict(list)
        for cycle, kind, data in rows[calls[j]:calls[j+1] if j+1 < len(calls) else len(rows)]:
            records[kind].append((cycle, data))

        def one(kind):
            assert len(records[kind]) == 1, (kind, records[kind])
            return records[kind][0]

        def nums(kind):
            return list(map(int, one(kind)[1]))

        def ordered(*kinds):
            cycles = [one(kind)[0] for kind in kinds]
            assert all(a < b for a, b in zip(cycles, cycles[1:])), (kinds, cycles)

        def held(kind, count):
            actual = records[kind + "_H"]
            assert len(actual) == count, (kind, count, actual)
            if count:
                handshake, fields = one(kind)
                assert all(c < handshake and data == fields for c, data in actual)

        job, epoch, task, token = nums("CALL")
        assert (job, epoch, task, token) == (7+j, 1, j+1, 2)
        reject = fault in RUNTIME_REJECT
        use_e = use_add and fault != "GFAULT" and not reject
        reads = 0 if reject else 32 if use_e else 16
        writes = 0 if status else 16
        assert nums("TERMINAL") == [job, 1, task, 2, status, reads, writes]
        assert nums("RESULT") == [job, 1, j+1, status, reads, writes]
        ordered("CALL", "TERMINAL", "RESULT", "READBACK")
        x, b = vectors(seed_id)
        g = tuple(silu_reference(v) for v in x)
        widened = [a + v for a, v in zip(g, b)]
        clipped = tuple(max(-32768, min(32767, v)) for v in widened)
        sat = use_e and not status and list(clipped) != widened
        assert nums("LC_SAT") == nums("MC_SAT") == [int(sat)]
        if not reject:
            assert nums("EXEC") == [job, 1, task, 0, 3, 3]
            assert nums("SERVICE") == [job, 1, task, 0, 3, status, reads, writes, int(sat)]
            assert one("GIN")[1] == [str(7 if fault == "GFAULT" else 0), f"{packed(x):08x}"]
            assert one("GOUT")[1][:2] == [str(int(fault == "GFAULT")), "0"]
            if fault != "GFAULT":
                assert int(one("GOUT")[1][2], 16) == packed(g)
            assert [int(v[0]) for _, v in records["READ"]] == list(addresses[:2] if use_e else addresses[:1])
            seed = seed_words(seed_id)
            assert [int(v[0], 16) for _, v in records["READ_RSP"]] == [
                int.from_bytes(seed[i:i+16], "little") for i in ([0, 64] if use_e else [0])]
            assert records["READ"][0][0] < records["READ_RSP"][0][0] < one("GIN")[0]
            ordered("CALL", "EXEC", "GIN", "GOUT", "SERVICE", "TERMINAL")
            held("GIN", stall * 2)
            held("GOUT", stall * 3)
            if use_e:
                assert one("EIN")[1] == [str(14 if fault == "EFAULT" else 0),
                                         f"{packed(g):032x}", f"{packed(b):032x}"]
                assert one("EOUT")[1] == [str(int(fault == "EFAULT")), str(int(sat)),
                                          f"{(0 if status else packed(clipped)):032x}"]
                assert one("GOUT")[0] < records["READ"][1][0] < records["READ_RSP"][1][0] < one("EIN")[0]
                ordered("GOUT", "EIN", "EOUT", "SERVICE")
                held("EIN", stall * 2)
                held("EOUT", stall * 3)
            else:
                assert not any(records[k] for k in ("EIN", "EOUT", "EIN_H", "EOUT_H"))
        else:
            assert not any(records[k] for k in ("EXEC", "READ", "READ_RSP", "GIN", "GOUT", "EIN", "EOUT", "SERVICE"))
        if status:
            assert not any(records[k] for k in ("WRITE", "WRITE_H", "ACK", "ACK_H"))
            expected = int.from_bytes(SENTINEL, "little")
        else:
            expected = packed(clipped if use_add else g)
            assert one("WRITE")[1] == [str(addresses[2]), f"{expected:032x}"]
            assert one("ACK")[1] == [f"{expected:032x}"]
            ordered("EOUT" if use_add else "GOUT", "WRITE", "ACK", "SERVICE")
            held("WRITE", stall * 4)
            held("ACK", stall * 5)
            assert [v[0] for _, v in records["RETIRE"]] == ["41", "44", "4f"]
        assert one("READBACK")[1] == [str(job), str(addresses[2]), f"{expected:032x}"]
        results.append(dict(job=job, task=task, status=status, actual_reads=reads, actual_writes=writes,
                            saturated=sat, result=f"{expected:032x}",
                            cycles={k.lower(): one(k)[0] for k in ("CALL", "GIN", "GOUT", "EIN", "EOUT", "WRITE",
                                   "ACK", "SERVICE", "TERMINAL", "RESULT", "READBACK") if records[k]},
                            held_cycles={k.lower(): len(records[k + "_H"]) for k in (
                                "GIN", "GOUT", "EIN", "EOUT", "WRITE", "ACK")}))
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verilator", default="verilator")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    validate_sources()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    g_dir = PROJECT / "rtl/block_v2"
    sources = [p for p in SOURCES if p.name not in ("block_v2_m.sv", "lc_m_dot_store_adapter.sv", "block_feed_loader.sv")]
    sources += [HERE / "tb_f_local.sv", HERE / "lc_f_store_adapter.sv",
                g_dir / "block_v2_g.sv", g_dir / "block_v2_e.sv"]
    exe = out / "obj_dir/sim"
    cmd = [args.verilator, "--binary", "--timing", "--timescale", "1ns/1ps",
           "--top-module", "tb_p_compute", "-I" + str(CTRL), "-I" + str(g_dir), "-DTB_F_COMPUTE",
           "--Mdir", exe.parent, "-j", env.get("SLURM_CPUS_PER_TASK", "4"), "-o", exe.name, *sources]
    compile_log = out / "compile.log"
    common.run(cmd, out, env, compile_log)
    results = []
    for name, use_add, addresses, stall, seed_ids, fault in SCENARIOS:
        case = out / name
        case.mkdir()
        a, b, dst = addresses
        mother, local = images(a, b, dst, use_add)
        validate_pair(mother, local)
        if fault in RUNTIME_REJECT:
            local = mutate_descriptor(local, fault)
            try:
                validate_pair(mother, local)
            except ValueError:
                pass
            else:
                raise AssertionError("host admitted injected descriptor")
        for stem, data in (("mother", mother), ("local", local),
                           ("seed", b"".join(seed_words(i) for i in seed_ids))):
            (case / (stem + ".bin")).write_bytes(data)
            mem(case / (stem + ".mem"), data)
        status = 5 if fault in RUNTIME_REJECT else 9 if fault in NATIVE_ERROR else 0
        launch = [exe, f"+MOTHER={case / 'mother.mem'}", f"+LOCAL={case / 'local.mem'}",
                  f"+MWORDS={len(mother)//16}", f"+LWORDS={len(local)//16}", f"+SEED={case / 'seed.mem'}",
                  f"+A={a}", f"+B={b}", f"+DST={dst}", f"+STALL={stall}",
                  f"+RUNS={len(seed_ids)}", f"+EXPECT={status}"]
        if use_add:
            launch.append("+FADD")
        if fault in NATIVE_ERROR or fault == "BADCFG":
            launch.append("+" + fault)
        log = common.run(launch, out, env, case / "run.log")
        assert f"PASS A2 jobs={len(seed_ids)} status={status}" in log
        jobs = audit(log, addresses, use_add, stall, seed_ids, fault, status)
        results.append(dict(case=name, use_add=use_add, expected_status=status, jobs=jobs,
                            command=list(map(str, launch)),
                            sha256={p.name: common.sha(p.read_bytes()) for p in sorted(case.iterdir())}))
        print(name, "PASS", flush=True)
    report = dict(schema="control-f-g-e-store/0.1", abi=ABI, topology=TOPOLOGY, cases=results,
                  actual_rtl=["mc_min_controller", "lc_min_controller", "block_local_s_macro", "block_v2_g", "block_v2_e"],
                  compile_command=list(map(str, cmd)), compile_log_sha256=common.sha(compile_log.read_bytes()),
                  python=sys.version, verilator=common.run([args.verilator, "--version"], out, env).strip(),
                  scope="one F trial, fixed wired native services; no cross-block or physical sign-off")
    (out / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("PASS F73", len(results), "RTL scenarios", flush=True)


if __name__ == "__main__":
    main()
