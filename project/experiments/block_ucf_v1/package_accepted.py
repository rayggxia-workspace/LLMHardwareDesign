"""Refuse partial deliveries; bundle only three qualified, exact-source U/C/F views."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tarfile

REQUIRED = {"physical", "abstract_lef", "timing", "native_drc", "stream_drc",
            "stream_geometry", "equivalence"}


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for data in iter(lambda: stream.read(1048576), b""):
            digest.update(data)
    return digest.hexdigest()


def verified(path):
    rows = {}
    for line in path.read_text().splitlines():
        digest, filename = line.split("  ", 1)
        entry = path.parent / filename
        assert entry.is_file() and sha(entry) == digest, entry
        assert entry not in rows
        rows[entry] = digest
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("gate", type=Path)
    parser.add_argument("--candidate", action="append", nargs=3, required=True,
                        metavar=("TYPE", "PRODUCER", "AUDIT"))
    args = parser.parse_args()
    gate = args.gate.resolve()
    gate_inputs = verified(gate / "inputs.sha256")
    gate_results = verified(gate / "results.sha256")
    for mode, seed in ((1, 121), (2, 121), (2, 122)):
        log = gate / f"mode-{mode}-seed-{seed}.log"
        assert log in gate_results
        output = log.read_text()
        assert output.count("real-SRAM compute and writeback") == 3
        assert output.count("PASS C-U-C held-source SRAM handoff") == 1
        assert output.count("PASS C interrupt and restart") == 1
    assert sorted(x[0] for x in args.candidate) == ["C", "F", "U"]
    deliverables = []
    for kind, producer, audit in args.candidate:
        prod, receive = Path(producer).resolve(), Path(audit).resolve()
        physical_receipt = receive / "receipt.json"
        checks = json.loads(physical_receipt.read_text())
        assert checks["passed"] is True
        assert set(checks["checks"]) == REQUIRED
        assert all(row["passed"] is True for row in checks["checks"].values())
        done = prod / "completion.json"
        assert checks["input_receipt_sha256"] == sha(done)
        view = receive / "physical-functional.v"
        assert gate_inputs[view] == checks["checks"]["physical"]["functional_netlist_sha256"]
        abstract = receive / "physical-abstract.lef"
        assert sha(abstract) == checks["checks"]["abstract_lef"]["sha256"]
        finish_receipt = json.loads(done.read_text())
        finished = finish_receipt["outputs"]
        views = {Path(p).name: Path(p) for p, digest in finished.items() if sha(Path(p)) == digest}
        assert set(views) == {f"6_final.{ext}" for ext in ("v", "sdc", "def", "odb", "spef", "gds")}
        assert views["6_final.v"].parents[1].name == f"block_{kind.lower()}16"
        for path in (prod / "mapped.v", view):
            assert sha(path) == checks["checks"]["equivalence"]["sources"].get(
                str(path), checks["checks"]["equivalence"]["sources"].get(path.name))
        deliverables.append((kind, prod, receive, views, checks))

    out = args.directory.resolve()
    out.mkdir(parents=True, exist_ok=False)
    delivery = {"scope": "TT 1.1 V 25 C standalone Nangate45 M1-M10 only",
                "timing_view": "final cell netlist, SDC, extracted SPEF, referenced standard and SRAM Liberty",
                "hierarchical_liberty_qualified": False, "blocks": {}}
    for kind, prod, receive, views, checks in deliverables:
        case = out / f"{kind}16"
        case.mkdir()
        members = {**views, "physical-abstract.lef": receive / "physical-abstract.lef",
                   "physical-functional.v": receive / "physical-functional.v",
                   "physical-receipt.json": receive / "receipt.json",
                   "producer-receipt.json": prod / "completion.json",
                   "producer-inputs.json": prod / "inputs.json",
                   "pins.json": prod / "pins.json", "pins.tcl": prod / "pins.tcl"}
        manifest_inputs = json.loads((prod / "inputs.json").read_text())
        canonical = json.loads((prod / "completion.json").read_text()).get("canonical_stream")
        if canonical:
            raw, proof = (Path(canonical[name]) for name in ("raw_gds", "proof"))
            assert sha(raw) == canonical["raw_gds_sha256"]
            assert sha(proof) == canonical["proof_sha256"]
            assert json.loads(proof.read_text())["all_global_physical_masks_identical"]
            members.update({"6_stream_raw.gds": raw, "canonical-wells.json": proof})
        original_sdc, = (Path(p) for p in manifest_inputs if Path(p).name == "input.sdc")
        bank_lib, = (Path(p) for p in manifest_inputs if p.endswith("_TT_1p1V_25C.lib"))
        assert sha(original_sdc) == checks["approved_sdc_sha256"] == manifest_inputs[str(original_sdc)]
        assert sha(bank_lib) == manifest_inputs[str(bank_lib)]
        members.update({"approved-input.sdc": original_sdc, bank_lib.name: bank_lib})
        for name in ("timing.rpt", "timing-summary.tsv", "physical-summary.tsv", "electrical-worst.rpt",
                     "electrical-violations.rpt", "native-drc.rpt", "full-gds-drc.lyrdb",
                     "stream-geometry.json", "gate-kepler.log", "negative-kepler.log",
                     "lef-pins.tsv", "sram-clocks.tsv", "sram-pulse.rpt", "sram-period.rpt"):
            members[name] = receive / name
        for name, source in members.items():
            target = case / name
            shutil.copyfile(source, target)
            assert sha(source) == sha(target)
        manifest = {name: sha(case / name) for name in members}
        (case / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
        path = out / f"{kind}16.tar.gz"
        with tarfile.open(path, "w:gz", compresslevel=3) as archive:
            archive.add(case, arcname=case.name)
        native = checks["checks"]["timing"]["timing"]["timed_endpoints"]
        delivery["blocks"][kind] = dict(passed=True, archive=path.name, sha256=sha(path),
                                         setup_ns=native["minimum_setup_ns"],
                                         hold_ns=native["minimum_hold_ns"], members=manifest)
    gate_evidence = out / "gate"
    gate_evidence.mkdir()
    for source in [gate / "inputs.sha256", gate / "results.sha256", *gate_results]:
        shutil.copyfile(source, gate_evidence / source.name)
        assert sha(source) == sha(gate_evidence / source.name)
    delivery["gate_evidence"] = {path.name: sha(path) for path in gate_evidence.iterdir()}
    (out / "delivery.json").write_text(json.dumps(delivery, indent=2) + "\n")


if __name__ == "__main__":
    main()
