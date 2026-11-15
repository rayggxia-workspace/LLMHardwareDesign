#!/usr/bin/env python3
#SBATCH --job-name=mdt-280qwen3
#SBATCH --partition=c96
#SBATCH --nodes=1
#SBATCH --ntasks=2
#SBATCH --cpus-per-task=12
#SBATCH --time=06:00:00
#SBATCH --output=slurm-%j.log
"""Build and run an isolated Qwen3 DDR energy replay on the project cluster."""
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys


SERVER_ROOT = Path("/public/home/yuzelu")
PROJECT = SERVER_ROOT / "project-circuit"
RUNS = SERVER_ROOT / "Melodydt/runs"
FROZEN = RUNS / "issue-274/three-p-full-01"
BRIDGE = RUNS / "issue-270/ffn-weight-05/tlm"
DRAM = PROJECT / "issue234-ddr-quiet-JDehtRNz/quiet/source"
CONFIG = PROJECT / "issue234-algo1-ffn-chain-20261112-01/DDR4-single-channel.ini"
SINGULARITY = "/public/software/singularity-ce-4.3.4/bin/singularity"
IMAGE = SERVER_ROOT / "opt/eda/containers/orfs-current-repacked.sif"
AUDIT_PYTHON = SERVER_ROOT / "RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python"
COMPAT = PROJECT / "LLMHardwareDesign/issue-234-systemc-benchmark/python-compat-001"
BASE_PREFILL = "run-115618-qwen3"
BASE_DECODE = "run-115619-qwen3"
PREFILL = "prefill-w4-tile128-pr272-combined"
DECODE = "decode-live-w4-tile128-pr272-combined"


def run(*args, cwd, env=None, stdout=None):
    command = [str(arg) for arg in args]
    print("Run", " ".join(command), flush=True)
    subprocess.run(command, cwd=cwd, env=env, stdout=stdout, check=True)


def check_sha(path, expected):
    sha = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            sha.update(block)
    if sha.hexdigest() != expected:
        raise ValueError(f"frozen dependency checksum differs: {path}")


def build_probe(work, bundle, cpus, frozen, bridge, dram):
    inputs = work / "inputs"
    inputs.mkdir()
    for filename in ("qwen3_short.py", "fast_qwen3_short.sbatch"):
        shutil.copy2(frozen / filename, inputs)
    for filename in ("fast_tlm_dram.cpp", "fast_tlm_replay.py"):
        shutil.copy2(bridge / filename, inputs)
    staged = work / "staged"
    run(sys.executable, "-B", bundle / "stage_ddr_probe.py", dram, staged,
        "--replay", inputs, cwd=work)
    source = staged / "dramsim3"
    replay = staged / "replay"
    builder = container_step(cpus)
    library = work / "ddr-probe.so"
    run(*builder, "cmake", "-S", source, "-B", work / "build",
        "-DCMAKE_BUILD_TYPE=Release", cwd=work)
    run(*builder, "cmake", "--build", work / "build", "--target", "dramsim3",
        "--parallel", cpus, cwd=work)
    run(*builder, "g++", "-std=c++17", "-O3", "-Wall", "-Wextra", "-Werror", "-shared",
        "-fPIC", "-isystem", source / "src", "-isystem", source / "ext/headers",
        replay / "fast_tlm_dram.cpp", "-L", source, f"-Wl,-rpath,{source}", "-ldramsim3",
        "-o", library, cwd=work)
    return replay, source / "libdramsim3.so", library


def write_manifest(path, entries, cwd):
    with path.open("w", encoding="utf-8") as output:
        run("sha256sum", *entries, cwd=cwd, stdout=output)


def container_step(cpus):
    return ("srun", "--exact", "-N1", "-n1", "-c", cpus, SINGULARITY,
            "exec", "--cleanenv", "--bind", SERVER_ROOT, IMAGE)


