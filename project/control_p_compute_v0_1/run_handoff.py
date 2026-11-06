"""Run native P or F output through the two-local RAW16 test route."""

import argparse
from collections import defaultdict
import json
import os
from pathlib import Path
import struct
import sys

from run_a2 import (CTRL, HERE, PROJECT, SILU_ABI, SILU_OP, SOURCES, assemble,
                    common, mem, rne, seed_job, silu_reference)
from image import parse_image


R4 = PROJECT / "control_r4_v0_1"
sys.path.insert(0, str(R4))
import stored_ack_check

TOPOLOGY = 0x1764A303
RAW_ABI = 0x00010001
F_ABI = 0x00017903
F_TOPOLOGY = 0x1764F303
F_HERE = PROJECT / "control_f_compute_v0_1"


def images(fault, f_store=False):
    topology = F_TOPOLOGY if f_store else TOPOLOGY
    abi = F_ABI if f_store else SILU_ABI
    resource, mask, block_type = (3, 0x2c, 3) if f_store else (0, 0x29, 0)
    operation = 0x0083 if f_store else SILU_OP
    source_id = 17961 if f_store else 17910
    bundles = json.loads((PROJECT / "control_image_v0_1/bundles.json").read_bytes())["bundles"]
    packed = next(bundle["images_hex"] for bundle in bundles if bundle["manifest"]["bundle"] == "receiver_first_16B")
    mother, old_source, sink = (
        parse_image(bytes.fromhex(packed[key]), role)
        for key, role in (("mother", "mother"), ("local0", "local"), ("local1", "local"))
    )
    source_program = [
        dict(op="L_OPEN", a=0), dict(op="L_EXEC", a=resource, b=3, c=0), dict(op="L_WAIT", x=8),
        dict(op="L_TX", b=0, c=0), dict(op="L_WAIT", x=1), dict(op="L_DROP", a=0), dict(op="L_END"),
    ]
    if fault == "premature_tx":
        del source_program[1:3]
    source_record = old_source["records"]
    source_task = dict(source_record["task"][0], block_type=block_type, input_object_mask=0,
                       required_resources=mask, program_image_id=source_id,
                       topology_id=topology, native_abi_id=abi)
    source_object = dict(source_record["object"][0], base_bytes=16 * (13 if fault == "wrong_destination" else 12),
                         native_abi_id=abi)
    execution = dict(resource=resource, service=0, native_op=operation, native_abi_id=abi,
                     native0=4 | (8 << 10) | (12 << 20))
    sink_record = sink["records"]
    return {
        "mother": assemble("mother", mother["program"], {"event_binding": mother["records"]["event_binding"]},
                           source_id-1, 0, abi, topology),
        "local0": assemble("local", source_program,
                           dict(task=[source_task], object=[source_object], execution=[execution],
                                transfer=[source_record["transfer"][1]]),
                           source_id, mask, abi, topology),
        "local1": assemble("local", sink["program"],
                           dict(task=[dict(sink_record["task"][0], program_image_id=source_id+1, topology_id=topology)],
                                object=[dict(sink_record["object"][0], base_bytes=256)],
                                transfer=sink_record["transfer"]),
                           source_id+1, 0x20, RAW_ABI, topology),
    }


def expected_word(seed):
    a = struct.unpack("8b", seed[:8])
    columns = struct.unpack("16b", seed[64:80])
    dot = [sum(x * y for x, y in zip(a, columns[start:start+8])) for start in (0, 8)]
    quantized = [max(-32768, min(32767, rne(value, 2))) for value in dot]
    activated = [silu_reference(value) for value in quantized]
    return int.from_bytes(struct.pack("<hh", *activated), "little")


def f_expected_word(seed):
    x = struct.unpack("<2h", seed[:4])
    addend = struct.unpack("<2h", seed[64:68])
    values = [silu_reference(v)+a for v, a in zip(x, addend)]
    clipped = [max(-32768, min(32767, v)) for v in values]
    return int.from_bytes(struct.pack("<2h", *clipped), "little"), int(values != clipped)


