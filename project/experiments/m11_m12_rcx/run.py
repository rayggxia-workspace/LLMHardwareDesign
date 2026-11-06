"""Generate and independently check an OpenRCX model for the 2 µm overlay."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys

BLOCK_V1 = Path(__file__).resolve().parents[1] / "block_v1"
sys.path.insert(0, str(BLOCK_V1))
from heldout_rc import verify_model
from overlay import generate
from pattern_prepare import prepare
from reference_fit import fit_shards
from reference_run import check_rows


def sha(path):
    digest = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def save(path, data):
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def logged(argv, log, cwd):
    with log.open("xb") as stream:
        subprocess.run(argv, cwd=cwd, stdout=stream, stderr=subprocess.STDOUT, check=True)


def openroad(directory, script, body):
    (directory / script).write_text(body, encoding="utf-8")
    logged(["openroad", "-no_init", "-exit", script], directory / (script + ".log"), directory)


def calibrate(out, native_lef, solver, cpus):
    patterns = out / "patterns"
    patterns.mkdir()
    spec = BLOCK_V1 / "technology-2um-v1.json"
    generate(native_lef, json.loads(spec.read_text()), patterns / "overlay")
    openroad(patterns, "prepare.tcl", r'''
read_lef overlay/research12.tech.lef
bench_wires -met_cnt 12 -len 100 -cnt 5 -w_list {1 2} -s_list {1 2 4 8} -all -over_dist 12 -under_dist 12
write_db patterns.odb
write_def patterns.def
set tech [ord::get_db_tech]
set out [open pattern-ndr.json w]
puts $out "{\"dbu_per_um\":[$tech getDbUnitsPerMicron],\"rules\":\{"
set separator ""
foreach rule [$tech getNonDefaultRules] {
  puts -nonewline $out "$separator\"[$rule getName]\":\{"
  set inner ""
  foreach layer [$tech getLayers] {
    set entry [$rule getLayerRule $layer]
    if {$entry ne "NULL" && $entry ne ""} {
      puts -nonewline $out "$inner\"[$layer getName]\":{\"width_dbu\":[$entry getWidth]}"
      set inner ","
    }
  }
  puts -nonewline $out "\}"
  set separator ","
}
puts $out "\}\}"
close $out
''')
    tech = patterns / "overlay/research12.tech.lef"
    inventory = {name: sha(patterns / name) for name in
                 ("patterns.odb", "patterns.def", "overlay/research12.tech.lef")}
    save(patterns / "receipt.json", dict(passed=True, outputs=inventory))
    scenes = out / "scenes"
    prepare(patterns, patterns / "pattern-ndr.json", scenes)
    manifest_path = scenes / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    for metal in ("metal11", "metal12"):
        assert manifest["layers"][metal]["width"] == 2.0

    cases = [case for case in manifest["cases"] if not case["name"].startswith("R6_")]
    workers = max(1, cpus // 2)
    threads = cpus // workers
    folders = [out / f"shard-{i:02d}" for i in range(workers)]

    def solve(index):
        folder = folders[index]
        folder.mkdir()
        shard = cases[index::workers]
        listing = folder / "scenes.txt"
        for case in shard:
            assert sha(Path(case["scene"])) == case["scene_sha256"]
        listing.write_text("".join(case["scene"] + "\n" for case in shard))
        rows_path = folder / "rows.jsonl"
        argv = [str(solver), "scenelist3d", str(threads), str(listing)]
        with rows_path.open("wb") as stdout, (folder / "solver.log").open("wb") as stderr:
            subprocess.run(argv, stdout=stdout, stderr=stderr, check=True)
        rows = [json.loads(line) for line in rows_path.read_text().splitlines()]
        assert rows.pop() == {"status": "PASS", "mode": "scenelist3d"}
        by_case = {}
        for row in rows:
            by_case.setdefault(int(row["case"]), []).append(row)
        assert set(by_case) == {case["id"] for case in shard}
        for case in shard:
            check_rows(case, by_case[case["id"]])
        record = dict(shard=index, receive_only=False, manifest=str(manifest_path),
                      manifest_sha256=manifest_sha, cases=[dict(id=c["id"]) for c in shard],
                      commands=[dict(argv=argv, rows_file=str(rows_path), rows_sha256=sha(rows_path))])
        save(folder / "reference-shard.json", record)
        save(folder / "receipt.json", dict(passed=True, outputs={
            "reference-shard.json": sha(folder / "reference-shard.json")}))

    manifest_sha = sha(manifest_path)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        list(pool.map(solve, range(workers)))
    fit = out / "fit"
    fit.mkdir()
    fit_shards(fit, lambda argv, log: logged(argv, fit / log, fit), folders)
    print("Model generated:", fit / "research12.rules", flush=True)
    return tech, fit / "research12.rules", manifest["layers"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--native-lef", type=Path, required=True)
    parser.add_argument("--solver", type=Path, required=True)
    parser.add_argument("--solver-sha256", required=True)
    parser.add_argument("--reuse-fit", type=Path, help="Existing run root; only run held-out checks")
    parser.add_argument("--version", type=float, choices=(1.0, 2.0, 2.2, 2.3), default=1.0,
                        help="OpenRCX extraction engine for held-out checks")
    args = parser.parse_args()
    cpus = int(os.environ.get("SLURM_CPUS_PER_TASK", "8"))
    assert cpus >= 8
    solver = args.solver.resolve(strict=True)
    assert sha(solver) == args.solver_sha256
    out = args.out.resolve()
    out.mkdir()
    if args.reuse_fit:
        source = args.reuse_fit.resolve(strict=True)
        tech = source / "patterns/overlay/research12.tech.lef"
        model = source / "fit/research12.rules"
        layers = json.loads((source / "scenes/manifest.json").read_text())["layers"]
    else:
        tech, model, layers = calibrate(out, args.native_lef.resolve(strict=True), solver, cpus)
    checks = out / "heldout"
    checks.mkdir()
    verify_model(checks, cpus, lambda argv, log: logged(argv, checks / log, checks),
                 args.version, model, layers, tech, solver, research_2um=True)


if __name__ == "__main__":
    main()
