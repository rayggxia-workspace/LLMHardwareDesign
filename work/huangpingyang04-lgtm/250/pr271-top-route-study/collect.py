"""Collect compact review evidence from a completed server comparison."""

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import subprocess


VARIANTS = ("top-1834", "top-1184-no-u0-dma")


def read(path):
    return json.loads(path.read_text())


def checksum(path):
    with path.open("rb") as stream:
        return sha256_file(stream)


def sha256_file(stream):
    digest = sha256()
    for chunk in iter(lambda: stream.read(1024*1024), b""):
        digest.update(chunk)
    return digest.hexdigest()


def stats(document):
    rows = {}
    for key in ("direct", "repair"):
        step = document[key]
        rows[key] = {
            "logic_routed": step.get("logical_nets_checked", step["nets_checked"]),
            "physical_routed": step["nets_checked"],
            "length_um": step["wire_length_dbu"]/2000,
            "via10": step["via10_count"],
            "via11": step["via11_count"],
            "families": step["families"],
            "load_violations": sum(row["overload_nets"] for row in step["families"].values()),
            "failures": dict(sum((Counter(row["failed"]) for row in step["families"].values()), Counter())),
        }
    return {**rows, **{key: document[key] for key in
                      ("method", "tried", "trials_with_relay", "geometric_recoveries")}}


def collect(root, output):
    run_numbers = "114252,114370,114371,114386,114387,114388,114389,114399,114400,114411,114412,114422,114423,114424,114425,114439,114440,114451,114452,114457,114458,114490,114493,114498,114499,114536,114537"
    jobs = subprocess.check_output(
        ["sacct", "-j", run_numbers, "-X", "-P", "-n", "-o", "JobID,State,ExitCode,Elapsed"], universal_newlines=True)
    data = {"server_job_dir": str(root), "jobs": [row.split("|") for row in jobs.splitlines()],
            "variants": {}, "sha256": {}}
    selected = []
    for variant in VARIANTS:
        directory = root/variant
        result = {}
        for name, file in (("study", "study"), ("weighted", "weighted"),
                           ("reserve", "reserve"), ("jumps", "jumps"),
                           ("near", "fast/results"), ("full_repair", "full-repair")):
            folder = directory/file
            if (folder/"summary.json").is_file():
                result[name] = stats(read(folder/"summary.json"))
                selected += [folder/f for f in
                             ("direct.json", "repair.json", "inventory.json", "trials.json", "summary.json")]
        if (directory/"direct.json").is_file():
            selected.append(directory/"direct.json")
            baseline = read(directory/"direct.json")
            result["unmodified_direct"] = {
                "geometry": baseline["geometry_check"],
                "routed": len(baseline["routes"]),
                "failed": dict(Counter(baseline["failed"].values())),
                "attempts": [{key: step[key] for key in ("round", "routed", "expanded")}
                             for step in baseline["attempts"]],
            }
        result["timing"] = {}
        for path in sorted(directory.glob("*-timing-*/timing-summary.json")):
            result["timing"][path.parent.name] = read(path)
            selected += [path, *path.parent.glob("net-*/sta.log")]
        for path in sorted(directory.glob("*-ablation-*/summary.json")):
            result["no_buffer_control"] = read(path)
            selected += [path, path.parent/"routes.json"]
        near_control = directory/"near-ablation/summary.json"
        if near_control.is_file():
            result["no_buffer_near"] = read(near_control)
            selected += [near_control, near_control.parent/"routes.json"]
        diagnostic = directory/"weighted/diagnosis.json"
        if diagnostic.is_file():
            result["diagnosis"] = read(diagnostic)
            selected.append(diagnostic)
        data["variants"][variant] = result
        selected += [root/"inputs"/variant/file for file in ("algorithm2-input.json", "nets.tsv", "handoff.json")]
    selected += [root/file for file in ("router-source.tar", "cells.lib", "inputs/placement.json", "inputs/upper-rules.json")]
    selected += [path for path in (root/"analysis").iterdir() if path.is_file()]
    data["sha256"] = {str(path.relative_to(root)): checksum(path) for path in sorted(set(selected))}
    with output.open("x", encoding="utf-8") as stream:
        json.dump(data, stream, indent=2)
        stream.write("\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    collect(args.root.resolve(), args.output)