def audit(log, seeds, fault, ack_rejects, f_store=False):
    source = "F73" if f_store else "A2"
    local_reads = 32 if f_store else 128
    events = defaultdict(list)
    for line in log.splitlines():
        parts = line.split()
        if parts and parts[0] in (source, "CHAIN", "N"):
            events[parts[0], parts[2]].append((int(parts[1]), parts[3:]))
    guard = stored_ack_check.check(log)
    assert guard["rejected"] == ack_rejects
    calls = events["CHAIN", "CALL"]
    ready = [(c, f) for c, f in events["CHAIN", "EVENT"] if f[:2] == ["1", "0"]]
    assert len(calls) == 2 * len(seeds) and len(ready) == len(seeds)
    for i, ((rx_cycle, rx), (tx_cycle, tx)) in enumerate(zip(calls[::2], calls[1::2])):
        assert rx == ["1", str(7+i), "1", str(i+1)] and tx == ["0", str(7+i), "1", str(i+1)]
        assert rx_cycle < ready[i][0] < tx_cycle and int(ready[i][1][2]) == 7+i
    stores = [(c, f) for c, f in events["N", "STORE"] if f[0] == "1"]
    writebacks = events[source, "ACK"]
    source_reads = events["CHAIN", "SOURCE_READ"]
    issues = events["CHAIN", "TX_ISSUE"]
    drops = events["CHAIN", "DROP"]
    results = events["CHAIN", "RESULT"]
    readbacks = events["CHAIN", "DEST_READ"]
    if fault in ("wrong_destination", "premature_tx", "g_fault", "e_fault"):
        assert not any((stores, writebacks, source_reads, issues, drops, results, readbacks, guard["receipts"]))
        status = {"wrong_destination": 5, "premature_tx": 7, "g_fault": 9, "e_fault": 9}[fault]
        assert any(f == ["0", "3", "7", str(status)] for _, f in events["CHAIN", "EVENT"])
        native_error = fault in ("g_fault", "e_fault")
        assert len(events[source, "EXEC"]) == int(native_error)
        assert len(events[source, "GOUT"]) == int(native_error)
        if f_store and native_error:
            response = events[source, "GOUT" if fault == "g_fault" else "EOUT"]
            assert len(response) == 1 and response[0][1][0] == "1"
            assert not events[source, "WRITE"]
        return dict(expected_source_error=status, destination_writes=0, ack_guard=guard)

    completed = 0 if fault == "lost_ack" else len(seeds)
    txs = events["N", "TX"]
    assert len(stores) == len(writebacks) == len(source_reads) == len(issues) == len(txs) == len(seeds)
    assert len(drops) == len(results) == len(readbacks) == len(guard["receipts"]) == completed
    records = []
    for i, seed in enumerate(seeds):
        expected, saturation = f_expected_word(seed) if f_store else (expected_word(seed), None)
        write, src, dest, issue, tx = (rows[i] for rows in (writebacks, source_reads, stores, issues, txs))
        computed = events[source, "EOUT" if f_store else "GOUT"][i]
        compute = events[source, "SERVICE" if f_store else "RETURN"][i]
        assert int(computed[1][0]) == 0 and int(computed[1][2], 16) == expected
        assert [int(x, 16) for x in (write[1][0], src[1][1], dest[1][-1])] == [expected] * 3
        assert src[1][0] == "12" and issue[1] == [str(7+i), "1", str(i+1), "1"]
        fields = [str(7+i), "1", str(i+1), "0", "3", "0", str(local_reads), "16"]
        if f_store:
            fields.append(str(saturation))
            g = events[source, "GOUT"][i]
            x = struct.unpack("<2h", seed[:4])
            g_word = int.from_bytes(struct.pack("<2h", *(silu_reference(v) for v in x)), "little")
            assert int(g[1][0]) == 0 and int(g[1][2], 16) == g_word and g[0] < computed[0]
        assert compute[1] == fields
        assert calls[2*i+1][0] < computed[0] < write[0] < compute[0] < issue[0] < src[0] < tx[0] < dest[0]
        row = dict(job=7+i, word=f"{expected:032x}", ready=ready[i][0], p0_write_ack=write[0],
                   compute_return=compute[0], tx=tx[0], p1_write_ack=dest[0])
        if completed:
            release = guard["receipts"][i]
            assert dest[0] == release["commit"] < release["accepted"] < release["released"]
            assert release["released"] < drops[i][0] < results[i][0] < readbacks[i][0]
            assert results[i][1] == [str(7+i), "0", str(local_reads+16), "32"]
            assert readbacks[i][1][0] == str(7+i) and int(readbacks[i][1][1], 16) == expected
            row.update(ack_release=release["released"], drop=drops[i][0], result=results[i][0])
        else:
            assert guard["pending"]["commit"] == dest[0] and guard["pending"]["accepted"] is None
        records.append(row)
    return dict(jobs=records, destination_writes=len(stores), completed=completed, ack_guard=guard)


