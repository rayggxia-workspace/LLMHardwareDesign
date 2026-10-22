"""Read a bounded evidence ZIP without extracting it; independently replay events."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile
from run import audit_events, closed_form


def verify(archive, expected_sha):
    archive=Path(archive)
    if hashlib.sha256(archive.read_bytes()).hexdigest()!=expected_sha:
        raise ValueError("archive SHA mismatch")
    with zipfile.ZipFile(archive) as z:
        names=z.namelist()
        expected={"manifest.json","rows.json","capacity.json","pareto.json","events.jsonl","summary.json","numerical.json"}
        if len(names)!=len(expected) or set(names)!=expected:
            raise ValueError("archive member set mismatch")
        if sum(x.file_size for x in z.infolist())>64*1024*1024:
            raise ValueError("archive exceeds declared evidence size")
        content={n:z.read(n) for n in names}
    manifest=json.loads(content["manifest.json"])
    for name,digest in manifest["artifacts"].items():
        if hashlib.sha256(content[name]).hexdigest()!=digest: raise ValueError("member SHA mismatch")
    if set(manifest["artifacts"])!=expected-{"manifest.json"}: raise ValueError("artifact index mismatch")
    rows=json.loads(content["rows.json"])
    keys=("external_read","external_write","matrix_read","matrix_write","vector_read","vector_write",
          "matrix_to_vector","vector_to_matrix","macs","engine_transfer_bytes","external_bytes","sram_access_bytes")
    seen=set()
    for line in content["events.jsonl"].splitlines():
        entry=json.loads(line);i=entry["case_id"]
        if i in seen or not 0<=i<len(rows) or rows[i]["case_id"]!=i: raise ValueError("invalid case ID")
        seen.add(i);r=rows[i]
        reconstructed=dict(counts={k:r[k] for k in keys},
                           peak_bank_bytes=dict(matrix=r["matrix_peak"],vector=r["vector_peak"]),
                           peak_total_bytes=r["peak_total"],max_copy_burst_bytes=r["max_copy_burst"])
        audit_events(entry["events"],reconstructed)
        closed_form(r,reconstructed,4)
    summary=json.loads(content["summary.json"])
    if len(seen)!=len(rows) or len(rows)!=summary["schedule_cases"]: raise ValueError("missing cases")
    numerical=json.loads(content["numerical.json"])
    if numerical["status"]!="PASS" or not all(n["detected"] for n in numerical["negative_controls"]):
        raise ValueError("numeric check failed")
    return dict(status="PASS",members=len(names),event_replays=len(seen),
                source_commit=manifest["source_commit"],archive_sha256=expected_sha,
                scope="archive integrity and schedule ledger, not hardware or model quality")


if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("archive");p.add_argument("--sha256",required=True)
    args=p.parse_args();print(json.dumps(verify(args.archive,args.sha256),indent=2))
