#!/usr/bin/env python3
"""Independently verify a recovered compact64 archive; do not extract it.

Usage: python verify-compact64.py archive.tar.gz EXPECTED_ARCHIVE_SHA256
Streams every manifest member, parses the full DRC, and checks final-netlist
binding, native/upper acceptance, and the archived program replay logs.
"""
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import sys
import tarfile
import xml.etree.ElementTree as ET


archive = Path(sys.argv[1])
h = hashlib.sha256()
with archive.open("rb") as stream:
    for chunk in iter(lambda: stream.read(1 << 20), b""):
        h.update(chunk)
assert h.hexdigest() == sys.argv[2], "archive SHA-256 mismatch"
with tarfile.open(archive, "r:gz") as tar:
    members = tar.getmembers()
    names = [m.name for m in members]
    assert len(names) == len(set(names)), "duplicate archive member"
    for member in members:
        path = PurePosixPath(member.name)
        assert not path.is_absolute() and ".." not in path.parts
        assert member.isdir() or member.isfile(), "non-regular archive payload"
    manifest = tar.extractfile("FILES.sha256").read().decode().splitlines()
    verified = set()
    for row in manifest:
        expected, name = row.split("  ./", 1)
        assert name not in verified
        verified.add(name)
        stream = tar.extractfile(name)
        h = hashlib.sha256()
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            h.update(chunk)
        assert h.hexdigest() == expected, name
    actual = {m.name for m in members if m.isfile()} - {"FILES.sha256"}
    assert verified == actual, "manifest does not cover the complete payload"
    release = json.load(tar.extractfile("release.json"))
    native = json.load(tar.extractfile("native/native-result.json"))
    assert native["passed"] and native["native_gds_drc_items"] == 0
    assert set(native["slack_ns"]) == {"max", "min"}
    assert min(native["slack_ns"].values()) >= 0
    assert native["electrical_pass"] and set(native["connected_supplies"]) == {"VDD", "VSS"}
    log = tar.extractfile("native/audit-native.log").read().decode()
    slack = {kind: float(value) for kind, value in re.findall(r"worst slack (max|min) (-?\d+\.\d+)", log)}
    assert slack == native["slack_ns"]
    electrical = log.split("=== ELECTRICAL VIOLATIONS ===", 1)[1].split("=== CONSTRAINT AUDIT ===", 1)[0]
    assert "(VIOLATED)" not in electrical
    for supply in ("VDD", "VSS"):
        assert "All shapes on net " + supply + " are connected." in log
    xml = ET.parse(tar.extractfile("native/native-drc.lyrdb"))
    assert len(xml.findall(".//items/item")) == 0
    for suffix in ("def", "gds", "odb", "sdc", "spef", "v"):
        assert tar.getmember("native/6_final." + suffix).size > 0
    v_sha = hashlib.sha256(tar.extractfile("native/6_final.v").read()).hexdigest()
    assert v_sha == release["final_netlist_sha256"]
    assert hashlib.sha256(tar.extractfile("provenance/package-compact64.py").read()).hexdigest() == release["package_script_sha256"]
    assert hashlib.sha256(tar.extractfile("provenance/original-FreePDK45.lydrc").read()).hexdigest() == \
        "4e35cad6786f21c6e233fb606bea59bb44e1a12713008cf7367d65a1a3de2147"
    upper = json.load(tar.extractfile("upper/upper-timing.json"))
    group = release["variant"].split("_")[0]
    assert set(upper) == {"low", "base", "high"}
    for report in upper.values():
        assert report["electrical_pass"]
        assert report["annotated_upper_nets"] == (34 if group == "P" else 130)
        assert report["timed_upper_paths"] > 0
        assert set(report["slack_ns"]) == {"min", "max"}
        assert min(report["slack_ns"].values()) >= 0
    geometry = json.load(tar.extractfile("upper/overlay.json"))
    assert all(geometry["checks"].values())
    assert len(geometry["routes"]) == (34 if group == "P" else 130)
    variants = ("normal", "even", "legacy") + (("fma",) if group == "U" else ())
    passes = 0
    for variant in variants:
        prefix = "gate/" + variant + "/"
        assert tar.extractfile(prefix + "gate-sha256.txt").read().decode().split()[0] == v_sha
        cases = ("normal",) if group == "P" else ("normal", "stalled", "fault", "stalled-fault", "reset")
        for case in cases:
            text = tar.extractfile(prefix + "results/" + case + ".log").read().decode()
            assert text.count("PASS native") == 3, (variant, case)
            assert tar.getmember(prefix + "results/" + case + ".words").size > 0
            for image in ("mother", "local0", "local1"):
                words = tar.extractfile(prefix + "results/" + case + "/" + image + ".mem").read().decode().splitlines()
                version = (int(words[0], 16) >> 64) & 0xffff
                count = (int(words[1], 16) >> 32) & 0xffffffff
                assert version == (1 if variant == "legacy" else 2)
                if variant == "even":
                    assert count % 2 == 0, (case, image, count)
            passes += 3
    assert passes == release["gate_passes"] == (9 if group == "P" else 60)
    source = json.load(tar.extractfile("provenance/hardware-source-verified.json"))
    assert source["physical_source_matches_committed_hardware"]
result = {"variant": release["variant"], "archive": str(archive.resolve()),
          "archive_sha256": sys.argv[2], "manifest_files": len(verified),
          "native": native, "upper": upper, "gate_passes": passes,
          "final_netlist_sha256": v_sha, "passed": True}
output = archive.with_suffix(".verification.json")
output.write_text(json.dumps(result, indent=2), encoding="utf-8")
print(json.dumps(result, indent=2))
