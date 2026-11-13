"""Independently read back strict three-P COPY rearm receipts."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import tarfile


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def audit(receipt, expected_sha, source_commit):
    with receipt.open("rb") as stream:
        assert hashlib.file_digest(stream, "sha256").hexdigest() == expected_sha
    hashes, manifests, trials, oracles, sources = {}, {}, {}, {}, {}
    allocation = ""
    with tarfile.open(receipt, "r|gz") as archive:
        for member in archive:
            if not member.isfile():
                continue
            name = member.name.removeprefix("./")
            raw = archive.extractfile(member).read()
            assert name not in hashes
            hashes[name] = sha(raw)
            if name in {"source.sha256", "candidate.sha256", "derived.sha256", "generated/generated.json"}:
                manifests[name] = raw.decode()
            elif name.startswith(("test/ffn_", "generated/ffn_")):
                sources[name] = raw
            elif name == "allocation.txt":
                allocation = raw.decode()
            elif name == "candidate-commit.txt":
                assert raw.decode().strip() == source_commit
            elif name == "build.log":
                assert b"%Error" not in raw and b"%Warning" not in raw
            elif name.endswith("/oracle.json"):
                oracles[name.split("/", 1)[0]] = json.loads(raw)
            elif m := re.fullmatch(r"seed-([0-9]+)/mode-([01])-initial-([012])\.log", name):
                assert b"%Error" not in raw and b"%Fatal" not in raw
                lines = raw.decode().splitlines()
                passed, = [s for s in lines if s.startswith("PASS ffn_copy_rearm")]
                assert passed == "PASS ffn_copy_rearm old_final=65535 new_final=32 held_ack_cycles=7 fences=1 words=3072 scatter=384"
                profiles = [s for s in lines if s.startswith("FFN_PROFILE ")]
                assert len(profiles) == 2
                cycles = []
                for i, profile in enumerate(profiles, 1):
                    p = dict(f.split("=", 1) for f in profile.split()[1:])
                    assert set(p) == {"cycles", "W64", "S_copy", "S_scatter"}
                    assert int(p["W64"]) == 26112 and int(p["S_copy"]) == 1536
                    assert int(p["S_scatter"]) == i*192
                    cycles.append(int(p["cycles"]))
                trials[tuple(map(int, m.groups()))] = cycles
    assert "Partition=c96" in allocation and "NumCPUs=96 NumTasks=8 CPUs/Task=12" in allocation
    assert hashes["baseline-source.tar.gz"] == "96846063d9c8d71fcf069ceba40bd4accd3fa39096397431b4c8e3f33d543467"
    for manifest in ("source.sha256", "candidate.sha256", "derived.sha256"):
        for line in manifests[manifest].splitlines():
            digest, name = line.split("  ", 1)
            if manifest == "derived.sha256":
                name = re.split(r"/issue250-copy-rearm-[0-9-]+/", name, maxsplit=1)[1]
            else:
                name = "source/" + name
            assert hashes[name] == digest
    for name, digest in json.loads(manifests["generated/generated.json"]).items():
        assert hashes["generated/" + name] == digest
    for name, old, new in (
        ("ffn_stripe_commit_rearm.sv", b"source<=0;way<=0;epoch<=0;", b"source<=0;way<=0;epoch<=16'hfff3;"),
        ("ffn_gate_up_mid_rearm.sv", b"if(reset)begin quant_epoch<=0;", b"if(reset)begin quant_epoch<=16'hfffc;"),
    ):
        actual = sources["generated/" + name]
        assert actual.count(old) == 1 and actual.replace(old, new) == sources["test/" + name]
    assert set(oracles) == {f"seed-{seed}" for seed in range(25001, 25009)}
    for directory, oracle in oracles.items():
        assert oracle["mid_tiles"] == 3 and oracle["descriptor_count"] == 6
        for file, digest in oracle["hashes"].items():
            assert hashes[directory + "/" + file] == digest
    assert set(trials) == {(seed, mode, initial) for seed in range(25001, 25009)
                           for mode in range(2) for initial in range(3)}
    return dict(pass_count=len(trials), run_cycles_by_scope=[[min(v[i] for v in trials.values()),
                                                            max(v[i] for v in trials.values())] for i in range(2)],
                checked_members=len(hashes), generated_sources=json.loads(manifests["generated/generated.json"]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--source-commit", required=True)
    args = parser.parse_args()
    print(json.dumps(audit(args.archive, args.sha256, args.source_commit)))


if __name__ == "__main__":
    main()