def audit_recovery(log, seeds):
    guard = stored_ack_check.check(log)
    assert guard["rejected"] == 1 and guard["pending"] is None
    abandoned, = guard["abandoned"]
    assert abandoned["commit"] is not None and abandoned["accepted"] is None
    assert len(guard["receipts"]) == 2
    assert (abandoned["identity"] >> 208) & 0xffffffff == 1
    assert all((row["identity"] >> 208) & 0xffffffff == 2 for row in guard["receipts"])
    events = defaultdict(list)
    for line in log.splitlines():
        f = line.split()
        if len(f) >= 3 and f[0] in ("REC", "CHAIN", "N", "ACKG"):
            events[f[0], f[2]].append((int(f[1]), f[3:]))
    isolated, = events["REC", "ISOLATED"]
    assert isolated[1] == ["1"] and abandoned["commit"] < isolated[0]
    certs = events["REC", "RESET_CERT"]
    assert [row[1][0] for row in certs] == ["1", "2"] and isolated[0] < certs[1][0]
    reload2 = [(c, fields) for c, fields in events["REC", "RELOAD"] if fields[1] == "2"]
    assert {f[0] for _, f in reload2} == {"0", "1", "2"} and len(reload2) == 3
    calls = events["CHAIN", "CALL"]
    assert [f[:3] for _, f in calls] == [
        [str(block), str(job), str(1 if job == 7 else 2)]
        for job in (7, 8, 9) for block in (1, 0)
    ]
    assert max(c for c, _ in reload2) < calls[2][0]
    assert any(int(f[0], 16) == abandoned["identity"] and c > calls[2][0]
               for c, f in events["ACKG", "WIRE"])
    results = events["CHAIN", "RESULT"]
    readbacks = events["CHAIN", "DEST_READ"]
    assert [f for _, f in results] == [["8", "0", "48", "32"], ["9", "0", "48", "32"]]
    assert [int(f[0]) for _, f in readbacks] == [7, 8, 9]
    assert [int(f[1], 16) for _, f in readbacks] == [f_expected_word(seed)[0] for seed in seeds]
    drops = events["CHAIN", "DROP"]
    assert len(drops) == 2 and all(
        ack["released"] < drop[0] < result[0]
        for ack, drop, result in zip(guard["receipts"], drops, results)
    )
    assert certs[1][0] < readbacks[0][0] < calls[2][0]
    return dict(completed=2, old_payload_retained=True, reloaded=reload2,
                readback=readbacks, result=results, isolated_cycle=isolated[0], ack_guard=guard)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verilator", required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--f-store", action="store_true", help="Use the native G/E F producer")
    parser.add_argument("--f-recovery", action="store_true", help="Verify cohort recovery after missing F ACK")
    args = parser.parse_args()
    if args.f_recovery:
        args.f_store = True
    if args.f_store:
        sys.path.insert(0, str(F_HERE))
        from f_images import validate_sources
        from run_f import seed_words
        validate_sources()
    else:
        seed_words = seed_job
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    sources = SOURCES + [CTRL / "tb_control_network.sv", R4 / "tb_real_local.sv",
                         R4 / "lc_raw16_s_adapter.sv", R4 / "p_stored_ack_guard.sv",
                         PROJECT / "rtl/block_v2/block_v2_g.sv"]
    if args.f_store:
        sources += [F_HERE / "tb_f_local.sv", F_HERE / "lc_f_store_adapter.sv",
                    PROJECT / "rtl/block_v2/block_v2_e.sv"]
    defines = ["-DTB_F_COMPUTE", "-DTB_F_HANDOFF"] if args.f_store else ["-DTB_P_SILU"]
    if args.f_recovery:
        sources += [R4 / "cohort_reset_controller.sv"]
        defines += ["-DTB_F_RECOVERY"]
    obj = out / "obj_dir"
    command = [args.verilator, "--binary", "--timing", "--top-module", "tb_control_network",
               "-DTB_COMPUTE_HANDOFF", "-DTB_STORED_ACK_GUARD", *defines,
               "-I"+str(CTRL), "-I"+str(HERE), "-I"+str(R4), "-I"+str(PROJECT/"rtl/block_v2"),
               "--Mdir", obj, "-j", "4", "-o", "sim", *sources]
    build = common.run(command, out, env, out / "compile.log")
    cases = (
        ("single", (0,), 0, 0, 0),
        ("two_jobs_stalled", (0, 2), 2, 0, 0),
        ("wrong_ack_epoch", (0,), 2, 5, 1),
        ("duplicate_ack", (2,), 2, 6, 1),
        ("previous_job_ack", (0, 2), 2, 7, 1),
        ("early_ack", (0,), 2, 8, 1),
        ("lost_ack", (0,), 2, 2, 0),
        ("wrong_destination", (0,), 2, 0, 0),
        ("premature_tx", (0,), 2, 0, 0),
        ("g_fault", (0,), 2, 0, 0),
    )
    if args.f_store:
        cases += (("e_fault", (0,), 2, 0, 0), ("saturation", (1,), 2, 0, 0))
    if args.f_recovery:
        cases = (("f_recovery", (0, 1, 2), 2, 2, 1),)
    results = []
    for fault, seed_ids, stall, mode, rejected in cases:
        case = out / fault
        case.mkdir()
        bundle = images(fault, args.f_store)
        argv = [obj / "sim", f"+STALL={stall}", f"+RUNS={len(seed_ids)}",
                f"+CALLS={len(seed_ids)*2}", f"+MODE={mode}"]
        for key, file_arg, word_arg in (("mother", "IMAGE", "WORDS"), ("local0", "LOCAL0", "WORDS0"),
                                       ("local1", "LOCAL1", "WORDS1")):
            file = case / (key + ".mem")
            mem(file, bundle[key])
            argv.extend([f"+{file_arg}={file}", f"+{word_arg}={len(bundle[key])//16}"])
        if args.f_store:
            argv.extend([f"+LOCAL={case/'local0.mem'}", f"+LWORDS={len(bundle['local0'])//16}"])
        seeds = [seed_words(i) for i in seed_ids]
        mem(case / "seed.mem", b"".join(seeds))
        argv.append(f"+SEED={case/'seed.mem'}")
        if fault in ("wrong_destination", "premature_tx", "g_fault", "e_fault"):
            argv.extend(["+POISON=1", "+CANCELS=1"])
        if fault == "g_fault":
            argv.append("+GFAULT")
        if fault == "e_fault":
            argv.append("+EFAULT")
        if fault in ("lost_ack", "f_recovery"):
            argv.append("+POISON=1")
        log = common.run(argv, out, env, case / "trace.log")
        assert "PASS network" in log
        checked = audit_recovery(log, seeds) if args.f_recovery else audit(log, seeds, fault, rejected, args.f_store)
        results.append(dict(case=fault, check=checked, command=[str(x) for x in argv],
                            artifacts_sha256={p.name: common.sha(p.read_bytes()) for p in case.iterdir()}))
        print(f"{fault} PASS", flush=True)
    (out / "report.json").write_text(json.dumps(dict(
        schema="f-recovery/0.1" if args.f_recovery else "f-compute-handoff/0.1" if args.f_store else "p-compute-handoff/0.1",
        topology=hex(F_TOPOLOGY if args.f_store else TOPOLOGY), results=results,
        tools=dict(verilator=common.run([args.verilator, "--version"], out, env).strip(), python=sys.version),
        compile_command=[str(x) for x in command], compile_log_sha256=common.sha(build.encode()),
        actual_mother=1, actual_locals=2, actual_private_s=2, actual_m=int(not args.f_store), actual_g=1,
        **({"actual_e": 1} if args.f_store else {}),
        route="bounded logical test route; production endpoint binding required",
    ), indent=2) + "\n", encoding="utf-8")
    print(f"PASS {'F handoff' if args.f_store else 'A2/A3'} {len(results)} real compute/handoff cases", flush=True)


if __name__ == "__main__":
    main()