def main():
    bundle = Path(os.environ["SLURM_SUBMIT_DIR"]).resolve()
    job = os.environ["SLURM_JOB_ID"]
    cpus = os.environ["SLURM_CPUS_PER_TASK"]
    # Slurm runs the job script from its spool, so the bundle comes from SLURM_SUBMIT_DIR.
    commit_file = bundle / "source-commit.txt"
    commit = commit_file.read_text(encoding="ascii").strip()
    if len(commit) != 40 or any(c not in "0123456789abcdef" for c in commit):
        raise ValueError("source-commit.txt must identify the staged source commit")
    run("sha256sum", "-c", "bundle.sha256", cwd=bundle)
    check_sha(BRIDGE / "run-113164.dram.so",
              "1e74820e1cbe48b447e29fd9f98f55c54b4bd4f3fb493b0f2d8e1317c3cd8c1b")
    check_sha(CONFIG, "748ba1a2e06c26f4a71f27a9a98060ecf00432376ad417deae1ab92afdcb0766")
    run("sha256sum", "-c", "source.sha256", cwd=BRIDGE)
    for name in ("source.sha256", "upstream.sha256", BASE_PREFILL + "/output.sha256",
                 BASE_DECODE + "/output.sha256"):
        run("sha256sum", "-c", name, cwd=FROZEN)
    work = bundle / f"pilot-{job}"
    work.mkdir()
    print(f"Qwen3 DDR pilot {job}, source {commit}, output {work}", flush=True)
    replay, dram_library, library = build_probe(work, bundle, cpus, FROZEN, BRIDGE, DRAM)
    for source in FROZEN.glob("*.py"):
        if not (replay / source.name).exists():
            shutil.copy2(source, replay)
    shutil.copy2(FROZEN / "upstream.sha256", replay)
    write_manifest(replay / "source.sha256",
                   sorted(p.name for p in replay.iterdir() if p.suffix in (".py", ".cpp", ".sbatch")),
                   replay)
    write_manifest(work / "pilot-inputs.sha256",
                   (commit_file, bundle / "bundle.sha256", FROZEN / "source.sha256",
                    FROZEN / "upstream.sha256", IMAGE, CONFIG, dram_library, library), work)
    env = dict(os.environ, SLURM_SUBMIT_DIR=str(replay), MDT_280_DDR_LIBRARY=str(library),
               MDT_274_NATIVE_MATH="1", MDT_274_THREE_P="1", MDT_274_TRACE_LAYERS="1",
               MDT_274_RUN_SUFFIX="", MDT_274_VERIFY_MATH="0", MDT_274_GEMMA_WIDE_RESIDUAL="0")
    run("bash", "fast_qwen3_short.sbatch", "qwen3", "prefill:4:tile128:combined",
        "decode-live:4:tile128:combined", cwd=replay, env=env)
    output = replay / f"run-{job}"
    run("sha256sum", "-c", output / "output.sha256", cwd=replay)
    results = []
    for mode, stage, base in (("prefill", PREFILL, BASE_PREFILL), ("decode", DECODE, BASE_DECODE)):
        result = work / f"ddr-{mode}.json"
        with result.open("w", encoding="utf-8") as stream:
            run(sys.executable, "-B", bundle / "ddr_window_energy.py", output / stage,
                "--baseline", FROZEN / base / stage, cwd=work, stdout=stream)
        results.append(result)
    audit = work / "audit-three-p.json"
    with audit.open("w", encoding="utf-8") as stream:
        run(*container_step(cpus), "env", f"LD_LIBRARY_PATH={COMPAT}",
            "OPENBLAS_NUM_THREADS=1", "OMP_NUM_THREADS=1", AUDIT_PYTHON, "-B",
            FROZEN / "audit_three_p.py",
            RUNS / "issue-274/reference-workloads-01/ref-114294/qwen3",
            FROZEN / "fp32-115617-qwen3", output / PREFILL, output / DECODE,
            cwd=work, stdout=stream)
    write_manifest(work / "pilot-results.sha256", (*results, audit, output / "output.sha256"), work)


if __name__ == "__main__":
    main()
