"""Assemble #202 Maxwell rows in bounded blocks and emit the #206 SPEF."""
import argparse
from array import array
from collections import defaultdict
from contextlib import ExitStack
from hashlib import sha256
import json
import math
from pathlib import Path
import re
from struct import Struct

from field_extract import scaled_bins
from run import save, sha

BLOCK = 16
BIN = Struct("<IIIId")


def checked(prep, proof, filename, key):
    path = prep / filename
    assert sha(path) == proof[key], path
    return path


def shard_rows(folder, geom, count):
    paths, receipts = {}, {}
    for path in sorted(folder.glob("job-*/result/shard.json")):
        row = json.loads(path.read_text())
        assert row["passed"] and row["field_sha256"] == geom["field_sha256"]
        assert row["solver_sha256"] == geom["solver_sha256"]
        shard, shards = row["shard"], row["shards"]
        assert shard not in receipts
        assert set(map(int, row["rows"])) == set(range(shard, count, shards))
        receipts[shard] = dict(path=str(path), sha256=sha(path), walks=row["walks"])
        for name, digest in row["rows"].items():
            i = int(name)
            assert i not in paths
            paths[i] = (path.parent / f"row-{i:03}.json", digest)
    assert set(paths) == set(range(count)) and len(receipts) == shards
    return paths, receipts


