"""Collect the successful SystemC replay receipts without rewriting source runs."""
import csv
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time


MODELS = ("phi", "gemma", "qwen3", "qwen35", "falcon", "qwen25", "granite")
FIELDS = "JobID,JobName,State,ExitCode,Elapsed,NodeList,AllocCPUS"


def account(build, pilot, array):
    wanted = {build, pilot} | {array + "_" + str(index) for index in range(len(MODELS))}
    for _ in range(6):
        rows = subprocess.check_output(
            ["sacct", "-X", "-n", "-P", "-j", ",".join((build, pilot, array)), "-o", FIELDS],
            universal_newlines=True,
        ).splitlines()
        jobs = {row["JobID"]: row for row in csv.DictReader(rows, fieldnames=FIELDS.split(","), delimiter="|")
                if row["JobID"] in wanted}
        if set(jobs) == wanted and all(row["State"] == "COMPLETED" and row["ExitCode"] == "0:0"
                                       for row in jobs.values()):
            return jobs
        time.sleep(5)
    raise ValueError("missing successful Slurm terminal records")


def verified_run(directory):
    subprocess.run(["sha256sum", "-c", "outputs.sha256"], cwd=str(directory), check=True, stdout=sys.stderr)
    raw = (directory / "verified.json").read_bytes()
    entry = json.loads(raw)
    entry["receipt_sha256"] = hashlib.sha256(raw).hexdigest()
    entry["output_manifest_sha256"] = hashlib.sha256((directory / "outputs.sha256").read_bytes()).hexdigest()
    entry["remote_dir"] = str(directory)
    return entry


def main():
    root, build, pilot, array = sys.argv[1:]
    root = Path(root).resolve()
    jobs = account(build, pilot, array)
    for name in ("upload.sha256", "build.sha256"):
        subprocess.run(["sha256sum", "-c", name], cwd=str(root), check=True, stdout=sys.stderr)
    pilot_entry = verified_run(root / "pilot-qwen35")
    models = {model: verified_run(root / ("full-" + model)) for model in MODELS}
    frozen_sha = hashlib.sha256((root / "long-systemc-results.json").read_bytes()).hexdigest()
    for model, entry in models.items():
        if (entry["mode"] != "full" or entry["frozen_summary_sha256"] != frozen_sha
                or entry["positions"] not in (23, 24) or entry["generated"] != 12):
            raise ValueError("inconsistent replay receipt: " + model)
    if sum(entry["positions"] for entry in models.values()) != 165:
        raise ValueError("incomplete seven-model sequence")
    result = {
        "root": str(root), "build_job": jobs[build], "pilot_job": jobs[pilot], "pilot": pilot_entry,
        "array": array, "jobs": {model: jobs[array + "_" + str(index)] for index, model in enumerate(MODELS)},
        "models": models, "frozen_summary_sha256": frozen_sha,
        "source_base": "5bc9d4b58ca46101ec4c377de0fc5700ae06539a",
        "build_manifest_sha256": hashlib.sha256((root / "build.sha256").read_bytes()).hexdigest(),
        "upload_manifest_sha256": hashlib.sha256((root / "upload.sha256").read_bytes()).hexdigest(),
    }
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
