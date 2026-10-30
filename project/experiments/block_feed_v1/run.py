"""Reproducible Issue130 RTL tests; outputs are NOT physical qualification.

Use an installed Verilator, or pass --verilator and set VERILATOR_ROOT for a
workspace-local extracted package. Never installs tools or submits remote jobs.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
RTL = ROOT / "project/rtl/block_feed_v1"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def call(args, log, cwd=ROOT):
    with log.open("w") as stream:
        proc = subprocess.run(list(map(str, args)), cwd=cwd, stdout=stream,
                              stderr=subprocess.STDOUT, check=False)
    if proc.returncode:
        raise RuntimeError(f"exit {proc.returncode}: {args}; see {log}")


def run_one(name, args, out):
    folder = out / name
    folder.mkdir(parents=True, exist_ok=False)
    top = {"m": "block_feed_m", "s": "block_feed_s16k", "pair": "block_feed_pair"}.get(name)
    legacy = name in ("v", "r", "t")
    if legacy:
        top = {"v": "block_v1_v", "r": "block_v1_r", "t": "transaction6k"}[name]
        sources = [ROOT / "project/rtl/block_library_v1" / (top + ".sv")]
        if name == "v":
            sources += [ROOT / "project/rtl/block_library_v1" / (n + ".sv")
                        for n in ("block_v1_v_group", "block_v1_v_function")]
        if name == "t":
            sources = [ROOT / "project/rtl/block_v1/transaction6k.sv"]
        cpp = ROOT / "project/experiments/block_v1" / {
            "v": "test_vector_macro.cpp", "r": "test_recurrent_macro.cpp", "t": "test_transaction.cpp"}[name]
    else:
        sources = [RTL / (top + ".sv")] if name != "pair" else sorted(RTL.glob("*.sv"))
        if name == "pair":
            sources += [ROOT / "project/rtl/block_v1/transaction6k.sv"]
        cpp = HERE / ("test_" + name + ".cpp")
        if name == "pair":
            call([args.verilator, "--lint-only", "-Wall", "--top-module", "block_feed_s_macro",
                  *(s for s in sources if s.parent == RTL and s.stem != "block_feed_pair")], folder / "strict-candidate-lint.log")
            call([args.verilator, "--lint-only", "-Wall", "-Wno-fatal", "--top-module", top, *sources], folder / "lint.log")
            for line in (folder / "lint.log").read_text().splitlines():
                if "%Warning" in line and not ("%Warning-WIDTH" in line and "transaction6k.sv:" in line):
                    raise RuntimeError(f"new integration lint warning: {line}")
        else:
            call([args.verilator, "--lint-only", "-Wall", "--top-module", top, *sources], folder / "lint.log")
    original_cpp = cpp
    adaptation = None
    if name in ("v", "r"):
        # Baseline fixtures construct their global DUT before commandArgs, so
        # +rand+reset would not affect its initial state. Adapt ONLY a generated
        # copy; preserve the baseline source and record both exact byte hashes.
        text = cpp.read_text()
        declaration = f"static V{top} dut;"
        entry = "Verilated::commandArgs(argc,argv);"
        if text.count(declaration) != 1 or text.count(entry) != 1:
            raise RuntimeError("baseline fixture changed: inspect constructor adaptation")
        text = text.replace(declaration, f"static V{top}* dut_ptr;\n#define dut (*dut_ptr)\n")
        text = text.replace(entry, entry + f"dut_ptr=new V{top};")
        cpp = folder / "adapted-fixture.cpp"
        cpp.write_text(text)
        adaptation = dict(reason="Construct DUT after commandArgs for actual randomized initial states",
                          original=str(original_cpp.relative_to(ROOT)), original_sha256=sha(original_cpp),
                          generated_sha256=sha(cpp), declaration_before=declaration,
                          declaration_after=f"static V{top}* dut_ptr;\n#define dut (*dut_ptr)\n",
                          entry_before=entry, entry_after=entry + f"dut_ptr=new V{top};")
        (folder / "fixture-adaptation.json").write_text(json.dumps(adaptation, indent=2) + "\n")
    command = [args.verilator, "--cc", "--exe", "--build", "-j", str(args.build_jobs),
               "--top-module", top, "--Mdir", folder / "obj", "--x-initial", "unique",
               "--x-assign", "unique", "--output-split", "20000", "--output-split-cfuncs", "200",
               "-CFLAGS", "-std=c++17 -O1", "-I" + str(ROOT / "project/rtl/block_library_v1"), *sources, cpp]
    if legacy or name == "pair":
        command.insert(1, "-Wno-fatal")  # Existing baseline warnings, saved in build.log.
    call(command, folder / "build.log")
    runs = []
    for mode, seed in [(1, 130), (2, 130), (2, 131)]:
        log = folder / f"result-{mode}-{seed}.json"
        invocation = [folder / "obj" / ("V" + top), f"+verilator+rand+reset+{mode}",
                      f"+verilator+seed+{seed}"]
        call(invocation, log)
        result = json.loads(log.read_text())
        if not result.get("passed"):
            raise RuntimeError(f"non-passing result: {log}")
        runs.append(dict(initial_mode=mode, seed=seed, result=result, result_sha256=sha(log)))
    inputs = [*sources, original_cpp, Path(__file__).resolve()]
    if name == "v":
        inputs.append(ROOT / "project/rtl/block_library_v1/block_v1_v_tables.svh")
    receipt = dict(passed=True, model=name, top=top, command=list(map(str, command)),
                   source_sha256={str(p.relative_to(ROOT)): sha(p) for p in inputs},
                   runs=runs, fixture_adaptation=adaptation, physical_qualified=False)
    (folder / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verilator", default="verilator")
    parser.add_argument("--out", type=Path, required=True, help="Fresh output directory")
    parser.add_argument("--models", nargs="+", choices=["m", "s", "pair", "v", "r", "t"], default=["m", "s", "pair", "v", "r", "t"])
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--build-jobs", type=int, default=4)
    parser.add_argument("--source-commit", help="Verified checkout HEAD when Linux cannot read Windows worktree metadata")
    args = parser.parse_args()
    if args.workers < 1 or args.build_jobs < 1 or args.workers * args.build_jobs > len(os.sched_getaffinity(0)):
        parser.error("workers*build-jobs must fit allocated CPU affinity")
    args.out = args.out.resolve()
    args.out.mkdir(parents=True, exist_ok=False)
    version = subprocess.check_output([args.verilator, "--version"], text=True).strip()
    git = args.source_commit or subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    if len(git) != 40 or any(c not in "0123456789abcdef" for c in git):
        parser.error("source commit must be an exact40-character lowercase SHA")
    results, errors = [], []
    start = time.time()
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        pending = {pool.submit(run_one, name, args, args.out): name for name in args.models}
        for future in as_completed(pending):
            name = pending[future]
            try:
                receipt = future.result(); results.append(receipt)
                print(f"PASS {name}", flush=True)
            except Exception as exc:
                errors.append(dict(model=name, error=str(exc))); print(f"FAIL {name}: {exc}", flush=True)
    result = dict(passed=not errors, source_commit=git, working_tree_source_hashes_in_receipts=True,
                  verilator=version, elapsed_seconds=time.time()-start,
                  cpu_affinity=sorted(os.sched_getaffinity(0)), workers=args.workers,
                  build_jobs=args.build_jobs, results=results, errors=errors, physical_qualified=False)
    compiler = Path(args.verilator).resolve()
    result["tool_sha256"] = {str(p): sha(p) for p in (compiler, compiler.parent / "verilator_bin") if p.is_file()}
    (args.out / "summary.json").write_text(json.dumps(result, indent=2) + "\n")
    return bool(errors)


if __name__ == "__main__":
    raise SystemExit(main())
