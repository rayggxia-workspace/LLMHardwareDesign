"""Stream independent receipt checks for three physical P.S bank models."""
import argparse
import base64
import hashlib
import io
import json
from pathlib import Path
import re
import tarfile
import zlib


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def fields(line):
    return {k: int(v) for k,v in (x.split("=",1) for x in line.split()[1:])}


def audit(root, cache):
    results = []
    paired_fabric = {}
    for run in json.loads((root/"index.json").read_text(encoding="utf-8"))["runs"]:
        job = run["job"]
        source = base64.b64decode((root/run["source_archive"]).read_bytes(), validate=True)
        assert sha(source) == run["source_sha256"]
        with tarfile.open(fileobj=io.BytesIO(source), mode="r:gz") as t:
            assert t.extractfile("source/source-commit.txt").read().decode().strip() == run["source_commit"]
            source_manifest = t.extractfile("source.sha256").read()
            for line in source_manifest.decode().splitlines():
                digest, path = line.split("  ",1)
                assert sha(t.extractfile("source/"+path).read()) == digest
        receipt = cache/f"{job}-receipts.tar.gz"
        assert receipt.stat().st_size == run["receipts_external"]["bytes"]
        with receipt.open("rb") as f:
            assert hashlib.file_digest(f,"sha256").hexdigest() == run["receipts_sha256"]
        hashes, oracles, scopes, profiles, fails = {}, {}, {}, {}, []
        build = b""
        manifest = None
        with tarfile.open(receipt, mode="r|gz") as t:
            for member in t:
                assert member.isfile() and member.name not in hashes
                data = t.extractfile(member).read()
                if member.name == "receipts-manifest.json":
                    manifest = json.loads(data)
                    continue
                hashes[member.name] = sha(data)
                if member.name == "source.sha256":
                    assert data == source_manifest
                if member.name == "build.log":
                    build = data
                if member.name.endswith("/oracle.json"):
                    oracles[member.name.rsplit("/",1)[0]] = json.loads(data)
                if member.name.endswith("/scopes.hex"):
                    scopes[member.name.rsplit("/",1)[0]] = data.decode().splitlines()
                m = re.fullmatch(r"(seed-[0-9]+)/mode-([01])-initial-([012])\.log", member.name)
                if m:
                    lines = data.decode().splitlines()
                    if any("%Fatal:" in x for x in lines):
                        fails.append(member.name)
                    else:
                        row, = [fields(x.removeprefix("PASS ")) for x in lines if x.startswith("PASS ffn_three_p_native ")]
                        ffn, = [fields(x) for x in lines if x.startswith("FFN_PROFILE ")]
                        down = [fields(x) for x in lines if x.startswith("DOWN_PROFILE ")]
                        dma = [fields(x) for x in lines if x.startswith("DMA_PROFILE ")]
                        programs = [fields(x) for x in lines if x.startswith("PROGRAM_PROFILE ")]
                        profiles[(m[1],int(m[2]),int(m[3]))] = (row,ffn,down,dma,programs)
        assert manifest == hashes
        if run["state"] == "FAILED":
            assert not profiles and (b"%Error" in build or fails), run["accounting"]
        elif job == 102514:
            assert not profiles and not oracles and not build
        else:
            assert len(profiles) == 36 and not fails and b"%Warning" not in build and b"%Error" not in build
            assert set(oracles) == {f"seed-{s}" for s in range(25001,25007)}
            for directory, oracle in oracles.items():
                for path, digest in oracle["hashes"].items():
                    assert hashes[directory+"/"+path] == digest
                words = scopes[directory]
                assert len(words) == oracle["descriptor_count"]
                for word, binding in zip(words,oracle["first_descriptors"],strict=True):
                    d = int(word,16).to_bytes(128,"little")
                    assert int.from_bytes(d[124:128],"little") == zlib.crc32(d[:124])
                    assert sha(d) == binding["sha256"]
                for mode in (0,1):
                    for initial in (0,1,2):
                        row, ffn, down, dma, programs = profiles[directory,mode,initial]
                        n, stripes = row["columns"], row["stripes"]
                        assert row["real_P_M"] == 3 and row["real_S_banks"] == 16
                        assert row["Mid"] == n//128 == oracle["mid_tiles"] and row["mode"] == mode
                        assert row.get("down",0) == len(down) == int(oracle.get("down",False))
                        assert stripes == (n+191)//192 and ffn["W64"] == n//8*32*17
                        assert ffn["S_copy"] == stripes*768 and ffn["S_scatter"] == n//2
                        if down:
                            d, = down
                            assert d["W64"] == 2048//8*86*17 and d["S_copy_words"] == 24768
                            assert d["result_words"] == 512 and d["Mid_replays"] == 516
                        assert len(dma) == row.get("shared_dma",0)
                        assert len(programs) == row.get("program",0)
                        if dma:
                            transport, = dma
                            beats = ffn["W64"] + (down[0]["W64"] if down else 0)
                            if programs:
                                program, = programs
                                assert program["calls"] == oracle["descriptor_count"]
                                assert program["confirmed_reads"] == beats*64 + program["calls"]*128
                                assert program["confirmed_writes"] == n*8 + (8192 if down else 0)
                                beats += 2*program["calls"]
                            assert transport["backend_requests"] == transport["backend_returns"] == beats
                            assert transport["purges"] >= 1
        rows = list(profiles.values())
        if job in (102563,102564):
            paired_fabric[job] = profiles
        results.append(dict(job=job, state=run["state"], trials=len(rows), sampled_failures=len(fails),
            gate_cycles=[min(x[1]["cycles"] for x in rows),max(x[1]["cycles"] for x in rows)] if rows else [],
            down_cycles=[min(x[2][0]["cycles"] for x in rows),max(x[2][0]["cycles"] for x in rows)]
                if rows and rows[0][2] else [],
            shared_dma=bool(rows and rows[0][3]), four_w=bool(rows and rows[0][0].get("four_w",0)),
            programmed=bool(rows and rows[0][4])))
    comparison = None
    if set(paired_fabric) == {102563,102564}:
        serial, four = (paired_fabric[job] for job in (102563,102564))
        assert set(serial) == set(four)
        rows = []
        for key, baseline in sorted(serial.items()):
            candidate = four[key]
            assert baseline[0]["four_w"] == 0 and candidate[0]["four_w"] == 1
            assert baseline[1]["W64"] == candidate[1]["W64"]
            assert baseline[2][0]["W64"] == candidate[2][0]["W64"] and baseline[3] == candidate[3]
            cycles_before = baseline[1]["cycles"] + baseline[2][0]["cycles"]
            cycles_after = candidate[1]["cycles"] + candidate[2][0]["cycles"]
            rows.append(dict(seed=key[0], pressure=key[1], initial=key[2], serial_cycles=cycles_before,
                             four_w_cycles=cycles_after, fraction_saved=1-cycles_after/cycles_before))
        comparison = dict(serial_job=102563, four_w_job=102564, pairs=rows,
                          fraction_saved_min=min(r["fraction_saved"] for r in rows),
                          fraction_saved_max=max(r["fraction_saved"] for r in rows))
    return dict(passed=True,runs=results,paired_fabric=comparison)


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root",type=Path,required=True)
    parser.add_argument("--receipt-cache",type=Path,required=True)
    args=parser.parse_args()
    print(json.dumps(audit(args.root,args.receipt_cache),indent=2))
