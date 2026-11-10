"""Eight same-work port diagnostics. No numerical/DDR/workload changes."""
import hashlib
import json
import os
from pathlib import Path
import subprocess

PLANS = [
    ("legacy-Xreg", 0, 0, 1, 0, 1),
    ("legacy-NoPool", 4, 0, 1, 0, 1),
    ("P128-Xreg", 0, 1, 1, 0, 1),
    ("P128-NoPool", 4, 1, 1, 0, 1),
    ("all128-Xreg", 0, 2, 1, 0, 1),
    ("all128-NoPool", 4, 2, 1, 0, 1),
    ("all128-NoPool-response1-ACK2", 4, 2, 1, 1, 2),
    ("all128-NoPool-word2", 4, 2, 2, 0, 1),
]
name, mode, scope, word_cycles, response_cycles, ack = PLANS[int(os.environ["SLURM_PROCID"])]
HERE = Path.cwd()
out = HERE / name
out.mkdir(exist_ok=False)
base = {k: v for k, v in os.environ.items() if not k.startswith(("SQ_", "BN_", "CL_", "NV_", "SF_", "SX_", "NS_"))}
env = dict(base, SQ_DIRECT="1", SQ_ABITS="16", SQ_BREAD="128", SQ_PCOUNT="3",
           SQ_CORE_K="16", SQ_BEAT="64", SQ_STRIPE="1", BN_RELEASE="2", CL_MODE="6",
           CL_ISSUE="2", CL_BANKS="4", CL_HEAD_GROUP="16", NV_BITS="32", NV_EXTRA="1",
           NV_MID="1", SQ_BW_MB="51200", SX_MODE=str(mode), SX_DESC_CYCLES="2",
           SX_LATENCY="2", SX_LOCAL_WIDTH="16", SX_LOCAL_LATENCY=str(ack),
           SX_SLOTS="2", SX_RETIRE_CYCLES="1", SX_PHASE_CYCLES="4", SX_EARLY=str(int(mode == 4)),
           SX_A_SLOTS="2", SX_COPY_LATENCY=str(ack), NS_PORT_SCOPE=str(scope),
           NS_WORD_CYCLES=str(word_cycles), NS_RESPONSE_CYCLES=str(response_cycles))
args = ["queued_pipe_w8", "prefix_pair_combine", "8", "1", "1", "16", "0", "4", "0", "1", "1", "1"]
trace = Path("/public/home/yuzelu/project-circuit/issue248-stream-quant-20261110-40/restored/inputs/decode512.trace")
report = dict(plan=name, passed=False, source_env={k: v for k, v in env.items() if k.startswith(("SQ_", "BN_", "CL_", "NV_", "SX_", "NS_"))},
              job=os.environ["SLURM_JOB_ID"], input_trace_SHA256=hashlib.sha256(trace.read_bytes()).hexdigest(), results=[],
              qualification="S128 sensitivity; operator/control pipelines and energy NOT fully calibrated")


def save():
    (out / "report.json").write_text(json.dumps(report, indent=2) + "\n")


try:
    for label, current in (("micro", HERE / "generated/micro.trace"), ("decode512", trace)):
        with (out / (label + ".log")).open("w") as log:
            subprocess.run([str(HERE / "candidate.exe"), str(current)] + args, env=env,
                           stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=2400)
        result = [json.loads(line[7:]) for line in (out / (label + ".log")).read_text().splitlines() if line.startswith("RESULT ")]
        assert len(result) == 1
        report["results"].append(dict(label=label, result=result[0]))
        save()
        print("CASE_PASS", name, label, result[0]["tokens_per_second"], flush=True)
    report["passed"] = True
    save()
except Exception as error:
    report["error"] = repr(error)
    save()
    raise
