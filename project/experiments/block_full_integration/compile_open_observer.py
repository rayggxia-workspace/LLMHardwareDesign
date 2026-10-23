#!/usr/bin/env python3
"""Compile only the unchanged original full-small DUT with a new public observer TB."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import shutil
import signal
import subprocess
import time

HERE = Path(__file__).resolve().parent


def sha(p):
    h = hashlib.sha256()
    with Path(p).open("rb") as f:
        for b in iter(lambda: f.read(1048576), b""):
            h.update(b)
    return h.hexdigest()


def save_new(p, obj):
    with Path(p).open("x") as f:
        json.dump(obj, f, indent=2)
        f.write("\n")


def stop_group(p):
    if p is None:
        return
    try:
        os.killpg(p.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        p.wait(timeout=2)
    except subprocess.TimeoutExpired:
        pass
    try:
        os.killpg(p.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    if p.poll() is None:
        p.wait(timeout=5)


def signal_abort(signum, frame):
    raise RuntimeError("Termination signal " + str(signum))


def validate(cfg, recipe):
    if cfg["schema"] != "open-observer-compile-v1" or cfg["DUT_kind"] != "original_RTL_full_small_with_new_TB_only":
        raise ValueError("Unsupported recipe")
    receipt = json.loads(Path(cfg["original_receipt"]["path"]).read_text())
    if receipt["status"] != cfg["original_status_expected"]:
        raise ValueError("Original baseline receipt is not the exact expected PASS")
    refs = list(cfg["locked_original_inputs"]) + cfg["tool_refs"] + [cfg["verilator_wrapper"]]
    for key in ("TB", "TB_contract"):
        item = cfg[key]
        p = HERE / item["relative"]
        if HERE not in p.resolve(strict=True).parents:
            raise ValueError("New testbench source escapes committed code")
        refs.append({"path": str(p), "bytes": p.stat().st_size, "sha256": item["sha256"]})
    refs.append({"path": str(recipe), "bytes": recipe.stat().st_size, "sha256": sha(recipe)})
    refs.append({"path": str(Path(__file__).resolve()), "bytes": Path(__file__).stat().st_size, "sha256": sha(__file__)})
    observed = {}
    for item in refs:
        p = Path(item["path"])
        if p.stat().st_size != item["bytes"] or sha(p) != item["sha256"]:
            raise ValueError("Pinned source/tool differs: " + str(p))
        observed[str(p)] = item["sha256"]
    bundle = Path(cfg["original_bundle"])
    included = re.findall(chr(96) + r'include\s+"([^"]+)"', bundle.read_text())
    if len(included) != cfg["original_include_count"] or set(included) - set(observed):
        raise ValueError("Unpinned or missing original include")
    contract = json.loads((HERE/cfg["TB_contract"]["relative"]).read_text())
    if not contract["old_protocol_and_write_counter_block_byte_identical"]:
        raise ValueError("Original assertion preservation not declared")
    old = Path(contract["source"]["path"])
    if sha(old) != contract["source"]["sha256"]:
        raise ValueError("Original TB changed")
    text = old.read_text()
    block = text[text.index("  always @(posedge clk) begin"):text.index("  initial begin")]
    if sha(HERE/cfg["TB"]["relative"]) != contract["derived"]["sha256"]:
        raise ValueError("Derived TB/contract mismatch")
    if block not in (HERE/cfg["TB"]["relative"]).read_text():
        raise ValueError("Original protocol/counter block was changed")
    if cfg["DUT_top_macro"] != "otpu_asic_top":
        raise ValueError("This recipe is only the original top, never an integrated fallback")
    return observed


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--recipe", type=Path, default=HERE/"configs/open_observer_compile.json")
    ap.add_argument("--run-root", type=Path)
    ap.add_argument("--check-only", action="store_true")
    a = ap.parse_args()
    recipe = a.recipe.resolve(strict=True)
    cfg = json.loads(recipe.read_text())
    before = validate(cfg, recipe)
    if a.check_only:
        print(json.dumps({"status": "READY_INPUTS_ONLY_NOT_COMPILED",
                          "source_tool_files": len(before), "DUT_kind": cfg["DUT_kind"]}))
        return 0
    if not os.environ.get("SLURM_JOB_ID"):
        raise ValueError("Compile requires Slurm")
    if a.run_root is None:
        raise ValueError("--run-root required")
    root = Path(cfg["task_root"]).resolve(strict=True)
    allowed = Path("/public/home/yuzelu/PingyangHuang").resolve(strict=True)
    if allowed not in root.parents:
        raise ValueError("Invalid task root")
    run = a.run_root
    if run.exists() or run.is_symlink():
        raise FileExistsError("Never reuse a compile output")
    parent = run.parent.resolve(strict=True)
    if parent != root and root not in parent.parents:
        raise ValueError("Output escapes current task")
    if root/"worktree" in [parent] + list(parent.parents):
        raise ValueError("Compiled outputs cannot go into committed worktree")
    if shutil.disk_usage(parent).free < cfg["budgets"]["min_disk_free_bytes"]:
        raise ValueError("Insufficient free disk")
    run.mkdir()
    run = run.resolve()
    for name in ("obj", "tmp", "home", "cache"):
        (run/name).mkdir()
    env = dict(os.environ, HOME=str(run/"home"), TMPDIR=str(run/"tmp"),
               TMP=str(run/"tmp"), TEMP=str(run/"tmp"), XDG_CACHE_HOME=str(run/"cache"),
               CCACHE_DIR=str(run/"cache"), OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1",
               PYTHONDONTWRITEBYTECODE="1", HISTFILE="/dev/null",
               VERILATOR_ROOT=cfg["verilator_prefix"]+"/share/verilator")
    result = {"status": "STARTED_COMPILE_ONLY", "DUT_kind": cfg["DUT_kind"],
              "job_id": os.environ["SLURM_JOB_ID"], "inputs_sha256": before,
              "recipe": str(recipe), "recipe_sha256": sha(recipe),
              "commands": [], "simulation_executed": False, "functional_verified": False,
              "integrated_DUT_verified": False, "scope_limits": cfg["scope_limits"]}
    save_new(run/"started.json", result)
    signal.signal(signal.SIGTERM, signal_abort)
    signal.signal(signal.SIGINT, signal_abort)
    deadline = time.monotonic() + cfg["budgets"]["total_seconds"]
    proc = None

    def command(label, argv, seconds):
        nonlocal proc
        limit = min(seconds, deadline-time.monotonic())
        if limit <= 0:
            raise TimeoutError("Total compile budget exhausted")
        log = run/(label+".log")
        row = {"label": label, "argv": argv, "cwd": str(run), "log": str(log),
               "timeout_seconds": limit}
        result["commands"].append(row)
        def child_limits():
            resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
            cap = cfg["budgets"]["AS_bytes"]
            resource.setrlimit(resource.RLIMIT_AS, (cap, cap))
        start = time.monotonic()
        with log.open("xb") as f:
            try:
                proc = subprocess.Popen(argv, cwd=str(run), env=env, stdout=f,
                                        stderr=subprocess.STDOUT, start_new_session=True,
                                        preexec_fn=child_limits)
                rc = proc.wait(timeout=limit)
            finally:
                stop_group(proc)
                proc = None
        row.update(returncode=rc, elapsed_seconds=time.monotonic()-start, log_sha256=sha(log))
        if rc != 0:
            raise RuntimeError(label + " returned " + str(rc))
        return log

    try:
        version_log = command("verilator-version", [cfg["verilator_wrapper"]["path"], "--version"], 20)
        compiler_log = command("compiler-version", [cfg["compiler"], "--version"], 20)
        result["tool_versions"] = {"verilator": version_log.read_text().strip(),
                                   "compiler": compiler_log.read_text().strip()}
        gen = [cfg["verilator_wrapper"]["path"]] + cfg["verilator_flags"] + [
            "-DBLOCK_INTEGRATION_OPENTPU_TOP="+cfg["DUT_top_macro"],
            "--top-module", cfg["top_module"], "--Mdir", str(run/"obj"),
            cfg["original_bundle"], cfg["original_DRAM_model"], str(HERE/cfg["TB"]["relative"])]
        genlog = command("generate", gen, cfg["budgets"]["generate_seconds"])
        cpp = list((run/"obj").glob("*.cpp"))
        if not cpp:
            raise RuntimeError("No generated C++")
        result["generated_CPP"] = {"count": len(cpp), "bytes": sum(x.stat().st_size for x in cpp)}
        warning_lines = [line for line in genlog.read_text(errors="replace").splitlines() if line.startswith("%Warning")]
        result["actual_warnings"] = warning_lines
        result["warning_scope"] = "Warnings preserved for review; exit0 does not prove functional equivalence"
        make = ["make", "-C", str(run/"obj"), "-f", "Vtb_asic_baseline.mk", "-j1"] + cfg["make_overrides"]
        command("build", make, cfg["budgets"]["build_seconds"])
        binary = run/"obj/Vtb_asic_baseline"
        if not binary.is_file():
            raise RuntimeError("Build did not produce the expected full top binary")
        result["binary"] = {"path": str(binary), "bytes": binary.stat().st_size, "sha256": sha(binary)}
        result["status"] = "PASS_COMPILE_ONLY_OBSERVER_UNRUN"
    except BaseException as exc:
        stop_group(proc)
        result["status"] = "FAIL_COMPILE_OBSERVER"
        result["error"] = type(exc).__name__ + ": " + str(exc)
    finally:
        try:
            result["inputs_sha256_after"] = validate(cfg, recipe)
            result["inputs_unchanged"] = before == result["inputs_sha256_after"]
            if not result["inputs_unchanged"]:
                raise ValueError("Inputs changed during build")
        except BaseException as exc:
            result["inputs_unchanged"] = False
            result["status"] = "FAIL_INPUT_IDENTITY"
            result["identity_error"] = type(exc).__name__ + ": " + str(exc)
        result["completed_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        save_new(run/"execution.json", result)
    print(json.dumps({"status": result["status"], "receipt": str(run/"execution.json"),
                      "sha256": sha(run/"execution.json")}))
    return 0 if result["status"] == "PASS_COMPILE_ONLY_OBSERVER_UNRUN" else 1


if __name__ == "__main__":
    raise SystemExit(main())
