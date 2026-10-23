"""Read-only native OpenDB inventory adapter. Standard library only.

Run inside the pinned EDA container under a scheduler allocation. Geometry files
are gzip TSV; OBS is separate from electrical conductors. This is an inventory,
not connectivity, DRC, timing, or functional signoff.
"""
import argparse
import collections
import csv
import datetime as dt
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for part in iter(lambda: f.read(1024 * 1024), b""):
            h.update(part)
    return h.hexdigest()

def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def write_json(path, value):
    with Path(path).open("x", encoding="utf-8") as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
        f.write("\n")

def utc():
    return dt.datetime.now(dt.timezone.utc).isoformat()

def safe_new(path):
    path = Path(path).absolute()
    base = Path("/public/home/yuzelu/PingyangHuang").resolve(strict=True)
    resolved_parent = path.parent.resolve(strict=True)
    if base not in (resolved_parent, *resolved_parent.parents):
        raise ValueError("Output parent resolves outside authorized directory")
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.mkdir()
    return path.resolve(strict=True)

def unescape(s):
    return re.sub(r"\\([\\tnr])", lambda m: {"\\":"\\","t":"\t","n":"\n","r":"\r"}[m[1]], s)

def table(directory, name):
    with gzip.open(Path(directory) / (name + ".tsv.gz"), "rt", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f, delimiter="\t", quoting=csv.QUOTE_NONE):
            if None in row or any(v is None for v in row.values()):
                raise ValueError("Malformed table row in " + name)
            yield {k: unescape(v) for k, v in row.items()}

def source_record(path, do_hash=True):
    p = Path(path)
    if not p.is_file():
        return {"path": str(p), "exists": False}
    stat = p.stat()
    return {"path":str(p), "realpath":str(p.resolve()), "exists":True,
            "bytes":stat.st_size, "mtime_ns":stat.st_mtime_ns,
            "sha256":digest(p) if do_hash else None}

