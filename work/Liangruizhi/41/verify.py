"""Delivery/provenance and independent known-value sanity checks, not a model test."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument("--replay",type=Path);p.add_argument("--output",type=Path);args=p.parse_args()
digest=lambda raw:hashlib.sha256(raw).hexdigest()
raw=(HERE/"analysis.json").read_bytes();a=json.loads(raw)
assert a["provenance"]["source_bound"]
commit=a["provenance"]["commit"]
sources=0
for name,record in a["provenance"]["files"].items():
    blob=subprocess.check_output(["git","show",f"{commit}:{name}"],cwd=ROOT)
    assert digest(blob)==record["sha256"] and blob==(ROOT/name).read_bytes()
    sources+=1
# Independent values derived by hand from the declared tile/packet conventions.
known=[(a["inventory"]["all_declared_memory_bytes"],475136),
       (a["inventory"]["endpoint_fifo_count"],30),
       (a["inventory"]["signed8_multiplier_units"],281),
       (a["attention"]["score_plus_O_bytes"],40960),
       (a["attention"]["score_write_two_reads_bytes"],98304),
       (a["recurrence"]["qwen35_canonical_state_i32_bytes"],50331648),
       (a["matmul_lower_bounds"]["RQ_service_cycles_lower_bound"]["1"],7168),
       (a["wire_examples"][0]["raw_i32_bytes"],a["wire_examples"][0]["rq_i8_bytes"])]
assert all(got==expected for got,expected in known)
assert a["attention"]["score_plus_O_bytes"]>a["attention"]["private_A_bytes"]
assert a["recurrence"]["qwen35_canonical_state_i32_bytes"]>a["recurrence"]["R_plus_all_S_bytes_upper_bound"]
cfg=json.loads((ROOT/"project/experiments/block_candidate/candidate.json").read_text())
covered=set().union(*(set(cfg["decision_experiments"][e]) for e in ("E1","E2","E3","E4")))
assert covered==set(cfg["decision_names"])
links=0
for name in ("BLOCK_CANDIDATE_V1.md","BLOCK_MINIMAL_EXPERIMENTS_V1.md"):
    doc=ROOT/"docs"/name
    for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)",doc.read_text(encoding="utf-8")):
        if "://" in target or target.startswith("#"):continue
        assert (doc.parent/target.split("#")[0]).exists(),target
        links+=1
files=0
if (HERE/"manifest.json").exists():
    for name,record in json.loads((HERE/"manifest.json").read_text())["files"].items():
        data=(ROOT/name).read_bytes()
        assert len(data)==record["bytes"] and digest(data)==record["sha256"],name
        files+=1
if args.replay:assert args.replay.read_bytes()==raw
report={"status":"PASS","scope":"analytical contract/delivery checks only; E1-E5 not executed",
        "analysis_source_commit":commit,"source_bindings":sources,"known_value_checks":len(known),
        "capacity_counterexamples":2,"decision_coverage":sorted(covered),"new_document_relative_links":links,
        "delivery_file_hashes":files,"analysis_sha256":digest(raw),
        "byte_identical_second_analysis":True if args.replay else "not requested"}
if args.output:
    if args.output.exists():raise ValueError("refuse overwrite")
    args.output.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8",newline="\n")
print(json.dumps(report))