def spool_rows(out, nets, paths):
    n = len(nets)
    widths = [len(net["nodes"]) for net in nets]
    caps, sigmas, ground, rows = [], [], [], []
    files = [out / f"bins-{i:03}.bin" for i in range((n + BLOCK - 1) // BLOCK)]
    with ExitStack() as stack:
        bins = [stack.enter_context(path.open("wb")) for path in files]
        for i in range(n):
            path, digest = paths[i]
            data = path.read_bytes()
            assert sha256(data).hexdigest() == digest
            row = json.loads(data)
            assert row["master"] == i and row["walks"] > 0 and row["hops"] > 0
            values = row["values"]
            total, sigma = values[i]
            assert len(values) == n and total > 0 and sigma <= .003 * total
            for value, error in (*values, row["ground"]):
                assert math.isfinite(value) and math.isfinite(error) and error >= 0
            assert abs(sum(value for value, _ in values) + row["ground"][0]) <= 1e-9 * total
            totals = [0.] * (n + 1)
            buffers, local_ground = defaultdict(bytearray), {}
            for j, a, b, value, error in row["bins"]:
                assert 0 <= j <= n and j != i and 0 <= a < widths[i]
                assert math.isfinite(value) and math.isfinite(error) and error >= 0
                totals[j] += value
                if j == n:
                    assert b == 0 and a not in local_ground
                    local_ground[a] = -value
                else:
                    assert 0 <= b < widths[j]
                    left, right, x, y = (i, j, a, b) if i < j else (j, i, b, a)
                    buffers[left // BLOCK] += BIN.pack(left, right, x, y, -value / 2)
            for j, (value, _) in enumerate([*values, row["ground"]]):
                if j != i:
                    assert abs(totals[j] - value) <= 1e-9 * total
            g = -row["ground"][0]
            assert g > 0
            ground.append(scaled_bins(local_ground, g))
            caps.append(array("d", (value for value, _ in values)))
            sigmas.append(array("d", (error for _, error in values)))
            rows.append(dict(walks=row["walks"], sigma_fraction=sigma / total, total_ff=total))
            for block, data in buffers.items():
                bins[block].write(data)
            if i % 256 == 255:
                print(f"Validated and partitioned {i + 1}/{n} Maxwell rows", flush=True)
    return files, caps, sigmas, ground, rows


def source_records(path):
    text = path.read_text()
    assert "*C_UNIT 1 PF\n" in text and "*R_UNIT 1 OHM\n" in text
    header, *parts = re.split(r"(?m)^\*D_NET ", text)
    aliases = dict(re.findall(r"(?m)^(\*\d+) ([^\s]+)\s*$", header))
    result = {}
    for part in parts:
        first, tail = part.split("\n", 1)
        alias, _ = first.split()
        conn, tail = tail.split("*CAP\n", 1)
        _, res = tail.split("*RES\n", 1)
        result[aliases[alias]] = (alias, conn, res)
    return header, result


def resistance_digest(path):
    """Hash each preserved *CONN and *RES record without loading the CAP body."""
    result, digest, inside = {}, None, False
    with path.open("rb") as stream:
        for line in stream:
            if line.startswith(b"*D_NET "):
                alias = line.split()[1]
                assert alias not in result
                digest = sha256()
            elif line.startswith((b"*CONN", b"*RES")):
                inside = True
            elif line.startswith(b"*CAP"):
                inside = False
            if inside:
                digest.update(line)
            if line.startswith(b"*END"):
                result[alias] = digest.hexdigest()
                inside = False
    return result


def emit(out, baseline, nets, files, caps, sigmas, ground, crossings):
    header, original = source_records(baseline)
    names = [net["name"] for net in nets]
    labels = [list(net["nodes"]) for net in nets]
    assert set(names) == set(original)
    count = len(names)
    ground_total = [sum(values.values()) for values in ground]
    mutual_total = [0.] * count
    remaining = set(crossings)
    index_positions = []
    pair_count = cap_count = 0
    max_reciprocity = 0.0
    with (out / "field.spef").open("wb+") as target, (out / "expected-pairs.tsv").open("w") as pair_file:
        def write(text):
            target.write(text.encode("ascii"))

        write(header)
        for block, path in enumerate(files):
            bins = defaultdict(lambda: defaultdict(float))
            with path.open("rb") as data:
                for chunk in iter(lambda: data.read(BIN.size * 16384), b""):
                    for i, j, a, b, ff in BIN.iter_unpack(chunk):
                        bins[i, j][a, b] += ff
            for i in range(block * BLOCK, min((block + 1) * BLOCK, count)):
                alias, conn, res = original[names[i]]
                write(f"*D_NET {alias} ")
                index_positions.append(target.tell())
                write(" " * 24 + "\n" + conn + "*CAP\n")
                index = 0
                for index, (a, ff) in enumerate(ground[i].items(), 1):
                    write(f"{index} {labels[i][a]} {ff / 1000:.12g}\n")
                for j in range(i + 1, count):
                    a, b = caps[i][j], caps[j][i]
                    total = min(caps[i][i], caps[j][j])
                    noise = 5 * math.hypot(sigmas[i][j], sigmas[j][i])
                    change = abs(a - b)
                    max_reciprocity = max(max_reciprocity, change / total)
                    assert change <= noise + .01 * total, (names[i], names[j], a, b)
                    value = -(a + b) / 2
                    assert value >= -(noise + .0001 * total), (names[i], names[j], a, b)
                    if value <= 0:
                        continue
                    physical = scaled_bins(bins[i, j], value)
                    for (x, y), ff in physical.items():
                        index += 1
                        write(f"{index} {labels[i][x]} {labels[j][y]} {ff / 1000:.12g}\n")
                    mutual_total[i] += value
                    mutual_total[j] += value
                    pair_count += 1
                    cap_count += len(physical)
                    remaining.discard((names[i], names[j]))
                    pair_file.write(f"{names[i]}\t{names[j]}\t{value:.17g}\n")
                write("*RES\n" + res)
            if block % 16 == 15:
                print(f"Emitted RC nets through block {block}", flush=True)
        for i, position in enumerate(index_positions):
            target.seek(position)
            write(f"{(ground_total[i] + mutual_total[i]) / 1000:>24.12g}")
    assert not remaining, sorted(remaining)[:20]
    diagonal = [abs(g + c - caps[i][i]) / caps[i][i] for i, (g, c) in
                enumerate(zip(ground_total, mutual_total))]
    assert max(diagonal) <= .03, (names[diagonal.index(max(diagonal))], max(diagonal))
    assert resistance_digest(out / "field.spef") == resistance_digest(baseline)
    with (out / "expected-totals.tsv").open("w") as stream:
        for name, g, c in zip(names, ground_total, mutual_total):
            stream.write(f"{name}\t{g:.17g}\t{c:.17g}\n")
    return dict(net_pairs=pair_count, node_pairs=cap_count, total_ground_ff=sum(ground_total),
                total_coupling_ff=sum(mutual_total) / 2, maximum_diagonal_change=max(diagonal),
                max_directional_reciprocity_difference_over_total=max_reciprocity)


def assemble(out, prep, rows_dir):
    geom = json.loads((prep / "geometry.json").read_text())
    assert geom["passed"] and geom["net_count"] == 2491
    nets = json.loads(checked(prep, geom, "conductors.json", "conductors_sha256").read_text())
    baseline = checked(prep, geom, "resistance.spef", "resistance_sha256")
    crossings = {tuple(x) for x in json.loads(
        checked(prep, geom, "crossings.json", "crossings_sha256").read_text())}
    paths, shards = shard_rows(rows_dir, geom, len(nets))
    files, caps, sigmas, ground, rows = spool_rows(out, nets, paths)
    metrics = emit(out, baseline, nets, files, caps, sigmas, ground, crossings)
    artifact = out / "field.spef"
    result = dict(passed=True, net_count=len(nets), projected_crossings=len(crossings),
                  crossing_pairs_with_nonzero_coupling=len(crossings),
                  maximum_sigma_fraction=max(row["sigma_fraction"] for row in rows),
                  total_walks=sum(row["walks"] for row in rows), shards=shards,
                  field_spef_bytes=artifact.stat().st_size, field_spef_sha256=sha(artifact),
                  pairs_sha256=sha(out / "expected-pairs.tsv"), totals_sha256=sha(out / "expected-totals.tsv"),
                  geometry_sha256=sha(prep / "geometry.json"), **metrics)
    save(out / "assembly.json", result)
    print(json.dumps({k: v for k, v in result.items() if k != "shards"}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("out", "prep", "rows-dir"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir()
    assemble(args.out, args.prep, args.rows_dir)
