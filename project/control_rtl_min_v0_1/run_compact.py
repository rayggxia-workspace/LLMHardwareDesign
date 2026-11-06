"""Exercise compact fetch, branch and image admission in the real MC and two LCs."""
import argparse
import json
import os
from pathlib import Path

import run as common
import network_check
from image import compact, pack_image, parse_image

HERE = Path(__file__).resolve().parent
BUNDLES = HERE.parent / "control_image_v0_1/bundles.json"
SOURCES = ("mc_min_controller.sv", "lc_min_controller.sv", "tb_network_pm.sv",
           "tb_network_local.sv", "tb_control_network.sv")


def receiver_bundle():
    bundles = json.loads(BUNDLES.read_bytes())["bundles"]
    found = next(b for b in bundles if b["manifest"]["bundle"] == "receiver_first_16B")
    return {key: parse_image(bytes.fromhex(value)) for key, value in found["images_hex"].items()}


def rebuild(original, program=None, *, version=2):
    role, header = original["role"], dict(original["header"])
    del header["version"]
    program = original["program"] if program is None else program
    records = {key: value for key, value in original["records"].items() if key != "instruction"}
    header.update(max_steps=len(program))
    if records["task"]:
        records["task"] = [dict(records["task"][0], max_steps=len(program))]
    return pack_image(role, program, records, header, instruction_version=version)


def with_branch(original, value):
    prefix = "G" if original["role"] == "mother" else "L"
    program = [dict(op=prefix+"_MOVI", a=7, x=value),
               dict(op=prefix+"_BRANCH", a=7, x=3, y=2),
               dict(op=prefix+"_MOVI", a=6, x=0xdeadbeef)]
    return rebuild(original, program + original["program"])


def change_word(data, pc, operation):
    offset = 128 + pc * 8
    old = int.from_bytes(data[offset:offset+8], "little")
    return data[:offset] + operation(old).to_bytes(8, "little") + data[offset+8:]


def retired(rows):
    return [int(str(r["signals"].get("trace_pc_o", 0)), 0) for r in rows
            if int(str(r["signals"].get("trace_retire_o", 0)), 0)]


def effects(trace):
    return [{k: v for k, v in event.items() if k != "cycle"} for event in trace["route"]]


def audit_fetch(rows, size):
    """Check the SRAM read address for each decoded instruction, including jump targets."""
    observed = []
    for row in rows:
        r = {k: int(str(v), 0) for k, v in row["signals"].items()}
        if r.get("pm_req_valid_o") and r.get("pm_req_ready_i") and r.get("trace_pm_owner_o") == 1:
            observed.append((r.get("trace_pc_o", 0), r["pm_req_address_o"]))
    assert observed
    assert all(address == 128 + 16*(pc//(16//size)) for pc, address in observed), observed
    return observed


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--verilator", required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True)
    obj = out/"obj_dir"
    env = dict(os.environ)
    compile_args = [args.verilator, "--binary", "--timing", "--top-module", "tb_control_network",
                    "-I"+str(HERE), "--Mdir", obj, "-j", env.get("SLURM_CPUS_PER_TASK", "4"),
                    "-o", "sim", *[HERE/s for s in SOURCES]]
    common.run(compile_args, out, env, out/"compile.log")
    source = receiver_bundle()
    old = {k: rebuild(v, version=1) for k, v in source.items()}
    new = {k: rebuild(v) for k, v in source.items()}
    roles = ("mother", "local0", "local1")
    results = {}

    def simulate(name, images, *, calls=2, status=0, extra=()):
        case = out/name
        case.mkdir()
        argv = [obj/"sim", f"+CALLS={calls}", "+STALL=3", f"+EXPECTED={status}", *extra]
        for role, image_arg, word_arg in zip(roles, ("IMAGE","LOCAL0","LOCAL1"), ("WORDS","WORDS0","WORDS1")):
            data = images[role]
            image_path = case/(role+".mem")
            image_path.write_text("".join(f"{int.from_bytes(data[i:i+16], 'little'):032x}\n"
                                          for i in range(0, len(data), 16)), encoding="ascii")
            argv.extend((f"+{image_arg}={image_path}", f"+{word_arg}={len(data)//16}"))
        log = common.run(argv, out, env, case/"trace.log")
        results[name] = dict(bytes={k:len(images[k]) for k in roles}, expected_status=status,
                             sha256={f.name:common.sha(f.read_bytes()) for f in case.iterdir()})
        print(name, "PASS", flush=True)
        return log

    def records(log):
        assert "PASS network actualMother=1 actualLC=2" in log
        trace = network_check.decode(log)
        return trace, [trace["mother"], *(part["cycles"] for part in trace["locals"])]

    original, old_rows = records(simulate("legacy", old))
    packed, new_rows = records(simulate("compact", new))
    assert effects(packed) == effects(original) and len(effects(packed)) > 0
    assert [retired(rows) for rows in old_rows] == [retired(rows) for rows in new_rows]
    for rows in old_rows:
        audit_fetch(rows, 16)
    for rows in new_rows:
        audit_fetch(rows, 8)
    for name, value, prefix in (("branch_true", 0x80000000, [0,1,3]), ("branch_false", 0, [0,1,2,3])):
        branch = {k: with_branch(v, value) for k, v in source.items()}
        trace, all_rows = records(simulate(name, branch))
        assert effects(trace) == effects(original)
        for rows in all_rows:
            pc_path = retired(rows)
            assert pc_path[:len(prefix)] == prefix, pc_path
            audit_fetch(rows, 8)
        results[name]["retired_pcs"] = [retired(rows) for rows in all_rows]

    branch = dict(new, mother=with_branch(source["mother"], 0x80000000))
    for name, mutate, status in (
        ("backward_false_target", lambda word: word & ~(0xffff << 16), 6),
        ("target_outside_image", lambda word: (word & ~(0xffff << 32)) | 0xffff << 32, 6),
        ("reserved_branch_bit", lambda word: word | 1, 2),
    ):
        bad = dict(branch, mother=change_word(branch["mother"], 1, mutate))
        _, all_rows = records(simulate(name, bad, calls=0, status=status))
        assert retired(all_rows[0]) == [0], retired(all_rows[0])

    odd = new["mother"]
    assert compact.unpack_header(odd[:128])["instruction_count"] % 2 == 1
    rejected = (
        ("odd_padding", odd[:168]+b"\x01"+odd[169:], 2, 5, 160),
        ("unknown_version", odd[:8]+b"\x03\0"+odd[10:], 3, 3, 0),
    )
    for name, mutated, op, status, address in rejected:
        log = simulate(name, dict(new, mother=mutated), calls=0, status=status,
                       extra=(f"+REJECT_CFG_OP={op}", f"+REJECT_CFG_STATUS={status}"))
        assert f"PASS config rejected op={op} status={status} address={address}" in log
    report = dict(cases=results, compiler=[str(a) for a in compile_args],
                  verilator=common.run([args.verilator, "--version"], out, env).strip(),
                  compile_sha256=common.sha((out/"compile.log").read_bytes()))
    (out/"report.json").write_text(json.dumps(report, indent=2)+"\n", encoding="utf-8")
    print(f"PASS {len(results)} compact fetch and branch RTL cases", flush=True)


if __name__ == "__main__":
    main()
