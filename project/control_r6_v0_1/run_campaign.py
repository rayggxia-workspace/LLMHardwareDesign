"""Run generated R6 images on the existing R4 two-controller DMA fixture."""
import argparse
import json
import os
import pathlib
import sys

from check_bundle import check as bundle_negative_checks
from check_ir import check as ir_checks
from compile_ir import compile_ir
from task_ir import HERE
from verify_bundle import verify

OLD = HERE.parent / "control_rtl_min_v0_1"
R4 = HERE.parent / "control_r4_v0_1"
RTL = HERE.parent / "rtl"
sys.path.insert(0, str(OLD))
sys.path.insert(0, str(R4))
import dma_check
import network_check
import run as common

need = common.check_cycles.need


def build(verilator, out, env):
    sources = [
        *(OLD / name for name in ["mc_min_controller.sv", "lc_min_controller.sv", "tb_network_pm.sv"]),
        *(R4 / name for name in ["lc_raw16_s_adapter.sv", "tb_dma_local.sv", "tb_control_dma.sv",
                                 "raw16_dma_bridge.sv", "finite_external_memory.sv"]),
        *(RTL / name for name in ["block_local_s/block_local_s_arbiter.sv", "block_local_s/block_local_s_macro.sv",
                                  "block_feed_v1/block_feed_s16k.sv", "block_feed_v1/block_feed_loader.sv",
                                  "hbm_feed/hbm_group_dma.sv", "hbm_feed/hbm_async_fifo.sv"]),
    ]
    obj = out / "obj_dir"
    command = [verilator, "--binary", "--timing", "--top-module", "tb_control_dma", "-I" + str(OLD),
               "--Mdir", obj, "-j", os.environ.get("SLURM_CPUS_PER_TASK", "4"), "-o", "sim", *sources]
    log = common.run(command, out, env, out / "compile.log")
    return obj / "sim", dict(command=[str(arg) for arg in command], log_sha256=common.sha(log.encode()),
                             sv_sha256={p.relative_to(HERE.parent).as_posix(): common.sha(p.read_bytes())
                                        for p in sources})


def materialize(name, out):
    source = HERE / "examples" / (name + ".json")
    ir = source.read_bytes()
    baseline = HERE / "generated" / (name + ".bundle.json")
    frozen = json.loads(baseline.read_text(encoding="utf-8"))
    generated = compile_ir(ir)
    need(generated == frozen, "server compiler output differs from the published example")
    images, decoded = verify(ir, generated)
    provenance = {"ir_sha256": common.sha(ir), "bundle_sha256": common.sha(baseline.read_bytes()),
                  "manifest_sha256": generated["manifest_sha256"],
                  "target_sha256": generated["target_sha256"], "images": generated["manifest"]["images"]}
    args = []
    for role, data in images.items():
        path = out / (role + ".mem")
        path.write_text("".join(f"{int.from_bytes(data[i:i+16], 'little'):032x}\n"
                                for i in range(0, len(data), 16)), encoding="ascii")
        stem = "IMAGE" if role == "mother" else role.upper()
        count = "WORDS" if role == "mother" else "WORDS" + role[-1]
        args.extend(["+" + stem + "=" + str(path), f"+{count}={len(data) // 16}"])
    return images, decoded, provenance, args


def native_addresses(log, decoded, runs):
    source, destination = decoded["s_byte_addresses"]
    addresses = []
    for line in log.splitlines():
        if line.startswith("S "):
            _, block, _, kind, *fields = line.split()
            if kind == "REQ":
                addresses.append([int(block), int(fields[0]), 16 * int(fields[1])])
    expected = [[0, 1, source], [0, 0, source], [1, 1, destination]] * runs
    need(addresses == expected, "actual native S requests differ from the IR addresses or service order")
    return addresses


def run_case(sim, name, bundle, runs, stall, delay, poison, out, env):
    work = out / name
    work.mkdir()
    images, decoded, provenance, args = materialize(bundle, work)
    cmd = [sim, *args, f"+RUNS={runs}", f"+CALLS={2 * runs}", f"+STALL={stall}", f"+RETURN_DELAY={delay}"]
    case = dict(name=name, calls=2 * runs, runs=runs, stall=stall, return_delay=delay,
                locals=[dict(calls=runs, commands=2 * runs, reports=0),
                        dict(calls=runs, commands=runs, reports=runs)])
    if poison:
        cmd.extend(["+MODE=2", "+POISON=1"])
        case.update(mode=2, poison=1)
        case["locals"][0]["poison"] = 1
    log = common.run(cmd, work, env, work / "trace.log")
    need("PASS network" in log, "missing actual RTL completion marker")
    trace = network_check.decode(log)
    checked = network_check.check(trace, case, images)
    checked["native_S_RTL"] = True
    checked["mother"]["actual_local_RTL"] = 2
    dma = dma_check.check(log)
    need(dma["descriptors"] == 3 * runs, "unexpected number of actual DMA completions")
    requests = native_addresses(log, decoded, runs)
    print(f"{name} PASS | results={checked['mother']['results']} "
          f"poison={checked['mother']['poisoned']} cycles={len(trace['mother'])}", flush=True)
    return dict(case=case, source_graph=decoded, provenance=provenance, native_s_requests=requests,
                network=checked, DMA=dma, command=[str(arg) for arg in cmd],
                trace_sha256=common.sha(log.encode("utf-8")))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verilator", required=True)
    parser.add_argument("--out", required=True, type=pathlib.Path)
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    admitted = ir_checks()
    rejected = bundle_negative_checks()
    sim, compile_report = build(args.verilator, out, env)
    configurations = [
        ("joined_continuous", "joined_wait", 2, 2, 0, False),
        ("split_boundary_backpressure", "split_wait", 2, 3, 40, False),
        ("split_missing_ack", "split_wait", 1, 2, 0, True),
    ]
    results = [run_case(sim, *case, out, env) for case in configurations]
    report = dict(schema="control-r6-rtl-campaign/0.1", IR=admitted, rehashed_mutants_rejected=rejected,
                  compile=compile_report, results=results,
                  tools=dict(python=sys.version.split()[0],
                             verilator=common.run([args.verilator, "--version"], out, env).strip()),
                  hardware=dict(mother=1, locals=2, private_S=2, DMA=1, async_FIFO=2),
                  fixture=dict(external_memory_peer_words=64, domain_clock_ratio="5:3"))
    (out / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("PASS 3 generated-image cases, 4 completed jobs, 1 expected poison, 6 bundle mutants rejected",
          flush=True)


if __name__ == "__main__":
    main()