def summarize(directory, custom_routing_levels):
    custom_routing_levels = sorted(set(int(x) for x in custom_routing_levels))
    if not custom_routing_levels or min(custom_routing_levels) < 1:
        raise ValueError("custom_routing_levels must contain positive routing levels")
    directory = Path(directory)
    meta = {r["key"]:r["value"] for r in table(directory, "metadata")}
    if meta.get("complete") != "true":
        raise RuntimeError("Native export has no complete marker")
    dbu = int(meta["dbu_per_um"])
    layers = list(table(directory, "layers"))
    level = {r["name"]:int(r["routing_level"]) for r in layers}
    counts = collections.Counter()
    actual_nets = collections.defaultdict(set)
    by_net = collections.Counter()
    obs_counts = collections.Counter()
    max_layer = 0
    shape_rows = 0
    for r in table(directory, "shapes"):
        box = tuple(int(r[k]) for k in ("x0","y0","x1","y1"))
        if box[0] > box[2] or box[1] > box[3]:
            raise ValueError("Inverted shape rectangle")
        key = (r["kind"],r["sig_type"],r["layer"],r["layer_type"])
        counts[key] += 1
        shape_rows += 1
        if r["kind"] == "BLOCK_OBS":
            obs_counts[r["layer"]] += 1
            continue
        if r["layer_type"] == "ROUTING":
            max_layer = max(max_layer, level[r["layer"]])
        if level.get(r["layer"], 0) in custom_routing_levels:
            actual_nets[r["layer"]].add(r["net"])
            by_net[(r["net"],r["sig_type"],r["layer"],r["kind"])] += 1
    expected = {(r["kind"],r["sig_type"],r["layer"],r["layer_type"]):int(r["count"])
                for r in table(directory,"shape_counts")}
    if dict(counts) != expected:
        raise RuntimeError("Independent shape count does not match native export")
    ports = list(table(directory,"bterms"))
    groups = collections.defaultdict(list)
    for p in ports:
        match = re.fullmatch(r"(.*)\[(\d+)\]", p["term"])
        groups[match[1] if match else p["term"]].append(p)
    group_out = []
    for name, rows in sorted(groups.items()):
        indices = [int(re.fullmatch(r".*\[(\d+)\]",p["term"])[1]) for p in rows if re.fullmatch(r".*\[(\d+)\]",p["term"])]
        group_out.append({"name":name, "bits":len(rows),
                          "directions":sorted({p["io_type"] for p in rows}),
                          "signal_types":sorted({p["sig_type"] for p in rows}),
                          "index_min":min(indices) if indices else None,
                          "index_max":max(indices) if indices else None,
                          "index_holes":sorted(set(range(min(indices),max(indices)+1))-set(indices)) if indices else [],
                          "missing_physical_pin_bits":[p["term"] for p in rows if not int(p["pin_count"])]})
    masters = {r["master"]:r for r in table(directory,"masters")}
    master_counts = collections.Counter()
    statuses = collections.Counter()
    instance_rows = 0
    unavailable_origins = 0
    for r in table(directory,"instances"):
        instance_rows += 1
        master_counts[r["master"]] += 1
        statuses[r["status"]] += 1
        unavailable_origins += r["origin_x"] == "UNAVAILABLE"
    if instance_rows != int(meta["instance_count"]):
        raise RuntimeError("Instance export incomplete")
    net_rows = sum(1 for _ in table(directory,"nets"))
    if net_rows != int(meta["net_count"]):
        raise RuntimeError("Net export incomplete")
    mgeom_counts = collections.Counter()
    for r in table(directory,"master_geometry"):
        mgeom_counts[(r["master"],r["category"],r["layer"])] += 1
    iterm_rows = unconnected = 0
    for r in table(directory,"iterms"):
        iterm_rows += 1
        unconnected += not r["net"]
    virtual_count = sum(1 for _ in table(directory,"virtual_connections"))
    via_defs = collections.Counter()
    for r in table(directory,"via_definitions"):
        via_defs[(r["scope"],r["name"],r["bottom_layer"],r["top_layer"])] += 1
    geometric_high = sum(v for key,v in by_net.items())
    master_high = [{"master":key[0], "layer":key[2], "master_pin_boxes":value,
                    "instance_count":master_counts[key[0]], "instantiated_pin_boxes":value*master_counts[key[0]]}
                   for key,value in sorted(mgeom_counts.items())
                   if key[1] == "PIN" and level.get(key[2],0) in custom_routing_levels]
    return {
      "schema_version":1, "status":"inventory_complete",
      "scope":"Read-only native geometry and interface inventory; not connectivity, DRC, timing, or equivalence",
      "native":meta, "dbu_per_um":dbu,
      "die_bbox_dbu":[int(x) for x in meta["die_box"].split()],
      "layers":layers, "highest_observed_routing_level":max_layer,
      "counts":{"instances":instance_rows,"nets":net_rows,"iterms":iterm_rows,
                "unconnected_iterms":unconnected,"shape_rows":shape_rows,"virtual_connections":virtual_count,
                "signal_port_bits":sum(p["sig_type"] not in ("POWER","GROUND") for p in ports)},
      "instance_statuses":dict(statuses), "instances_with_unavailable_origin":unavailable_origins,
      "masters":[dict(masters[n],instance_count=k) for n,k in sorted(master_counts.items())],
      "port_groups":group_out,
      "shape_counts":[dict(zip(("kind","sig_type","layer","layer_type"),key),count=value) for key,value in sorted(counts.items())],
      "master_geometry_counts":[{"master":key[0],"category":key[1],"layer":key[2],"count":value} for key,value in sorted(mgeom_counts.items())],
      "via_definitions":[{"scope":key[0],"name":key[1],"bottom":key[2],"top":key[3],"box_count":value} for key,value in sorted(via_defs.items())],
      "upper_layer_occupancy":{"custom_routing_levels":custom_routing_levels,"electrical_geometry_boxes":geometric_high,
          "master_pin_shapes":master_high,
          "master_pin_shape_instances":sum(x["instantiated_pin_boxes"] for x in master_high),
          "net_counts":{k:len(v) for k,v in actual_nets.items()},
          "nets":[dict(zip(("net","sig_type","layer","kind"),key),shape_boxes=value) for key,value in sorted(by_net.items())]},
      "limitations":[
          "OBS is a routing constraint, not electrical occupancy; it is reported separately.",
          "ITerm bbox is native; exact pin shapes are stored once per master in local coordinates plus instance transform data.",
          "Master geometry is not counted as top-level routing; it remains available for endpoint/access checks.",
          "Virtual SHORT/VWIRE opcodes are recorded and are not accepted as physical conductors.",
          "Layer width/spacing fields do not encode the full foundry rule deck.",
          "No claims of empty M9/M10 if conductors or pins remain; via cuts and landings remain in detailed tables.",
          "Instance origins marked UNAVAILABLE need native API resolution before geometry reconstruction."
      ]}

