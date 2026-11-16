"""Join final ODB/VCD provenance and matched-duty E32 energy evidence."""
import argparse
import base64
import hashlib
import io
import json
from pathlib import Path
import re
import tarfile


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def audit(path):
    remote = (path / "remote-evidence.txt").read_text()
    assert re.search(r"^102629\|COMPLETED\|0:0\|[\d:]+\|96$", remote, re.M)
    files = {}
    for digest, name in re.findall(r"^([0-9a-f]{64}) +(.+)$", remote, re.M):
        # The second source manifest belongs to the earlier waveform job.
        assert name not in files or name == "source.sha256"
        files.setdefault(name, digest)
    archive = base64.b64decode((path / "raw.tar.gz.b64").read_bytes(), validate=True)
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as package:
        raw = {member.name: package.extractfile(member).read() for member in package.getmembers()}
    modes = ("active", "idle", "active-clock-only")
    logs_and_scripts = [f"{mode}-pins.{ext}" for mode in modes for ext in ("tcl", "log")]
    for name in ("allocation.txt", "input.sha256", "source.sha256", "slurm-102629.log", *logs_and_scripts):
        assert sha(raw[name]) == files[name], name
    for line in raw["source.sha256"].decode().splitlines():
        digest, name = line.split("  ", 1)
        assert sha(raw["source/" + name]) == digest
    assert sha(raw["trace-102602.json"]) == files["energy/energy.json"]
    trace = json.loads(raw["trace-102602.json"])
    for mode, row in zip(("active", "idle"), trace["cases"], strict=True):
        assert row["vcd_sha256"] == files[f"energy/{mode}-tt300.vcd"]
    for name, digest in trace["postroute_inputs"].items():
        original, = [file for file in files if file.endswith("/" + name)]
        assert files[original] == digest

    reports = {}
    for mode in modes:
        report = raw[f"{mode}-pins.log"].decode()
        match = re.search(r"^E_GATE_PIN_ACTIVITY matched=(\d+) trace_only=(\d+) active_clock=(\d+) clocks_only=(\d+)$",
                          report, re.M)
        gate, others, clocks, clock_only = map(int, match.groups())
        assert (gate, others, clocks, clock_only) == (89389, 57467, 1921, int(mode == "active-clock-only"))
        assert re.search(r"^unannotated\s+0$", report, re.M)
        assert re.search(r"^vcd\s+158$", report, re.M)
        totals = re.search(r"^Total\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)", report, re.M)
        internal, switching, leakage, total = map(float, totals.groups())
        assert abs(internal + switching + leakage - total) < max(1e-12, total * 1e-6)
        reports[mode] = dict(internal_W=internal, switching_W=switching, leakage_W=leakage, total_W=total,
                             gate_pins=gate, port_bits=158, unannotated=0, traced_clocks=clocks)
    active, reference = reports["active"], reports["active-clock-only"]
    assert active["leakage_W"] == reference["leakage_W"]
    delta = active["total_W"] - reference["total_W"]
    assert delta > 0
    duration = trace["cases"][0]["seconds"]
    operations = trace["cases"][0]["operations"]
    return dict(job=102629, trace_job=102602, period_ps=3333, full_gate_pin_activity=True,
                clock_and_duty_reference=True, temperature_C=25, voltage_V=1.1,
                actual_active_duration_seconds=duration, mixed_services=operations, reports=reports,
                incremental_observed_nonclock_J_per_service=delta * duration / operations,
                absolute_active_J_per_observed_service=active["total_W"] * duration / operations,
                whole_model_energy_qualified=False, source_manifest_sha256=sha(raw["source.sha256"]),
                trace_source_bundle_sha256=files["source.tar.gz"],
                raw_hash_index_sha256=sha(remote.encode()))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    print(json.dumps(audit(parser.parse_args().run), indent=2))
