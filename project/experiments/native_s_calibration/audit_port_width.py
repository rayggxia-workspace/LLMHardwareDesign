"""Audit the historical same-work NoPool SystemC port-width sensitivity."""

import argparse
import base64
import hashlib
import io
import json
from pathlib import Path
import tarfile


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def audit(run):
    recovery = json.loads((run / "recovery.json").read_bytes())
    raw = base64.b64decode(b"".join((run / "receipts.tar.gz.b64").read_bytes().split()), validate=True)
    assert sha256(raw) == recovery["receipts_archive_sha256"]
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:gz") as archive:
        members = {member.name: archive.extractfile(member).read()
                   for member in archive if member.isfile()}
    assert {name: sha256(data) for name, data in members.items()} == recovery["members"]
    plans = {"legacy-NoPool": 0, "P128-NoPool": 1, "all128-NoPool": 2}
    work_keys = ("tokens", "logical_read_bytes", "logical_write_bytes",
                 "read_bus_bytes", "write_bus_bytes", "M_commands")
    rows = {}
    for plan, scope in plans.items():
        report = json.loads(members[f"{plan}/report.json"])
        assert report["passed"] and report["plan"] == plan and report["job"] == recovery["job"]
        env = dict(report["source_env"])
        assert env.pop("NS_PORT_SCOPE") == str(scope)
        assert env["SQ_BEAT"] == "64" and env["SQ_BW_MB"] == "51200"
        assert env["SX_LOCAL_WIDTH"] == "16" and env["NS_WORD_CYCLES"] == "1"
        assert env["NS_RESPONSE_CYCLES"] == "0"
        results = [json.loads(line[7:])
                   for line in members[f"{plan}/decode512.log"].decode().splitlines()
                   if line.startswith("RESULT ")]
        assert len(results) == 1
        result = results[0]
        assert result == next(item["result"] for item in report["results"] if item["label"] == "decode512")
        # The byte field is the configured base width. The cycle field is
        # the actual model cost to move those 64 bytes through P.S.
        hardware = result["hardware_study"]
        assert hardware["S_port_bytes"] == hardware["DDR_beat_bytes"] == 64
        assert hardware["S_port_cycles"] == (4 if scope else 1)
        assert hardware["aggregate_bandwidth_B_s"] == 51_200_000_000
        trace = report["input_trace_SHA256"]
        work = {key: result[key] for key in work_keys}
        if scope == 0:
            matched = (env, trace, work)
        else:
            assert (env, trace, work) == matched
        rows[plan] = {
            "ordinary_S_bytes_per_service_model_P_U": [16 if scope else 64, 16 if scope == 2 else 64],
            "cycles": result["ticks"],
            "token_per_second": result["tokens_per_second"],
            "spans_cycles": result["spans_ticks"],
        }

    wide = rows["legacy-NoPool"]
    narrow = rows["all128-NoPool"]
    return {
        "job": recovery["job"],
        "source_commit": recovery["source_commit"],
        "archive_sha256": recovery["receipts_archive_sha256"],
        "trace_sha256": trace,
        "changed_environment_keys": ["NS_PORT_SCOPE"],
        "matched_work": work,
        "modeled_DDR_beat_B": 64,
        "modeled_DDR_total_GB_per_s": 51.2,
        "explicit_A_and_COPY_configuration_unchanged": True,
        "rows": rows,
        "P_only_added_cycles": rows["P128-NoPool"]["cycles"] - wide["cycles"],
        "P_and_U_added_cycles": narrow["cycles"] - wide["cycles"],
        "P_and_U_added_Dot_span_cycles": narrow["spans_cycles"]["Dot"] - wide["spans_cycles"]["Dot"],
        "P_and_U_throughput_loss_fraction": 1 - narrow["token_per_second"] / wide["token_per_second"],
        "scope": "Historical SystemC sensitivity only. No wide product RTL, bandwidth or routed timing proof.",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    print(json.dumps(audit(parser.parse_args().run), indent=2))
