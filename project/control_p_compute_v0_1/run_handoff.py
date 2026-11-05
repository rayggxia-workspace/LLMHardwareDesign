"""Run the real single-P SiLU output through the two-local RAW16 test route."""

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


def images(fault):
    bundles = json.loads((PROJECT / "control_image_v0_1/bundles.json").read_bytes())["bundles"]
    packed = next(bundle["images_hex"] for bundle in bundles if bundle["manifest"]["bundle"] == "receiver_first_16B")
    mother, old_source, sink = (
        parse_image(bytes.fromhex(packed[key]), role)
        for key, role in (("mother", "mother"), ("local0", "local"), ("local1", "local"))
    )
    source_program = [
        dict(op="L_OPEN", a=0), dict(op="L_EXEC", b=3, c=0), dict(op="L_WAIT", x=8),
        dict(op="L_TX", b=0, c=0), dict(op="L_WAIT", x=1), dict(op="L_DROP", a=0), dict(op="L_END"),
    ]
    if fault == "premature_tx":
        del source_program[1:3]
    source_record = old_source["records"]
    source_task = dict(source_record["task"][0], input_object_mask=0, required_resources=0x29,
                       program_image_id=17910, topology_id=TOPOLOGY, native_abi_id=SILU_ABI)
    source_object = dict(source_record["object"][0], base_bytes=16 * (13 if fault == "wrong_destination" else 12),
                         native_abi_id=SILU_ABI)
    execution = dict(resource=0, service=0, native_op=SILU_OP, native_abi_id=SILU_ABI,
                     native0=4 | (8 << 10) | (12 << 20))
    sink_record = sink["records"]
    return {
        "mother": assemble("mother", mother["program"], {"event_binding": mother["records"]["event_binding"]},
                           17909, 0, SILU_ABI, TOPOLOGY),
        "local0": assemble("local", source_program,
                           dict(task=[source_task], object=[source_object], execution=[execution],
                                transfer=[source_record["transfer"][1]]),
                           17910, 0x29, SILU_ABI, TOPOLOGY),
        "local1": assemble("local", sink["program"],
                           dict(task=[dict(sink_record["task"][0], program_image_id=17911, topology_id=TOPOLOGY)],
                                object=[dict(sink_record["object"][0], base_bytes=256)],
                                transfer=sink_record["transfer"]),
                           17911, 0x20, RAW_ABI, TOPOLOGY),
    }


def expected_word(seed):
    a = struct.unpack("8b", seed[:8])
    columns = struct.unpack("16b", seed[64:80])
    dot = [sum(x * y for x, y in zip(a, columns[start:start+8])) for start in (0, 8)]
    quantized = [max(-32768, min(32767, rne(value, 2))) for value in dot]
    activated = [silu_reference(value) for value in quantized]
    return int.from_bytes(struct.pack("<hh", *activated), "little")


