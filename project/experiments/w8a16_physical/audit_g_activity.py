"""Verify exact G32 activity source and price only the covered FFN packets."""
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


def audit(run):
    remote = (run / "remote-evidence.txt").read_text(encoding="utf-8")
    assert re.search(r"^102639\|COMPLETED\|0:0\|[\d:]+\|96$",remote,re.M)
    hashes = {path:digest for digest,path in re.findall(r"^([0-9a-f]{64}) +(.+)$",remote,re.M)}
    archive = base64.b64decode((run / "raw.tar.gz.b64").read_bytes(),validate=True)
    assert sha(archive)==hashes["bounded-evidence.tar.gz"]
    with tarfile.open(fileobj=io.BytesIO(archive),mode="r:gz") as tar:
        raw = {member.name:tar.extractfile(member).read() for member in tar.getmembers()}
    for name in ("inputs.json","test_g_s32_activity.sv","source.sha256","delivery.json"):
        assert sha(raw[name]) == hashes[name]
    for line in raw["source.sha256"].decode().splitlines():
        expected, name = line.split("  ",1)
        assert sha(raw[name]) == expected
    scope = json.loads(raw["inputs.json"])
    assert scope["actual_scope"]==dict(layer=0,batch=0,packets=512)
    assert sha(raw["actual-model-vectors.txt"])==scope["vectors_256_sha256"]
    assert b"G_S32_PASS mode=0 packets=256" in raw["active-simulation.log"]
    assert b"G_ACTIVITY cycles=270 packets=256" in raw["active-simulation.log"]
    assert b"G_ACTIVITY cycles=256 packets=0" in raw["idle-simulation.log"]
    reports = {}
    for mode in ("active","idle","active-clock-only"):
        report = raw[f"{mode}-pins.log"].decode()
        counts = re.search(r"^G_GATE_PIN_ACTIVITY matched=(\d+) trace_only=(\d+) active_clock=(\d+) clocks_only=(\d+)$",report,re.M)
        assert tuple(map(int,counts.groups())) == (77354,47058,830,int(mode=="active-clock-only"))
        assert re.search(r"^vcd\s+204$",report,re.M)
        assert re.search(r"^unannotated\s+0$",report,re.M)
        totals = re.search(r"^Total\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)",report,re.M)
        internal,switching,leakage,total=map(float,totals.groups())
        assert abs(internal+switching+leakage-total)<max(1e-12,total*1e-6)
        reports[mode]=dict(internal_W=internal,switching_W=switching,leakage_W=leakage,total_W=total)
    active,reference=reports["active"],reports["active-clock-only"]
    assert active["leakage_W"]==reference["leakage_W"]
    pulse_J = (active["total_W"]-reference["total_W"]) * (270*3333e-12)/256
    assert pulse_J > 0
    packets=36*11008//2
    return dict(job=102639,voltage_V=1.1,temperature_C=25,clock_period_ps=3333,covered=scope,
                gate_pins=77354,top_port_bits=204,unannotated=0,reports=reports,
                nonclock_J_per_observed_two_lane_packet=pulse_J,
                conditional_g_only_ffn_packet_count_per_token=packets,
                conditional_g_only_ffn_nonclock_J_per_token=pulse_J*packets,
                archive_sha256=sha(archive),whole_token_energy_qualified=False)


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run",type=Path,required=True)
    print(json.dumps(audit(parser.parse_args().run),indent=2))
