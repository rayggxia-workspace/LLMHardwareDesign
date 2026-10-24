"""Run the authorized local checks and preserve honest per-command receipts.

Creates a new evidence directory, never overwrites a prior run or any fixture.
This runner does not access the network or inspect ref-project/.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone, timedelta

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
BASE = "b06d85a801a87c07f9745ccae6950dc7e4cbd0d2"
DOCS = ["docs/BLOCK_V2_FIELD_MAPPING.md", "docs/ARCHITECTURE.md",
        "docs/handoffs/2026-10-24-pending-block-v2-offline-prep.md", "progress/huangpingyang04-lgtm/STATUS.md"]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, env={**os.environ, "GIT_NO_LAZY_FETCH": "1"})


def protected_files():
    # Only the user-specified estimator and new fixtures/source copies; no reference
    # packages, old experimental results, model tensors, or credentials are scanned.
    return sorted(set((ROOT / "project/analysis/llm_resources").rglob("*.py")) |
                  set((ROOT / "project/analysis/llm_resources").rglob("*.json")) |
                  set((HERE / "fixtures").glob("*.json")) |
                  set((HERE / "sources").rglob("*.md")) | {HERE / "sources/manifest.json"})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True, help="new directory only")
    args = parser.parse_args()
    out = args.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=False)
    before = {str(p.relative_to(ROOT)).replace("\\", "/"): sha(p) for p in protected_files()}
    commands = []

    def run(label, argv, expected_exit=0, expected_tests=None):
        result = subprocess.run(argv, cwd=ROOT, capture_output=True, encoding="utf-8", errors="replace")
        (out / f"{label}.stdout.txt").write_text(result.stdout, encoding="utf-8", newline="\n")
        (out / f"{label}.stderr.txt").write_text(result.stderr, encoding="utf-8", newline="\n")
        match = re.search(r"Ran (\d+) tests?", result.stdout + result.stderr)
        entry = {"label": label, "argv": list(map(str, argv)), "exit_code": result.returncode,
                 "expected_exit_code": expected_exit, "passed": result.returncode == expected_exit,
                 "test_count": int(match[1]) if match else None,
                 "expected_test_count": expected_tests,
                 "stdout_sha256": sha(out / f"{label}.stdout.txt"),
                 "stderr_sha256": sha(out / f"{label}.stderr.txt")}
        if expected_tests is not None:
            entry["passed"] = entry["passed"] and entry["test_count"] == expected_tests
        commands.append(entry)
        print(f"{label}: exit={result.returncode}, expected={expected_exit}, tests={entry['test_count']}", flush=True)
        return result

    py = sys.executable
    # Required order: management -> new business -> original estimator regression.
    run("01-management", [py, "-B", "scripts/check_project.py"])
    run("02-offline-tests", [py, "-B", "-m", "unittest", "discover", "-s", "project/analysis/block_v2_offline", "-v"], expected_tests=32)
    run("03-estimator-regression", [py, "-B", "-m", "unittest", "discover", "-s", "project/analysis/llm_resources", "-v"], expected_tests=31)
    deterministic = {}
    for index, name in enumerate(["graph1_reduce_rq", "graph2_state_commit"], 4):
        argv = [py, "-B", str(HERE / "replay.py"), str(HERE / f"fixtures/{name}.input.json"),
                "--expected", str(HERE / f"fixtures/{name}.expected.json")]
        first = run(f"0{index}a-{name}", argv)
        second = run(f"0{index}b-{name}", argv)
        deterministic[name] = first.returncode == second.returncode == 0 and first.stdout == second.stdout
    # Explicit CLI receipts with readable errors and nonzero exits, using temp copies.
    source = json.loads((HERE / "fixtures/graph1_reduce_rq.input.json").read_text(encoding="utf-8"))
    expected = json.loads((HERE / "fixtures/graph1_reduce_rq.expected.json").read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory() as tmp:
        bad_input, bad_expected = Path(tmp) / "bad-input.json", Path(tmp) / "bad-expected.json"
        source["data"]["groups"].pop()
        bad_input.write_text(json.dumps(source), encoding="utf-8")
        expected["rq_codes"] = [-2, 4]
        bad_expected.write_text(json.dumps(expected), encoding="utf-8")
        run("06-negative-missing-group", [py, "-B", str(HERE / "replay.py"), str(bad_input),
            "--expected", str(HERE / "fixtures/graph1_reduce_rq.expected.json")], 2)
        run("07-negative-wrong-expected", [py, "-B", str(HERE / "replay.py"), str(HERE / "fixtures/graph1_reduce_rq.input.json"),
            "--expected", str(bad_expected)], 2)
    run("08-diff-check", ["git", "diff", "--check"])
    run("09-final-status", ["git", "status", "--short", "--untracked-files=all"])
    after = {str(p.relative_to(ROOT)).replace("\\", "/"): sha(p) for p in protected_files()}
    baseline_matches = {}
    for relative in before:
        if relative.startswith("project/analysis/llm_resources/"):
            baseline_matches[relative] = hashlib.sha256(git("show", f"{BASE}:{relative}")).hexdigest() == before[relative]
    source_manifest = json.loads((HERE / "sources/manifest.json").read_text(encoding="utf-8"))
    source_checks = []
    for record in source_manifest["files"]:
        matches = hashlib.sha256(git("show", f"{record['commit']}:{record['path']}")).hexdigest() == record["sha256"]
        if "local_copy" in record:
            matches = matches and sha(ROOT / record["local_copy"]) == record["sha256"]
        source_checks.append({"commit": record["commit"], "path": record["path"], "matches": matches})
    whitespace_errors = []
    delivery_files = sorted(HERE.rglob("*")) + [ROOT / path for path in DOCS]
    for path in delivery_files:
        if not path.is_file() or (path.is_relative_to(HERE) and "sources" in path.relative_to(HERE).parts):
            continue  # fixed source documents retain their original whitespace
        if path.suffix in (".md", ".py", ".json") and out not in path.parents:
            for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if line.rstrip() != line:
                    whitespace_errors.append(f"{path.relative_to(ROOT)}:{number}")
    tracked_changes = git("diff", "--name-only", "HEAD").decode("utf-8").splitlines()
    untracked = git("ls-files", "--others", "--exclude-standard").decode("utf-8").splitlines()
    changed_paths = sorted(set(tracked_changes + untracked))
    outside_scope = [p for p in changed_paths if p not in DOCS and not p.startswith("project/analysis/block_v2_offline/")]
    local_artifacts = {str(p.relative_to(ROOT)).replace("\\", "/"): sha(p) for p in delivery_files
                       if p.is_file() and not (p.is_relative_to(HERE) and "evidence" in p.relative_to(HERE).parts)}
    missing_documents = [path for path in DOCS if not (ROOT / path).is_file()]
    report = {"recorded_at": datetime.now(timezone(timedelta(hours=8))).isoformat(),
              "worktree": str(ROOT), "branch": git("branch", "--show-current").decode().strip(),
              "baseline_commit": BASE, "head_at_validation": git("rev-parse", "HEAD").decode().strip(),
              "delivery_commit": None, "delivery_source_bound": False, "status": "local offline/pending",
              "python": sys.version, "commands": commands, "deterministic_replays": deterministic,
              "protected_before": before, "protected_after": after, "protected_unchanged": before == after,
              "estimator_matches_committed_baseline": baseline_matches, "source_checks": source_checks,
              "changed_paths": changed_paths, "outside_scope": outside_scope,
              "local_artifact_sha256": local_artifacts, "missing_documents": missing_documents,
              "new_file_whitespace_errors": whitespace_errors,
              "not_executed": ["server/SSH/SCP/Slurm", "EDA/RTL/physical/PPA", "model inference/weights",
                               "GitHub Issue/PR/board mutations or push/merge", "Issue63 general adapter"],
              "online_latest_state": "unverified; see sources/manifest.json"}
    report["all_required_local_checks_passed"] = (all(c["passed"] for c in commands) and all(deterministic.values())
        and before == after and all(baseline_matches.values()) and all(c["matches"] for c in source_checks)
        and not whitespace_errors and not outside_scope and not missing_documents)
    (out / "validation.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"all_required_local_checks_passed={report['all_required_local_checks_passed']}", flush=True)
    return 0 if report["all_required_local_checks_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
