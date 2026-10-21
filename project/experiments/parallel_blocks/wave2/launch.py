"""Submit three bounded, isolated work streams; no job or test wall-clock deadline."""
import argparse
import datetime
import json
from pathlib import Path
import re
import shlex
import subprocess

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
HOST = "yuzelu@10.129.166.172"
IMAGE = "/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif"
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--attempt", required=True)
parser.add_argument("--profile", choices=("full", "physical", "gemm-receipt", "top-contract", "abc-probe", "abc-probe-short", "retired-evidence", "act-audit", "full-physical-audit", "targeted-repair"), default="full")
parser.add_argument('--dependency', help='Explicit one-shot Slurm dependency, e.g. afterany:89499')
args = parser.parse_args()
assert re.fullmatch(r"parallel-blocks-wave2-[0-9]+", args.attempt)
if args.dependency:
    assert re.fullmatch(r'afterany:\d+(?::\d+)*',args.dependency)
remote = "/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-7/" + args.attempt


def ssh(command):
    return subprocess.check_output(["ssh", "-n", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15", HOST, command], text=True).strip()


def task(name, kind, cores, case="opentpu-act", margin=0):
    return dict(name=name, kind=kind, cores=cores, case=case, cap_margin=margin)


plan = {"A": {"node": "node7", "cores": 64, "tasks": [
    task("act-cap00", "physical", 16), task("act-cap10", "physical", 16, margin=10),
    task("act-cap20", "physical", 16, margin=20), task("opentpu-validation", "opentpu-validation", 8),
    task("gemm-regression", "gemm-regression", 8, case="llaccel-gemm")]},
    "B": {"node": "node8", "cores": 64, "tasks": [
        task("gemm-cap10", "physical", 16, case="llaccel-gemm", margin=10),
        task("gemm-cap20", "physical", 16, case="llaccel-gemm", margin=20),
        task("mxu-cap20", "physical", 16, case="opentpu-mxu", margin=20),
        task("merged-cap20", "physical", 16, case="opentpu-act-mxu", margin=20)]},
    "C": {"node": "node9", "cores": 8, "tasks": [task("baseline-views", "baseline-views", 8)]}}
if args.profile == 'gemm-receipt':
    plan={'C': {'node':'node9','cores':1,'tasks':[task('gemm-receipt','gemm-receipt',1,case='llaccel-gemm')]}}
if args.profile == 'top-contract':
    plan={'C': {'node':'node9','cores':1,'tasks':[task('top-contract','top-contract',1)]}}
if args.profile == 'abc-probe':
    plan={'C': {'node':'node9','cores':2,'tasks':[task('abc-probe-short','abc-probe',1),task('abc-probe-long','abc-probe',1)]}}
if args.profile == 'abc-probe-short':
    plan={'C': {'node':'node9','cores':1,'tasks':[task('abc-probe-short','abc-probe',1)]}}
if args.profile == 'physical':
    plan={label: stream for label, stream in plan.items() if label in ('A','B')}
    plan['A']['tasks']=[t for t in plan['A']['tasks'] if t['kind']=='physical']
    plan['A']['cores']=sum(t['cores'] for t in plan['A']['tasks'])
if args.profile == 'retired-evidence':
    plan={'C': {'node':'node9','cores':1,'tasks':[task('retired-evidence','retired-evidence',1)]}}
if args.profile in ('act-audit','full-physical-audit'):
    name='act-sweep-audit' if args.profile=='act-audit' else 'full-physical-audit'
    plan={'C': {'node':'node9','cores':1,'tasks':[task(name,'physical-audit',1)]}}
if args.profile == 'targeted-repair':
    act = task('act-cap10-repair', 'route-repair', 16, margin=10)
    act.update(source_task='act-cap10', replacements=[['_5406_', 'MUX2_X1', 'MUX2_X2']])
    merged = task('merged-cap20-repair', 'route-repair', 16, case='opentpu-act-mxu', margin=20)
    merged.update(source_task='merged-cap20', replacements=[
        ['u_mxu.g_ask[1].g_p[1].u_a.g_regs.r[1][3]$_DFF_P_', 'DFF_X1', 'DFF_X2'],
        ['place15504', 'BUF_X1', 'BUF_X2'], ['place15492', 'BUF_X1', 'BUF_X2'],
        ['place15563', 'BUF_X1', 'BUF_X2']])
    plan={'A': {'node':'node7','cores':32,'tasks':[act, merged]},
          'C': {'node':'node9','cores':1,'tasks':[task('cap-diagnostic','cap-diagnostic',1)]}}
for stream in plan.values():
    assert sum(t["cores"] for t in stream["tasks"]) <= stream["cores"]
receipt = dict(attempt=args.attempt, remote=remote, host=HOST, image=IMAGE, plan=plan,
               profile=args.profile,
               dependency=args.dependency,
               runner_commit=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=BASE, text=True).strip(),
               issue="https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/7",
               submitted_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
               scope={
                   'full':'A/B physical cases, C baseline-only view preparation; no accepted hard macro assumed',
                   'physical':'Seven physical retries with tool-default scratch; no repeated functional or baseline-view job',
                   'gemm-receipt':'Verify existing original simulation summary and hash; no new simulation',
                   'top-contract':'Checked black-box wiring and common-die proposal only; no top PNR',
                   'abc-probe':'Minimal TMPDIR completion-protocol comparison; no block acceptance',
                   'abc-probe-short':'Corrected minimal short-default TMPDIR probe with standard-cell declarations',
                   'retired-evidence':'Seal already-written failed audit bytes; retain all failures',
                   'act-audit':'Independent ACT sweep hashes and strict worst-margin budget audit',
                   'full-physical-audit':'Independent seven-case hashes and strict worst-margin budget audit',
                   'targeted-repair':'Read-only verified wave2-06 CTS checkpoints, explicit equivalent-cell drive upgrades, new route/extraction and strict gates; no source or historical output changes'}[args.profile])
ssh("test ! -e " + shlex.quote(remote) + " && mkdir -p " + shlex.quote(remote + "/runner/wave2"))
for directory, paths in ((remote + "/runner", list(BASE.glob("*.py")) + list(BASE.glob("*.sh"))),
                         (remote + "/runner/wave2", list(HERE.glob("*.py")) + list(HERE.glob("*.sh")))):
    subprocess.run(["scp", "-q", *map(str, paths), HOST + ":" + directory + "/"], check=True)
ssh("find " + shlex.quote(remote + "/runner") + " -name '*.sh' -exec bash -n '{}' ';'")
payload = json.dumps(receipt, indent=2)
ssh("printf '%s\\n' " + shlex.quote(payload) + " > " + shlex.quote(remote + "/submission.json"))
out = BASE / "results" / (args.attempt + "-submission.json")
out.write_text(payload + "\n")
for label, stream in plan.items():
    command = ["sbatch", "--parsable", "-p", "c64", "-N", "1", "-n", "1", "-c", str(stream["cores"]),
               "-w", stream["node"], "--time=0", "-J", "lyz-wave2-" + label.lower(),
               "-o", remote + "/stream-" + label + ".log", "--export",
               "ALL,LLHD_BATCH=" + remote + ",LLHD_IMAGE=" + IMAGE + ",LLHD_STREAM=" + label,
               remote + "/runner/wave2/stream.sh"]
    if args.dependency:
        command.insert(1,'--dependency='+args.dependency)
    job = ssh(" ".join(map(shlex.quote, command)))
    assert re.fullmatch(r"\d+", job)
    stream["job_id"] = int(job)
    stream["scheduler_readback"] = ssh("scontrol -o show job " + job)
    assert "TimeLimit=UNLIMITED" in stream["scheduler_readback"], "Incorrect limit; inspect this newly submitted job"
    payload = json.dumps(receipt, indent=2)
    ssh("printf '%s\\n' " + shlex.quote(payload) + " > " + shlex.quote(remote + "/submission.json"))
    out.write_text(payload + "\n")
    print(label, job, stream["node"], stream["cores"], flush=True)
dependencies=":".join(str(s["job_id"]) for s in plan.values())
audit=ssh(" ".join(map(shlex.quote,["sbatch","--parsable","-p","c64","-N","1","-n","1","-c","1",
    "--time=0","--dependency=afterany:"+dependencies,"-J","lyz-wave2-audit","-o",remote+"/audit.log",
    "--export","ALL,LLHD_BATCH="+remote,remote+"/runner/wave2/audit.sh"])))
assert re.fullmatch(r"\d+",audit)
receipt['audit_job_id']=int(audit)
receipt['audit_scheduler_readback']=ssh('scontrol -o show job '+audit)
assert 'TimeLimit=UNLIMITED' in receipt['audit_scheduler_readback']
payload=json.dumps(receipt,indent=2)
ssh("printf '%s\\n' " + shlex.quote(payload) + " > " + shlex.quote(remote + "/submission.json"))
out.write_text(payload+'\n')
print('audit',audit,'afterany:'+dependencies,flush=True)
