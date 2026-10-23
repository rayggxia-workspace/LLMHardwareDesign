#!/usr/bin/env python3
"""Replay existing source-bound baseline binaries in a new task directory.

This does not compile or modify a DUT/TB. PASS is limited to the exact original
baseline tests and does not validate a new Block-integrated design.
"""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import resource
import signal
import subprocess
import time


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for buf in iter(lambda: f.read(1024 * 1024), b""):
            h.update(buf)
    return h.hexdigest()


def write_new(path, obj):
    with Path(path).open("x", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)
        f.write("\n")


def verify(refs):
    got = {}
    for ref in refs:
        p = Path(ref["path"])
        if not p.is_file() or p.stat().st_size != ref["bytes"]:
            raise ValueError("Input missing or size differs: " + str(p))
        digest = sha(p)
        if digest != ref["sha256"]:
            raise ValueError("Input SHA mismatch: " + str(p))
        got[str(p)] = digest
    return got


def stop_group(proc):
    if proc is None:
        return
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        proc.wait(timeout=2)
    except subprocess.TimeoutExpired:
        pass
    # Kill residual descendants even if the group leader already exited.
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    if proc.poll() is None:
        proc.wait(timeout=5)


def termination_signal(signum, frame):
    raise RuntimeError("Termination signal " + str(signum))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", type=Path, required=True)
    ap.add_argument("--run-root", type=Path)
    ap.add_argument("--check-only", action="store_true")
    args = ap.parse_args()
    cfg = json.loads(args.config.read_text(encoding="utf-8"))
    if cfg["schema"] != "baseline-extra-v1" or cfg["DUT_kind"] != "original_RTL_baseline_existing_binary":
        raise ValueError("Unsupported DUT/config kind")
    task = Path(cfg["task_root"]).resolve(strict=True)
    allowed = Path("/public/home/yuzelu/PingyangHuang").resolve(strict=True)
    if allowed not in task.parents:
        raise ValueError("Invalid task root")
    refs = cfg["locked_inputs"]
    before = verify(refs)
    if len(cfg["tests"]) != 2 or sorted(t["seed"] for t in cfg["tests"]) != [0, 2]:
        raise ValueError("This bounded extension is exactly seeds 0 and 2")
    binary = Path(cfg["binary"]["path"])
    if cfg["binary"] not in refs:
        raise ValueError("Binary is not locked")
    for test in cfg["tests"]:
        if test["argv"] != [str(binary), "+seed=" + str(test["seed"]), "+cases=30"]:
            raise ValueError("Unexpected replay command")
        if test["expected_passed"] != 60 or test["expected_failed"] != 0:
            raise ValueError("Refusing weaker assertions")
    if args.check_only:
        print(json.dumps({"status": "READY_INPUTS_ONLY_NOT_EXECUTED",
                          "input_count": len(before), "tests": 2,
                          "scope": cfg["scope"]}, ensure_ascii=False))
        return 0
    if not os.environ.get("SLURM_JOB_ID"):
        raise ValueError("Actual replay must run in an allocated Slurm job")
    if args.run_root is None:
        raise ValueError("--run-root required for actual replay")
    run = args.run_root
    if run.exists() or run.is_symlink():
        raise FileExistsError("Never overwrite a run directory")
    parent = run.parent.resolve(strict=True)
    if parent != task and task not in parent.parents:
        raise ValueError("Run output escapes this task")
    run.mkdir()
    run = run.resolve(strict=True)
    for name in ("home", "tmp", "cache", "cases"):
        (run / name).mkdir()
    env = dict(os.environ)
    env.update(HOME=str(run/"home"), TMPDIR=str(run/"tmp"), TMP=str(run/"tmp"),
               TEMP=str(run/"tmp"), XDG_CACHE_HOME=str(run/"cache"),
               PYTHONDONTWRITEBYTECODE="1", OMP_NUM_THREADS="1",
               OPENBLAS_NUM_THREADS="1", HISTFILE="/dev/null")
    result = {"status": "RUNNING_ORIGINAL_BASELINE_ONLY",
              "scope": cfg["scope"], "DUT_kind": cfg["DUT_kind"],
              "new_integrated_DUT_executed": False,
              "job_id": os.environ["SLURM_JOB_ID"],
              "created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "input_sha256": before, "config_path": str(args.config.resolve()),
              "config_sha256": sha(args.config), "runner_sha256": sha(__file__),
              "runtime": {"platform": platform.platform(), "libc": platform.libc_ver()},
              "tests": [], "limitations": cfg["limitations"]}
    write_new(run/"started.json", result)
    signal.signal(signal.SIGTERM, termination_signal)
    signal.signal(signal.SIGINT, termination_signal)
    deadline = time.monotonic() + cfg["budgets"]["total_seconds"]
    proc = None
    try:
        # ldd itself can exit 0 despite version-not-found diagnostics.
        ldd = subprocess.run(["ldd", str(binary)], stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT, universal_newlines=True,
                             timeout=20, env=env, cwd=str(run))
        with (run/"ldd.log").open("x", encoding="utf-8") as f:
            f.write(ldd.stdout)
        result["runtime"]["ldd_returncode"] = ldd.returncode
        if ldd.returncode != 0 or "not found" in ldd.stdout:
            raise RuntimeError("Required runtime libraries unavailable; use the qualified container")
        for test in cfg["tests"]:
            case = run/"cases"/test["id"]
            case.mkdir()
            log = case/"simulation.log"
            limit = min(cfg["budgets"]["per_test_seconds"], deadline-time.monotonic())
            if limit <= 0:
                raise TimeoutError("Total replay budget exhausted before next test")
            def limits():
                resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
                ceiling = cfg["budgets"]["address_space_bytes"]
                resource.setrlimit(resource.RLIMIT_AS, (ceiling, ceiling))
            started = time.monotonic()
            row = {"id": test["id"], "seed": test["seed"],
                   "command": test["argv"], "cwd": str(case),
                   "status": "RUNNING", "timeout_seconds": limit, "log": str(log)}
            result["tests"].append(row)
            with log.open("xb") as output:
                try:
                    proc = subprocess.Popen(test["argv"], cwd=str(case), env=env,
                                            stdout=output, stderr=subprocess.STDOUT,
                                            start_new_session=True, preexec_fn=limits)
                    rc = proc.wait(timeout=limit)
                except BaseException:
                    stop_group(proc)
                    raise
                finally:
                    stop_group(proc)
                    proc = None
            row.update(returncode=rc, elapsed_seconds=time.monotonic()-started,
                       log=str(log), log_sha256=sha(log), log_bytes=log.stat().st_size)
            text = log.read_text(encoding="utf-8", errors="replace")
            matches = re.findall(r"^tb_system \(real engines\): (\d+) passed, (\d+) failed -> (PASS|FAIL)$",
                                 text, flags=re.MULTILINE)
            if rc != 0 or len(matches) != 1:
                row["status"] = "FAIL_EXECUTION_OR_SUMMARY"
                raise RuntimeError("Nonzero exit or missing/duplicate exact test summary")
            passed, failed, status = matches[0]
            row["observed"] = {"passed": int(passed), "failed": int(failed),
                               "reported_status": status, "launches": 30,
                               "full_DRAM_compare": "in-harness assertion on every launch",
                               "direct_memory_dump_exported": False,
                               "public_cycle_trace_exported": False}
            if (int(passed), int(failed), status) != (test["expected_passed"], test["expected_failed"], "PASS"):
                row["status"] = "FAIL_ASSERTIONS"
                raise RuntimeError("Actual assertion counts do not meet the original contract")
            row["status"] = "PASS_ORIGINAL_RTL_FINITE_SYSTEM_CASES"
        result["status"] = "PASS_ORIGINAL_RTL_SEEDS_0_2_EXTENSION"
    except BaseException as exc:
        stop_group(proc)
        result["status"] = "FAIL_ORIGINAL_BASELINE_EXTENSION"
        result["error"] = type(exc).__name__ + ": " + str(exc)
    finally:
        try:
            after = verify(refs)
            result["input_sha256_after"] = after
            result["inputs_unchanged"] = before == after
            if sha(args.config) != result["config_sha256"] or sha(__file__) != result["runner_sha256"]:
                raise ValueError("Config or runner changed during execution")
        except BaseException as exc:
            result["inputs_unchanged"] = False
            result["status"] = "FAIL_INPUT_IDENTITY"
            result["identity_error"] = type(exc).__name__ + ": " + str(exc)
        result["completed_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        write_new(run/"execution.json", result)
    print(json.dumps({"status": result["status"], "receipt": str(run/"execution.json"),
                      "sha256": sha(run/"execution.json")}, ensure_ascii=False))
    return 0 if result["status"] == "PASS_ORIGINAL_RTL_SEEDS_0_2_EXTENSION" else 1


if __name__ == "__main__":
    raise SystemExit(main())
