"""Verify the combined COPY budget and real shared-DMA FENCE receipt."""

import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import tarfile

from audit_ffn_copy_rearm import sha


PASS = ("PASS ffn_copy_combined scopes=2 copy_fences=1 blocked_ack_cycles=7 "
        "M_fences=22,22,22 first_purges=34 purges=67 W64=52224 COPY=3072 scatter=384")


def audit(receipt, archive_sha, candidate_commit, candidate_sha, lookahead=False):
    with receipt.open("rb") as stream:
        assert hashlib.file_digest(stream, "sha256").hexdigest() == archive_sha
    hashes, manifests, trials, oracles = {}, {}, {}, {}
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
            elif name == "candidate.tar.gz":
                assert hashes[name] == candidate_sha
                with tarfile.open(fileobj=io.BytesIO(raw)) as candidate:
                    assert candidate.pax_headers["comment"] == candidate_commit
            elif name == "allocation.txt":
                allocation = raw.decode()
            elif name == "build.log":
                assert b"%Error" not in raw and b"%Warning" not in raw
            elif name.endswith("/oracle.json"):
                oracles[name.split("/", 1)[0]] = json.loads(raw)
            elif match := re.fullmatch(r"seed-([0-9]+)/mode-([01])-initial-([012])\.log", name):
                assert b"%Error" not in raw and b"%Fatal" not in raw
                lines = raw.decode().splitlines()
                assert [s for s in lines if s.startswith("PASS ffn_copy_combined")] == [PASS]
                witness = "COPY_NEAR_WRAP held_prefetched_U=1 and_old_P_ACK=1"
                assert (witness in lines) == lookahead
                profiles = [s for s in lines if s.startswith("FFN_PROFILE ")]
                assert len(profiles) == 2
                cycles = []
                for index, profile in enumerate(profiles, 1):
                    record = dict(f.split("=", 1) for f in profile.split()[1:])
                    assert set(record) == {"cycles", "W64", "S_copy", "S_scatter"}
                    assert int(record["W64"]) == 26112 and int(record["S_copy"]) == 1536
                    assert int(record["S_scatter"]) == index*192
                    cycles.append(int(record["cycles"]))
                trials[tuple(map(int, match.groups()))] = cycles
    assert "Partition=c96" in allocation and "NumCPUs=96 NumTasks=8 CPUs/Task=12" in allocation
    assert hashes["source.tar.gz"] == "3791b2087fb6a8f050cb7181ac6e08139fecbda84e3db563ee90c4dc4cef385c"
    for manifest in ("source.sha256", "candidate.sha256", "derived.sha256"):
        for line in manifests[manifest].splitlines():
            digest, name = line.split("  ", 1)
            if manifest == "derived.sha256":
                name = re.split(r"/issue250-copy-combined-[0-9-]+/", name, maxsplit=1)[1]
            else:
                name = "source/" + name.removeprefix("./")
            assert hashes[name] == digest
    for name, digest in json.loads(manifests["generated/generated.json"]).items():
        assert hashes["generated/" + name] == digest
    if lookahead:
        assert hashes["test/early_copy_3p_rearm_lookahead.sv"] == "fb6f9d4d24a7a662fd90cd915802223f5d19b41810f21f6acb431659c50ddf23"
        assert hashes["test/early_copy_epoch_3p_rearm_lookahead.sv"] == "96d5d9542d3dde0b6c895a1bc9aaa3744fd069e04a420d64dfca459571123bbc"
    assert set(oracles) == {f"seed-{seed}" for seed in range(25001, 25009)}
    for directory, oracle in oracles.items():
        assert oracle["mid_tiles"] == 3 and oracle["descriptor_count"] == 6 and oracle["split_up_channel"]
        for file, digest in oracle["hashes"].items():
            assert hashes[directory + "/" + file] == digest
    assert set(trials) == {(seed, mode, initial) for seed in range(25001, 25009)
                           for mode in range(2) for initial in range(3)}
    return dict(pass_count=len(trials), checked_members=len(hashes),
                run_cycles_by_scope=[[min(v[i] for v in trials.values()), max(v[i] for v in trials.values())]
                                     for i in range(2)],
                derived_sha256={name: digest for name, digest in sorted(hashes.items())
                                if name.startswith(("test/", "generated/"))})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--candidate-commit", required=True)
    parser.add_argument("--candidate-sha256", required=True)
    parser.add_argument("--lookahead", action="store_true")
    args = parser.parse_args()
    print(json.dumps(audit(args.archive, args.sha256, args.candidate_commit, args.candidate_sha256,
                           args.lookahead), indent=2))


if __name__ == "__main__":
    main()