def audit(log, seeds, fault, ack_rejects):
    events = defaultdict(list)
    for line in log.splitlines():
        parts = line.split()
        if parts and parts[0] in ("A2", "CHAIN", "N"):
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
    writebacks = events["A2", "ACK"]
    source_reads = events["CHAIN", "SOURCE_READ"]
    issues = events["CHAIN", "TX_ISSUE"]
    drops = events["CHAIN", "DROP"]
    results = events["CHAIN", "RESULT"]
    readbacks = events["CHAIN", "DEST_READ"]
    if fault in ("wrong_destination", "premature_tx", "g_fault"):
        assert not any((stores, writebacks, source_reads, issues, drops, results, readbacks, guard["receipts"]))
        status = {"wrong_destination": 5, "premature_tx": 7, "g_fault": 9}[fault]
        assert any(f == ["0", "3", "7", str(status)] for _, f in events["CHAIN", "EVENT"])
        assert len(events["A2", "EXEC"]) == int(fault == "g_fault")
        assert len(events["A2", "GOUT"]) == int(fault == "g_fault")
        return dict(expected_source_error=status, destination_writes=0, ack_guard=guard)

    completed = 0 if fault == "lost_ack" else len(seeds)
    txs = events["N", "TX"]
    assert len(stores) == len(writebacks) == len(source_reads) == len(issues) == len(txs) == len(seeds)
    assert len(drops) == len(results) == len(readbacks) == len(guard["receipts"]) == completed
    records = []
    for i, seed in enumerate(seeds):
        expected = expected_word(seed)
        write, src, dest, issue, tx = (rows[i] for rows in (writebacks, source_reads, stores, issues, txs))
        g = events["A2", "GOUT"][i]
        compute = events["A2", "RETURN"][i]
        assert int(g[1][0]) == 0 and int(g[1][2], 16) == expected
        assert [int(x, 16) for x in (write[1][0], src[1][1], dest[1][-1])] == [expected] * 3
        assert src[1][0] == "12" and issue[1] == [str(7+i), "1", str(i+1), "1"]
        assert compute[1] == [str(7+i), "1", str(i+1), "0", "3", "0", "128", "16"]
        assert calls[2*i+1][0] < g[0] < write[0] < compute[0] < issue[0] < src[0] < tx[0] < dest[0]
        row = dict(job=7+i, word=f"{expected:032x}", ready=ready[i][0], p0_write_ack=write[0],
                   compute_return=compute[0], tx=tx[0], p1_write_ack=dest[0])
        if completed:
            release = guard["receipts"][i]
            assert dest[0] == release["commit"] < release["accepted"] < release["released"]
            assert release["released"] < drops[i][0] < results[i][0] < readbacks[i][0]
            assert results[i][1] == [str(7+i), "0", "144", "32"]
            assert readbacks[i][1][0] == str(7+i) and int(readbacks[i][1][1], 16) == expected
            row.update(ack_release=release["released"], drop=drops[i][0], result=results[i][0])
        else:
            assert guard["pending"]["commit"] == dest[0] and guard["pending"]["accepted"] is None
        records.append(row)
    return dict(jobs=records, destination_writes=len(stores), completed=completed, ack_guard=guard)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verilator", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    sources = SOURCES + [CTRL / "tb_control_network.sv", R4 / "tb_real_local.sv",
                         R4 / "lc_raw16_s_adapter.sv", R4 / "p_stored_ack_guard.sv",
                         PROJECT / "rtl/block_v2/block_v2_g.sv"]
    obj = out / "obj_dir"
    command = [args.verilator, "--binary", "--timing", "--top-module", "tb_control_network",
               "-DTB_COMPUTE_HANDOFF", "-DTB_P_SILU", "-DTB_STORED_ACK_GUARD",
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
    results = []
    for fault, seed_ids, stall, mode, rejected in cases:
        case = out / fault
        case.mkdir()
        bundle = images(fault)
        argv = [obj / "sim", f"+STALL={stall}", f"+RUNS={len(seed_ids)}",
                f"+CALLS={len(seed_ids)*2}", f"+MODE={mode}"]
        for key, file_arg, word_arg in (("mother", "IMAGE", "WORDS"), ("local0", "LOCAL0", "WORDS0"),
                                       ("local1", "LOCAL1", "WORDS1")):
            file = case / (key + ".mem")
            mem(file, bundle[key])
            argv.extend([f"+{file_arg}={file}", f"+{word_arg}={len(bundle[key])//16}"])
        seeds = [seed_job(i) for i in seed_ids]
        mem(case / "seed.mem", b"".join(seeds))
        argv.append(f"+SEED={case/'seed.mem'}")
        if fault in ("wrong_destination", "premature_tx", "g_fault"):
            argv.extend(["+POISON=1", "+CANCELS=1"])
        if fault == "g_fault":
            argv.append("+GFAULT")
        if fault == "lost_ack":
            argv.append("+POISON=1")
        log = common.run(argv, out, env, case / "trace.log")
        assert "PASS network" in log
        checked = audit(log, seeds, fault, rejected)
        results.append(dict(case=fault, check=checked, command=[str(x) for x in argv],
                            artifacts_sha256={p.name: common.sha(p.read_bytes()) for p in case.iterdir()}))
        print(f"{fault} PASS", flush=True)
    (out / "report.json").write_text(json.dumps(dict(
        schema="p-compute-handoff/0.1", topology=hex(TOPOLOGY), results=results,
        tools=dict(verilator=common.run([args.verilator, "--version"], out, env).strip(), python=sys.version),
        compile_command=[str(x) for x in command], compile_log_sha256=common.sha(build.encode()),
        actual_mother=1, actual_locals=2, actual_private_s=2, actual_m=1, actual_g=1,
        route="bounded logical test route; production endpoint binding required",
    ), indent=2) + "\n", encoding="utf-8")
    print(f"PASS A2/A3 {len(results)} real compute/handoff cases", flush=True)


if __name__ == "__main__":
    main()
