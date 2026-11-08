"""Collect reproducible proof for the R7.1 synthesis and timing run."""
import collections
import hashlib
import json
import pathlib
import re
import subprocess
import sys
import tarfile

run = pathlib.Path(sys.argv[1]).resolve()
previous = run.parent / "r001"


def sha(file):
    h = hashlib.sha256()
    with file.open("rb") as f:
        for data in iter(lambda: f.read(1024 * 1024), b""):
            h.update(data)
    return h.hexdigest()


def source(directory):
    manifest = json.loads((directory / "source.json").read_bytes())
    assert all(sha(directory / "source" / name) == digest for name, digest in manifest["files"].items())
    assert sha(directory / ("source-" + manifest["run"] + ".tar")) == manifest["archive_sha256"]
    return manifest


def accounting(directory):
    job = (directory / "job-id.txt").read_text().strip()
    result = subprocess.check_output(["sacct", "-j", job, "--format=JobID,State,ExitCode,Elapsed,NodeList",
                                      "--noheader", "--parsable2"]).decode("utf-8")
    rows = [line.split("|") for line in result.splitlines()]
    state = next(row for row in rows if row[0] == job)
    return dict(job=job, state=state[1], exit_code=state[2], elapsed=state[3], node=state[4], sacct=result)


def critical_nets(report, root):
    result = {}
    for row in report["modules"]:
        if "setup_slack_ns" not in row["timing"]:
            continue
        directory = root / row["name"]
        path = (directory / "timing.log").read_text(encoding="utf-8")
        delays = []
        for m in re.finditer(r"(?m)^\s*([+-]?[0-9.]+)\s+[+-]?[0-9.]+\s+[\^v]\s+(\w+)/(\w+)\s+\((\w+)\)", path):
            delay, cell, pin, kind = m.groups()
            delays.append((float(delay), cell, pin, kind))
        delay, cell, pin, kind = max(delays)
        verilog = (directory / "mapped.v").read_text(encoding="utf-8")
        connections = re.compile(r"\.(\w+)\(([^()]+)\)")
        pins = {}
        for m in re.finditer(r"(?ms)^  (\w+) (\w+) \(\n(.*?)^  \);", verilog):
            pins[m[2]] = dict(connections.findall(m[3]))
        pin_net = pins[cell][pin]
        multiplicity = collections.Counter(net for inst in pins.values() for net in inst.values())
        start = row["timing"]["startpoint"].split()[0]
        end = row["timing"]["endpoint"].split()[0]
        result[row["name"]] = dict(max_cell_arc_delay_ns=delay, arc_cell=cell, arc_pin=pin, cell_type=kind,
                                   arc_net=pin_net, other_cell_pin_connections=multiplicity[pin_net] - 1,
                                   start_q_net=pins[start].get("Q"), endpoint_q_net=pins[end].get("Q"))
    return result


success = accounting(run)
failure = accounting(previous)
assert success["state"] == "COMPLETED" and success["exit_code"] == "0:0"
assert failure["state"] == "FAILED" and failure["exit_code"] == "1:0"
main_log = run / ("slurm-" + success["job"] + ".log")
first_log = previous / ("slurm-" + failure["job"] + ".log")
assert "ORD-2010" in first_log.read_text(encoding="utf-8")
results = run / "results/synthesis"
raw = results / "synthesis-report.json"
report = json.loads(raw.read_bytes())
assert len(report["modules"]) == 9
assert sum("setup_slack_ns" in row["timing"] for row in report["modules"]) == 7
for row in report["modules"]:
    assert sha(run / "source" / row["source"]) == row["source_sha256"]
    for name, expected in row["artifacts_sha256"].items():
        assert sha(results / row["name"] / name) == expected
outputs = {p.relative_to(run).as_posix(): sha(p) for p in sorted(results.rglob("*")) if p.is_file()}
outputs[main_log.name] = sha(main_log)
index = dict(
    schema="control-r7-synthesis-evidence/0.1", server="yuzelu@10.129.166.172", directory=run.as_posix(),
    source=source(run), slurm=dict(success, partition="debug", cores=4, name="mdt-r7179",
                                 command=f"cd {run} && sbatch --parsable job-{run.name}.sh"),
    failed_attempt=dict(failure, directory=previous.as_posix(), source=source(previous),
                        reason="OpenROAD link_design requires technology LEF (ORD-2010)",
                        log_sha256=sha(first_log),
                        mother_yosys_log_sha256=sha(previous / "results/synthesis/mother/yosys.log"),
                        timing_log_sha256=sha(previous / "results/synthesis/mother/timing.log")),
    container=dict(path="/public/home/yuzelu/opt/eda/containers/orfs-26Q1.sif",
                   complete_image_sha256="not measured", singularity="4.3.4", python="3.10.12"),
    file_sha256=outputs, critical_net_observations=critical_nets(report, results),
)
metadata = run / "evidence-index.json"
metadata.write_text(json.dumps(index, indent=2) + "\n", encoding="utf-8")
archive = run / "evidence.tar.gz"
with tarfile.open(archive, "w:gz") as t:
    for path in [metadata, raw, main_log, *sorted(results.glob("*/timing.log"))]:
        t.add(path, arcname=path.relative_to(run), recursive=False)
    t.add(first_log, arcname="failed/" + first_log.name, recursive=False)
print(json.dumps(dict(index_sha256=sha(metadata), report_sha256=sha(raw), archive_sha256=sha(archive),
                      hashed_outputs=len(outputs), critical=index["critical_net_observations"])))
