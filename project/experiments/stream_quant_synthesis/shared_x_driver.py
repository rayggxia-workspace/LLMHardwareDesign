"""Same full decode trace, arithmetic and off-chip traffic for six X plans."""
import hashlib
import json
import os
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
PLANS = [("baseline-Xreg", 0, 1, 2, 16, 2, 1, 2, 0, 2, 1, 1), ("shared-slot2-prep8-lat4", 1, 8, 4, 16, 2, 2, 2, 0, 2, 1, 1),
         ("S16-final-prep2", 4, 2, 2, 16, 2, 1, 4, 1, 2, 1, 1), ("S16-final-prep8", 4, 8, 2, 16, 2, 1, 8, 1, 2, 1, 1),
         ("S16-final-prep16", 4, 16, 2, 16, 2, 1, 8, 1, 2, 1, 1), ("S16-final-stateACK2", 4, 16, 2, 16, 2, 1, 8, 1, 2, 1, 2),
         ("S16-final-copyACK2", 4, 16, 2, 16, 2, 1, 8, 1, 2, 2, 1), ("S16-final-bothACK2", 4, 16, 2, 16, 2, 1, 8, 1, 2, 2, 2)]
rank = int(os.environ["SLURM_PROCID"])
name, mode, desc_cycles, latency, local_width, slots, retire, phase, early, a_slots, copy_latency, state_latency = PLANS[rank]
out = HERE / name
out.mkdir(exist_ok=False)
base = {k: v for k, v in os.environ.items() if not k.startswith(("SQ_", "BN_", "CL_", "NV_", "SF_", "SX_"))}
env = dict(base, SQ_DIRECT="1", SQ_ABITS="16", SQ_BREAD="128", SQ_PCOUNT="3",
           SQ_CORE_K="16", SQ_BEAT="64", SQ_STRIPE="1", BN_RELEASE="2", CL_MODE="6",
           CL_ISSUE="2", CL_BANKS="4", CL_HEAD_GROUP="16", NV_BITS="32", NV_EXTRA="1",
           NV_MID="1", SQ_BW_MB="51200", SX_MODE=str(mode),
           SX_DESC_CYCLES=str(desc_cycles), SX_LATENCY=str(latency), SX_LOCAL_WIDTH=str(local_width), SX_LOCAL_LATENCY=str(state_latency),
           SX_SLOTS=str(slots), SX_RETIRE_CYCLES=str(retire), SX_PHASE_CYCLES=str(phase),
           SX_EARLY=str(early), SX_A_SLOTS=str(a_slots), SX_COPY_LATENCY=str(copy_latency))
args = ["queued_pipe_w8", "prefix_pair_combine", "8", "1", "1", "16", "0", "4", "0", "1", "1", "1"]
trace = Path("/public/home/yuzelu/project-circuit/issue248-stream-quant-20261110-40/restored/inputs/decode512.trace")
report = dict(plan=name, passed=False, source_env={k: v for k, v in env.items() if k.startswith(("SQ_", "BN_", "CL_", "NV_", "SX_"))},
              job=os.environ["SLURM_JOB_ID"], input_trace_SHA256=hashlib.sha256(trace.read_bytes()).hexdigest(), results=[])


def save():
    (out / "report.json").write_text(json.dumps(report, indent=2) + "\n")


try:
    for label, current in (("micro", HERE / "micro.trace"), ("decode512", trace)):
        with (out / (label + ".log")).open("w") as log:
            subprocess.run([str(HERE / "candidate.exe"), str(current)] + args, env=env,
                           stdout=log, stderr=subprocess.STDOUT, check=True, timeout=2400)
        lines = (out / (label + ".log")).read_text().splitlines()
        result = [json.loads(line[7:]) for line in lines if line.startswith("RESULT ")]
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
