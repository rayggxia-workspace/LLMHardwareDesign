"""Submit isolated llaccel VECTOR screening/physical pilots through Slurm.

All remote writes stay below the Issue #7 experiment root. Source repositories,
historical flow outputs and installed tools are read-only inputs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import shlex
import subprocess

HERE = Path(__file__).resolve().parent
HOST = "yuzelu@10.129.166.172"
REMOTE_ROOT = "/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-7"
SOURCE = "/public/home/yuzelu/project-circuit/llm_routing_analysis/worktrees/llaccel-v1"
COMMIT = "f7db8a22791a1ce9dc13e7c90b0b9b9386169aa5"
IMAGE = "/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif"
IMAGE_SHA256 = "49eae8b526c6eec806473b13db5d98f848424f38de9fa3430e8ce8e157144f3a"


def ssh(command: str) -> str:
    return subprocess.check_output(
        ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15", HOST, command],
        text=True,
        encoding="utf-8",
    ).strip()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--attempt", required=True)
    parser.add_argument("--mode", choices=["screening", "pilot", "integration", "resume", "regression", "pdn-audit"], required=True)
    parser.add_argument("--block-attempt", help="Issue #7 attempt containing the completed VECTOR hardening")
    parser.add_argument("--depends-on", type=int, help="Slurm afterok dependency, or afterany for a resume job")
    parser.add_argument("--resume-from", help="Terminal Issue #7 VECTOR attempt whose completed ORFS stages should be copied")
    parser.add_argument("--skip-phase-lec", action="store_true", help="Independent physical resume route with LEC_CHECK=0; never a formal-equivalence claim")
    parser.add_argument("--macro-pdn", choices=["platform-default", "detailed-m10", "guarded-m10"], default="platform-default", help="Integration-only H1 view/M10 access; guarded adds pitch-bloated OBS and early PG checks")
    parser.add_argument("--partition", choices=["c64", "c96"], default="c64")
    parser.add_argument("--cpus", type=int, default=8)
    args = parser.parse_args()
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", args.attempt):
        parser.error("attempt must be a simple lowercase identifier")
    if not 1 <= args.cpus <= 16:
        parser.error("this pilot permits 1-16 CPUs")
    if args.mode in ("integration", "pdn-audit") and not args.block_attempt:
        parser.error("integration/pdn-audit requires --block-attempt")
    if args.block_attempt and not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", args.block_attempt):
        parser.error("block-attempt must be a simple lowercase identifier")
    if args.mode == "resume" and not args.resume_from:
        parser.error("resume requires --resume-from")
    if args.skip_phase_lec and args.mode != "resume":
        parser.error("--skip-phase-lec is allowed only with --mode resume")
    if args.macro_pdn != "platform-default" and args.mode != "integration":
        parser.error("a custom --macro-pdn profile is allowed only with --mode integration")
    if args.resume_from and not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", args.resume_from):
        parser.error("resume-from must be a simple lowercase identifier")
    remote = f"{REMOTE_ROOT}/{args.attempt}"
    quote = shlex.quote
    ssh(
        "set -eu\n"
        f"test \"$(git -C {quote(SOURCE)} rev-parse HEAD)\" = {COMMIT}\n"
        f"test ! -e {quote(remote)}\n"
        f"mkdir -p {quote(REMOTE_ROOT)}\n"
        f"mkdir {quote(remote)}\n"
        f"mkdir {quote(remote + '/source')}\n"
        f"git -C {quote(SOURCE)} archive --format=tar {COMMIT} | "
        f"tar -xf - -C {quote(remote + '/source')}\n"
    )
    files = [
        "job.sh", "inside_screening.sh", "inside_pilot.sh", "prepare_vec.py",
        "inside_integration.sh", "prepare_top.py", "inspect_top.tcl", "validate_ports.py", "report_top_timing.tcl",
        "validate_physical_interfaces.py",
        "inside_resume.sh",
        "validate_resume.py",
        "inside_regression.sh",
        "export_macro_view.tcl", "validate_macro_view.py", "pdn_vec_m10.tcl",
        "inside_pdn-audit.sh", "audit_pdn.tcl",
        "check_pdn_connectivity.tcl", "post_pdn_check.tcl",
        "collect_attempt_outputs.sh",
    ]
    subprocess.run(
        ["scp", "-q", *[str(HERE / name) for name in files], HOST + ":" + remote + "/"],
        check=True,
    )
    condition = "afterany" if args.mode == "resume" else "afterok"
    dependency = f"--dependency={condition}:{args.depends_on} --kill-on-invalid-dep=yes " if args.depends_on else ""
    block = f"{REMOTE_ROOT}/{args.block_attempt}" if args.block_attempt else ""
    resume = f"{REMOTE_ROOT}/{args.resume_from}" if args.resume_from else ""
    command = (
        f"sbatch --parsable --partition={args.partition} --cpus-per-task={args.cpus} "
        f"--time=0 --job-name=yzl-vec-{args.mode} "
        + dependency +
        f"--output={quote(remote + '/slurm-%j.log')} "
        f"--export=ALL,LLHD_ATTEMPT={remote},LLHD_MODE={args.mode},LLHD_IMAGE={IMAGE},LLHD_IMAGE_SHA256={IMAGE_SHA256},LLHD_BLOCK={block},LLHD_RESUME_FROM={resume},LLHD_SKIP_PHASE_LEC={int(args.skip_phase_lec)},LLHD_MACRO_PDN={args.macro_pdn} "
        f"{quote(remote + '/job.sh')}"
    )
    job = ssh(command)
    job_number = job.split(";", 1)[0]
    if not job_number.isdigit():
        raise RuntimeError(f"Unexpected Slurm job receipt: {job!r}")
    receipt = {
        "job_id": job,
        "attempt": remote,
        "mode": args.mode,
        "partition": args.partition,
        "cpus": args.cpus,
        "requested_time_limit": "UNLIMITED (--time=0)",
        "effective_time_limit": None,
        "scheduler_job_snapshot": None,
        "launcher_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "source_commit": COMMIT,
        "image": IMAGE,
        "expected_image_sha256": IMAGE_SHA256,
        "host": HOST,
        "block_attempt": block or None,
        "depends_on": args.depends_on,
        "resume_from": resume or None,
        "skip_phase_lec": args.skip_phase_lec,
        "macro_pdn": args.macro_pdn,
        "verification_scope": "Physical flow, abstract and interface checks only; phase LEC deliberately disabled in this independent attempt" if args.skip_phase_lec else "Configured checks only; no original RTL-to-physical equivalence or system signoff claim",
    }
    # Preserve the known job identity even if the scheduler readback fails.
    ssh(f"printf '%s\\n' {quote(json.dumps(receipt, indent=2))} > {quote(remote + '/submission.json')}")
    scheduler = ssh(f"scontrol -o show job {job_number}")
    effective_limit = re.search(r"(?:^| )TimeLimit=(\S+)", scheduler)
    receipt.update(
        effective_time_limit=effective_limit.group(1) if effective_limit else None,
        scheduler_job_snapshot=scheduler,
    )
    print(json.dumps(receipt, ensure_ascii=False, indent=2))
    ssh(f"printf '%s\\n' {quote(json.dumps(receipt, indent=2))} > {quote(remote + '/submission.json')}")
    if receipt["effective_time_limit"] != "UNLIMITED":
        ssh(f"scancel {job_number}")
        raise RuntimeError("Slurm did not grant UNLIMITED; cancelled the new job, preserving its receipt")


if __name__ == "__main__":
    main()