def run(args):
    config_path = Path(args.config).resolve(strict=True)
    config = read_json(config_path)
    case = next((x for x in config["cases"] if x["id"] == args.case), None)
    if not case or case.get("role") != "primary":
        raise ValueError("Select a primary configured case")
    output = safe_new(args.output)
    native = output / "native"
    native.mkdir()
    record = {"started_utc":utc(),"status":"running","case":case,"config":source_record(config_path),
              "scheduler_job_id":os.getenv("SLURM_JOB_ID",os.getenv("TASK_JOB_ID")),
              "inputs":{},"commands":[],"output":str(output),"read_only_database":True}
    try:
        if not record["scheduler_job_id"]:
            raise RuntimeError("Refusing substantive ODB inventory outside scheduler allocation")
        tool = shutil.which("openroad")
        if not tool:
            raise RuntimeError("OpenROAD missing; source ORFS env.sh")
        record["tools"] = {"openroad":source_record(tool),"python":sys.version,
                           "adapter":source_record(__file__),"native_script":source_record(Path(__file__).with_suffix(".tcl"))}
        version = subprocess.run([tool,"-version"], text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
        record["tools"]["openroad"]["reported_version"] = version.stdout.strip()
        record["tools"]["openroad"]["version_exit_code"] = version.returncode
        for name,path in case["inputs"].items():
            record["inputs"][name] = source_record(path)
        for name,path in config.get("technology_inputs",{}).items():
            record["inputs"]["technology_"+name] = source_record(path)
        missing = [n for n in case.get("required",["odb","netlist","sdc","spef","lef","liberty"]) if not record["inputs"][n]["exists"]]
        if missing:
            raise FileNotFoundError("Missing required inputs: "+", ".join(missing))
        env = dict(os.environ, HPY_INVENTORY_ODB=case["inputs"]["odb"], HPY_INVENTORY_OUTPUT=str(native),
                   PYTHONDONTWRITEBYTECODE="1")
        cmd = [tool,"-exit",str(Path(__file__).with_suffix(".tcl"))]
        record["commands"].append(cmd)
        with (output/"native.log").open("x",encoding="utf-8") as log:
            result = subprocess.run(cmd,env=env,stdout=log,stderr=subprocess.STDOUT,check=False,cwd=output)
        record["native_exit_code"] = result.returncode
        if result.returncode:
            raise RuntimeError("OpenROAD native export failed; inspect native.log")
        summary = summarize(native, config["custom_routing_levels"])
        if summary["native"]["block"] != case["expected_master"]:
            raise RuntimeError("Unexpected actual block name: "+summary["native"]["block"])
        inherited = case.get("inherited_metrics")
        if inherited:
            p = Path(inherited)
            record["inherited_metrics_source"] = source_record(p)
            raw = read_json(p)
            summary["inherited_metrics"] = {k:v for k,v in raw.items() if any(word in k for word in
              ("setup__ws","hold__ws","setup__tns","hold__tns","drv__max_cap","drv__max_slew","drv__max_fanout"))}
            summary["inherited_metrics_note"] = "Existing run metrics, not new STA; original source preserved"
        for name,source in record["inputs"].items():
            if source["exists"]:
                stat = Path(source["path"]).stat()
                if stat.st_size != source["bytes"] or stat.st_mtime_ns != source["mtime_ns"]:
                    raise RuntimeError("Input stat changed during inventory: "+name)
        summary["case_id"] = case["id"]
        summary["source_commit"] = case["source_commit"]
        summary["parameters"] = case.get("parameters")
        summary["clock_constraints"] = case.get("clock_constraints")
        write_json(output/"summary.json",summary)
        record["artifacts"] = {str(p.relative_to(output)):source_record(p) for p in sorted(output.rglob("*")) if p.is_file()}
        record["status"] = "pass_inventory_only"
    except Exception as exc:
        record["status"] = "fail"
        record["error"] = type(exc).__name__+": "+str(exc)
        raise
    finally:
        record["finished_utc"] = utc()
        write_json(output/"execution.json",record)
    print(json.dumps({"output":str(output),"status":record["status"]}))

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command",required=True)
    p = sub.add_parser("run")
    p.add_argument("--config",required=True)
    p.add_argument("--case",required=True)
    p.add_argument("--output",required=True)
    p = sub.add_parser("summarize")
    p.add_argument("--input",required=True)
    p.add_argument("--config",required=True)
    p.add_argument("--output",required=True)
    args = parser.parse_args()
    if args.command == "run":
        run(args)
    else:
        target = Path(args.output)
        allowed = Path("/public/home/yuzelu/PingyangHuang").resolve(strict=True)
        if allowed not in target.parent.resolve(strict=True).parents:
            raise ValueError("Summary output outside allowed directory")
        write_json(target,summarize(args.input, read_json(args.config)["custom_routing_levels"]))

if __name__ == "__main__":
    main()
