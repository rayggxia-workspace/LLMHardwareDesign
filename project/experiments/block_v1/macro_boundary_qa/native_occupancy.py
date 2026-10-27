"""Read a source-bound ODB and compare occupied metal against abstract OBS."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import time

from audit import Bundle, audit_source, file_sha, require
from obstruction_coverage import inspect


def execute(index, output, executable, geometry_helper):
    bundle = Bundle(index)
    audit_source(bundle)
    executable, geometry_helper = Path(executable).resolve(), Path(geometry_helper).resolve()
    script = Path(__file__).with_name("source_occupancy.tcl")
    output = Path(output).resolve()
    require(all(not output.is_relative_to(path.parent) for path in bundle.paths.values()), "occupancy output inside evidence inputs")
    sealed = {"executable": file_sha(executable), "geometry_helper": file_sha(geometry_helper),
              "script": file_sha(script), "index": file_sha(bundle.index_path)}
    output.mkdir(parents=True, exist_ok=False)
    receipt = {"schema": "block-v1-native-occupancy-receipt/1", "passed": False,
               "started": time.time(), "inputs": sealed,
               "source_odb_sha256": bundle.digest("final_odb"),
               "source_lef_sha256": bundle.digest("lef"),
               "readback_sha256": bundle.digest("lef_interface"), "outputs": {}}
    try:
        env = dict(os.environ, OMP_NUM_THREADS="1", BV1QA_ODB=str(bundle.paths["final_odb"]),
                   BV1QA_GEOMETRY_HELPER=str(geometry_helper))
        argv = [str(executable), "-no_init", "-exit", str(script)]
        receipt["argv"] = argv
        with (output / "native.log").open("w", encoding="utf-8") as log:
            code = subprocess.run(argv, cwd=output, env=env, stdout=log, stderr=subprocess.STDOUT).returncode
        receipt["returncode"] = code
        require(code == 0, "native occupancy export failed; preserve native.log")
        stats = {}
        for line in (output / "occupancy-summary.tsv").read_text().splitlines():
            key, value = line.split("\t")
            require(key not in stats and value.isdigit(), "occupancy summary")
            stats[key] = int(value)
        require(set(stats) == {"dbu_per_um", "native_instances", "native_master_obstruction_boxes"}
                and stats["dbu_per_um"] == 2000 and stats["native_instances"] > 0, "native occupancy scope/count")
        with (output / "source-occupancy.tsv").open(encoding="utf-8") as stream:
            result = inspect((line.rstrip("\n").split("\t") for line in stream), bundle.rows("lef_interface"))
        result.update(native_summary=stats, source_odb_sha256=bundle.digest("final_odb"),
                      source_occupancy_sha256=file_sha(output / "source-occupancy.tsv"),
                      source_index_sha256=sealed["index"])
        (output / "occupancy-coverage.json").write_text(json.dumps(result, indent=2)+"\n", encoding="utf-8")
        bundle.unchanged()
        require(all(file_sha(path) == sealed[role] for role, path in
                    (("executable", executable), ("geometry_helper", geometry_helper), ("script", script))),
                "occupancy producer changed during run")
        receipt["passed"] = True  # Completed diagnostic; coverage result may be false.
        return result
    except Exception as error:
        receipt["error"] = f"{type(error).__name__}: {error}"
        raise
    finally:
        receipt["finished"] = time.time()
        receipt["outputs"] = {p.name: file_sha(p) for p in output.iterdir() if p.is_file() and p.name != "receipt.json"}
        (output / "receipt.json").write_text(json.dumps(receipt, indent=2)+"\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("index", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--executable", type=Path, required=True)
    parser.add_argument("--geometry-helper", type=Path, required=True)
    args = parser.parse_args()
    result = execute(args.index, args.output, args.executable, args.geometry_helper)
    print(json.dumps(result, indent=2))
    return 0 if result["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
