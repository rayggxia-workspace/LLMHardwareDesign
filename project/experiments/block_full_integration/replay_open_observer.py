#!/usr/bin/env python3
"""Run finite original-openTPU observer qualification; never compile or substitute a DUT."""
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


def sha(p):
    h = hashlib.sha256()
    with Path(p).open("rb") as f:
        for b in iter(lambda: f.read(1048576), b""):
            h.update(b)
    return h.hexdigest()


def put(p, obj):
    with Path(p).open("x", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.write("\n")


def verify(refs):
    out = {}
    for item in refs:
        p = Path(item["path"])
        if p.stat().st_size != item["bytes"] or sha(p) != item["sha256"]:
            raise ValueError("Pinned input mismatch: " + str(p))
        out[str(p)] = item["sha256"]
    return out


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


def ready_next(x):
    x = (x ^ (x << 13)) & 0xffffffff
    x = (x ^ (x >> 17)) & 0xffffffff
    return (x ^ (x << 5)) & 0xffffffff


def trace_check(path, fields, case, metrics, writes, budgets, deadline):
    if not path.is_file() or path.stat().st_size > budgets["max_trace_bytes_per_case"]:
        raise ValueError("Trace missing or exceeds configured bound")
    names = [x["name"] for x in fields]
    if len(names) != 41 or len(names) != len(set(names)):
        raise ValueError("Unexpected observer schema")
    count = accepted = stalled = actual_writes = 0
    reset_seen_low = False
    prev = {}
    rng = 0x6d2b79f5 ^ (case["seed"] or 0)
    ready_patterns = []
    h = hashlib.sha256()
    last = None
    dt = None
    hold_fields = {
        "a": ("a_we", "a_addr", "a_wdata", "a_be"),
        "b": ("b_tag", "b_we", "b_par", "b_wmask", "b_wdata", "b_addr"),
        "sw": ("sw_addr", "sw_wdata", "sw_be"),
    }
    with path.open("rb") as stream:
        raw = stream.readline()
        h.update(raw)
        if raw.decode("ascii").rstrip("\r\n").split("\t") != names:
            raise ValueError("Trace header differs from compiled observer contract")
        for raw in stream:
            h.update(raw)
            count += 1
            if count > budgets["trace_max_rows"]:
                raise ValueError("Trace exceeds row bound")
            if count % 1024 == 0 and time.monotonic() >= deadline:
                raise TimeoutError("Replay budget exhausted while validating trace")
            values = raw.decode("ascii").rstrip("\r\n").split("\t")
            if len(values) != len(fields):
                raise ValueError("Incomplete or malformed trace row")
            row = {}
            for spec, value in zip(fields, values):
                if not value or value != value.strip():
                    raise ValueError("Malformed trace field")
                fmt = spec["format"][-1]
                alphabet = "01" if fmt == "b" else "0123456789abcdefABCDEF" if fmt == "h" else "0123456789"
                if any(x not in alphabet for x in value):
                    raise ValueError("Invalid/unknown trace value: " + spec["name"])
                n = int(value, 2 if fmt == "b" else 16 if fmt == "h" else 10)
                if spec["bits"] is not None and n >= 1 << spec["bits"]:
                    raise ValueError("Trace field exceeds declared width")
                row[spec["name"]] = n
            if row["cycle"] != count-1 or row["clk"] != 1:
                raise ValueError("Trace cycle sequence or rising-edge clock differs")
            if last is not None:
                step = row["time"]-last["time"]
                if step <= 0 or (dt is not None and step != dt):
                    raise ValueError("Nonuniform logical clock sample times")
                dt = step
            if not row["sys_rst"]:
                reset_seen_low = True
            elif reset_seen_low:
                raise ValueError("Unexpected new reset; this qualification has startup reset only")
            if case["seed"] is not None:
                force = ((count-1) & 15) == 15
                exp = [int(force or ((rng >> shift) & 3) != 0) for shift in (0, 2, 4)]
                actual = [row[x] for x in ("a_rdy", "b_rdy", "sw_rdy")]
                if actual != exp:
                    raise ValueError("Actual ready sequence differs from the declared seed at cycle " + str(count-1))
                if len(ready_patterns) < 32:
                    ready_patterns.append(actual)
                rng = ready_next(rng)
            if not row["sys_rst"]:
                for channel in ("a", "b", "sw"):
                    req, ready = row[channel+"_req"], row[channel+"_rdy"]
                    payload = tuple(row[x] for x in hold_fields[channel])
                    if channel in prev and (not req or payload != prev[channel]):
                        raise ValueError("Public payload changed under stall: " + channel)
                    if req and not ready:
                        prev[channel] = payload
                    else:
                        prev.pop(channel, None)
                    accepted += int(bool(req and ready))
                    stalled += int(bool(req and not ready))
                    actual_writes += int(bool(req and ready and (channel == "sw" or row[channel+"_we"])))
            last = row
    if not count or not reset_seen_low:
        raise ValueError("Trace contains no complete active run")
    if (accepted, stalled, actual_writes) != (metrics["accepted"], metrics["stalls"], writes):
        raise ValueError("Public trace acceptance/stall/write counts differ from actual TB counters")
    if last["icount"] != metrics["icount"]:
        raise ValueError("Final public frontend count differs from log")
    if case["seed"] is not None and stalled == 0:
        raise ValueError("Seed case did not actually exercise valid-request backpressure")
    return {"status": "PASS_TRACE_FORMAT_SEED_PROTOCOL_COUNTERS_ONLY",
            "path": str(path), "bytes": path.stat().st_size, "sha256": h.hexdigest(),
            "rows": count, "clock_step_in_printed_time_units": dt,
            "accepted": accepted, "stalls": stalled, "writes": actual_writes,
            "first32_ready_triplets": ready_patterns,
            "paired_integrated_trace_comparison": "NOT_RUN",
            "sampling": "posedge active pre-NBA; invalid payloads retained but not counted as accepted data"}


def parse_log(text, case, expected_trace):
    if re.search(r"%Error|%Warning|Assertion|FATAL|execution failure", text):
        raise ValueError("Runtime warning or failure")
    modes = re.findall(r"SIM_READY_MODE seeded=(\d+) seed=(\d+) legacy_stall=(\d+) trace=(\S+)", text)
    if len(modes) != 1:
        raise ValueError("Missing/duplicate ready-mode marker")
    seeded, seed, stall, path = modes[0]
    expected_stall = next(int(x.split("=", 1)[1]) for x in case["plusargs"] if x.startswith("+stall="))
    if int(seeded) != int(case["seed"] is not None) or int(seed) != (case["seed"] or 0) or int(stall) != expected_stall or path != str(expected_trace):
        raise ValueError("Runtime ready mode differs from requested stimulus")
    ws = re.findall(r"SIM_PUBLIC_WRITES count=(\d+)", text)
    closed = re.findall(r"SIM_TRACE_CLOSED rows=(\d+) path=(\S+)", text)
    if len(ws) != 1 or len(closed) != 1 or closed[0][1] != str(expected_trace):
        raise ValueError("Missing writes or closed trace receipt")
    writes = int(ws[0])
    if writes != case["expected_writes"]:
        raise ValueError("Unexpected externally accepted writes")
    if case["expected_timeout"]:
        rx = r"SIM_EXPECTED_TIMEOUT cycles=(\d+) icount=(\d+) accepted=(\d+) stalls=(\d+) error=(\d+) wait_to=(\d+) halted=(\d+) rd_idle=(\d+) drain_cycles=(\d+) stable_ticks=(\d+)"
        found = re.findall(rx, text)
        if len(found) != 1 or "SIM_COMPLETE" in text:
            raise ValueError("Wrong expected-timeout result marker")
        metrics = dict(zip(("cycles", "icount", "accepted", "stalls", "error", "wait_to", "halted", "rd_idle", "drain_cycles", "stable_ticks"), map(int, found[0])))
        if not 2 <= metrics["icount"] <= 4 or any(metrics[x] != 1 for x in ("error", "wait_to", "halted", "rd_idle")) or metrics["stable_ticks"] != 20 or metrics["drain_cycles"] > 100 or writes != 0:
            raise ValueError("Expected timeout/halt/drain/quiet contract violated")
    else:
        found = re.findall(r"SIM_COMPLETE cycles=(\d+) icount=(\d+) accepted=(\d+) stalls=(\d+)", text)
        if len(found) != 1 or "SIM_EXPECTED_TIMEOUT" in text:
            raise ValueError("Wrong completion marker")
        metrics = dict(zip(("cycles", "icount", "accepted", "stalls"), map(int, found[0])))
        if metrics["icount"] != case["expected_icount"]:
            raise ValueError("Wrong frontend instruction count")
    if case["legacy_metrics_must_match"] and metrics != case["legacy_metrics"]:
        raise ValueError("Observer changed existing legacy-run metrics")
    init = re.findall(r"SIM_INIT expected_timeout=(\d+) rinit_present=([0-9a-f]+)((?: rinit\d+=[0-9a-f]+){8})", text)
    if len(init) != 1 or int(init[0][0]) != int(case["expected_timeout"]):
        raise ValueError("Missing public-init marker")
    provided = {int(m.group(1)):int(m.group(2),16) for arg in case["plusargs"]
                for m in [re.fullmatch(r"\+rinit(\d+)=([0-9a-fA-F]+)",arg)] if m}
    expected = {i:provided.get(i,0) for i in range(8,16)}
    actual = {int(k):int(v,16) for k,v in re.findall(r"rinit(\d+)=([0-9a-f]+)",init[0][2])}
    if actual != expected or int(init[0][1],16) != (255 if provided else 0):
        raise ValueError("rinit public-port value/order differs")
    return metrics, writes, int(closed[0][0])


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", type=Path, default=Path(__file__).resolve().parent/"configs/open_observer_replay.json")
    ap.add_argument("--run-root", type=Path)
    ap.add_argument("--check-only", action="store_true")
    args = ap.parse_args()
    config_path = args.config.resolve(strict=True)
    cfg = json.loads(config_path.read_text())
    if cfg["schema"] != "open-observer-replay-v1" or cfg["DUT_kind"] != "original_RTL_full_small_with_observer":
        raise ValueError("Not an original-observer replay configuration")
    before = verify(cfg["locked_inputs"])
    compile_receipt = json.loads(Path(cfg["compile_receipt"]["path"]).read_text())
    if compile_receipt["status"] != "PASS_COMPILE_ONLY_OBSERVER_UNRUN" or not compile_receipt["inputs_unchanged"] or compile_receipt["binary"] != cfg["binary"]:
        raise ValueError("Compile/source lineage is not closed")
    old = json.loads(Path(cfg["original_receipt"]["path"]).read_text())
    if old["status"] != "PASS_ORIGINAL_RTL_PUBLIC_CONTROLS_8_CASES":
        raise ValueError("Old baseline was not actually PASS")
    cases = cfg["cases"]
    if len(cases)!=20 or sum(c["kind"]=="legacy_preservation" for c in cases)!=8 or sum(c["kind"]=="seeded_ready" for c in cases)!=12:
        raise ValueError("Unexpected expansion or loss of the bounded qualification suite")
    if len(set(c["id"] for c in cases))!=len(cases):
        raise ValueError("Duplicate case ID")
    for case in cases:
        if not re.fullmatch(r"[A-Za-z0-9_.-]+",case["id"]):
            raise ValueError("Unsafe case ID")
        if case["kind"]=="seeded_ready" and case["seed"] not in (0,1,2):
            raise ValueError("Unexpected seed")
        if any(not x.startswith(("+n=","+stall=","+ready_seed=","+rinit","+expect_wait_timeout=")) for x in case["plusargs"]):
            raise ValueError("Unexpected simulation argument")
        for name in ("initial_dram","expected_dram"):
            if case[name] not in cfg["locked_inputs"] or case[name]["bytes"]!=262144:
                raise ValueError("Unpinned or smaller memory input")
    contract = json.loads(Path(cfg["observer_contract"]["path"]).read_text())
    if args.check_only:
        print(json.dumps({"status":"READY_20_CASE_INPUTS_ONLY_NOT_RUN","cases":20,
                          "legacy":8,"seeded":12,"inputs":len(before)}))
        return 0
    if not os.environ.get("SLURM_JOB_ID"):
        raise ValueError("Actual replay requires Slurm")
    root = Path(cfg["task_root"]).resolve(strict=True)
    allowed = Path("/public/home/yuzelu/PingyangHuang").resolve(strict=True)
    if allowed not in root.parents or args.run_root is None:
        raise ValueError("Invalid task/output root")
    run = args.run_root
    if run.exists() or run.is_symlink():
        raise FileExistsError("Never reuse prior run")
    parent = run.parent.resolve(strict=True)
    if parent != root and root not in parent.parents:
        raise ValueError("Output escapes current task")
    if root/"worktree" in [parent]+list(parent.parents):
        raise ValueError("Outputs cannot go into the committed source")
    if shutil.disk_usage(parent).free < cfg["budgets"]["min_disk_free_bytes"]:
        raise ValueError("Insufficient free space")
    run.mkdir()
    run = run.resolve()
    for name in ("home","tmp","cache","cases"):
        (run/name).mkdir()
    env=dict(os.environ,HOME=str(run/"home"),TMPDIR=str(run/"tmp"),TMP=str(run/"tmp"),
             TEMP=str(run/"tmp"),XDG_CACHE_HOME=str(run/"cache"),PYTHONDONTWRITEBYTECODE="1",
             OMP_NUM_THREADS="1",OPENBLAS_NUM_THREADS="1",HISTFILE="/dev/null")
    result={"status":"RUNNING_ORIGINAL_OBSERVER_QUALIFICATION","DUT_kind":cfg["DUT_kind"],
            "job_id":os.environ["SLURM_JOB_ID"],"input_sha256":before,
            "config_path":str(config_path),"config_sha256":sha(config_path),
            "runner_sha256":sha(__file__),"tests":[],"scope":cfg["scope"],
            "new_integrated_DUT_executed":False,"paired_cycle_equivalence":"NOT_RUN"}
    put(run/"started.json",result)
    signal.signal(signal.SIGTERM,signal_abort)
    signal.signal(signal.SIGINT,signal_abort)
    deadline=time.monotonic()+cfg["budgets"]["total_seconds"]
    proc=None
    try:
        ldd=subprocess.run(["ldd",cfg["binary"]["path"]],cwd=str(run),env=env,
                           stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                           universal_newlines=True,timeout=20)
        with (run/"ldd.log").open("x") as f:f.write(ldd.stdout)
        if ldd.returncode or "not found" in ldd.stdout:
            raise RuntimeError("Qualified container runtime libraries missing")
        for case in cases:
            wd=run/"cases"/case["id"];wd.mkdir()
            initial=wd/"dram_0.bin"
            with Path(case["initial_dram"]["path"]).open("rb") as src,initial.open("xb") as dst:
                shutil.copyfileobj(src,dst)
            if sha(initial)!=case["initial_dram"]["sha256"]:
                raise ValueError("Copied memory input differs")
            trace=wd/"public_trace.tsv"
            argv=[cfg["binary"]["path"],"+dir="+str(wd)]+case["plusargs"]+["+trace_path="+str(trace)]
            log=wd/"simulation.log"
            limit=min(cfg["budgets"]["per_case_seconds"],deadline-time.monotonic())
            if limit<=0:raise TimeoutError("Replay total budget exhausted")
            entry={"id":case["id"],"seed":case["seed"],"kind":case["kind"],
                   "command":argv,"cwd":str(wd),"log":str(log),"status":"RUNNING"}
            result["tests"].append(entry)
            def bounds():
                resource.setrlimit(resource.RLIMIT_CORE,(0,0))
                cap=cfg["budgets"]["AS_bytes"];resource.setrlimit(resource.RLIMIT_AS,(cap,cap))
            t=time.monotonic()
            with log.open("xb") as f:
                try:
                    proc=subprocess.Popen(argv,cwd=str(wd),env=env,stdout=f,stderr=subprocess.STDOUT,
                                          start_new_session=True,preexec_fn=bounds)
                    rc=proc.wait(timeout=limit)
                finally:
                    stop_group(proc);proc=None
            entry.update(returncode=rc,seconds=time.monotonic()-t,log_sha256=sha(log))
            if rc:raise RuntimeError("Simulation returned "+str(rc))
            metrics,writes,logged_rows=parse_log(log.read_text(errors="replace"),case,trace)
            actual=wd/"dram_out_0.bin"
            if not actual.is_file() or actual.stat().st_size!=262144:
                raise ValueError("Full memory dump missing or wrong size")
            expected=Path(case["expected_dram"]["path"])
            if actual.read_bytes()!=expected.read_bytes():
                raise ValueError("Actual full DRAM differs from the unchanged original oracle")
            tinfo=trace_check(trace,contract["fields"],case,metrics,writes,cfg["budgets"],deadline)
            if tinfo["rows"]!=logged_rows:
                raise ValueError("Closed trace row count differs from actual file")
            if sha(initial)!=case["initial_dram"]["sha256"]:
                raise ValueError("Simulation modified its input DRAM file")
            entry.update(status="PASS_ORIGINAL_FULL_CORE_FINITE_OBSERVER_CASE",
                         metrics=metrics,accepted_write_requests=writes,trace=tinfo,
                         actual_dram={"path":str(actual),"bytes":262144,"sha256":sha(actual)},
                         expected_dram=case["expected_dram"],full_memory_mismatches=0)
            put(wd/"case_result.json",entry)
        result["status"]="PASS_ORIGINAL_OBSERVER_LEGACY8_SEEDED12"
    except BaseException as exc:
        stop_group(proc)
        result["status"]="FAIL_ORIGINAL_OBSERVER_QUALIFICATION"
        result["error"]=type(exc).__name__+": "+str(exc)
    finally:
        try:
            after=verify(cfg["locked_inputs"]);result["input_sha256_after"]=after
            result["inputs_unchanged"]=after==before
            if not result["inputs_unchanged"] or sha(config_path)!=result["config_sha256"] or sha(__file__)!=result["runner_sha256"]:
                raise ValueError("Input/config/runner changed")
        except BaseException as exc:
            result["inputs_unchanged"]=False;result["status"]="FAIL_INPUT_IDENTITY"
            result["identity_error"]=type(exc).__name__+": "+str(exc)
        result["completed_utc"]=datetime.datetime.now(datetime.timezone.utc).isoformat()
        put(run/"execution.json",result)
    print(json.dumps({"status":result["status"],"receipt":str(run/"execution.json"),
                      "sha256":sha(run/"execution.json")}))
    return 0 if result["status"]=="PASS_ORIGINAL_OBSERVER_LEGACY8_SEEDED12" else 1


if __name__=="__main__":
    raise SystemExit(main())
