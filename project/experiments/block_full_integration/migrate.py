"""Selective upper-layer wire migration qualification; standard library only.

No source input is written. Native FIXED route encoding is qualified by a floorplan-mode DEF
NETS-only roundtrip and an exact physical inventory comparison before rerouting.
This tool does not certify formal equivalence, extracted connectivity, or signoff.
"""
import argparse
import collections
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

def sibling(name):
    spec = importlib.util.spec_from_file_location("hpy_"+name, Path(__file__).with_name(name+".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod
inv = sibling("native_inventory")
review = sibling("native_review")
geometry = sibling("native_geometry")

def nets_only_def(source, target):
    """Use the native writer's NETS text verbatim; never edit route geometry."""
    text = Path(source).read_text()
    match = re.search(r"(?m)^NETS\s+(\d+)\s*;\s*$", text)
    end = re.search(r"(?m)^END NETS\s*$", text)
    if not match or not end or end.start() < match.end():
        raise ValueError("Native DEF has no unique NETS section")
    if len(re.findall(r"(?m)^NETS\s",text)) != 1:
        raise ValueError("Ambiguous native DEF")
    header = []
    for pattern in (r"VERSION\s+[^;]+;",r"DIVIDERCHAR\s+[^;]+;",
                    r"BUSBITCHARS\s+[^;]+;",r"DESIGN\s+[^;]+;",
                    r"UNITS\s+DISTANCE\s+MICRONS\s+\d+\s*;"):
        item = re.search(r"(?m)^"+pattern,text)
        if not item:
            raise ValueError("Missing native DEF header: "+pattern)
        header.append(item[0])
    body = text[match.start():end.end()]
    if re.search(r"\+\s+PROPERTY\b",body):
        raise ValueError("NETS properties require a reviewed DEF property adapter")
    count = len(re.findall(r"(?m)^[ \t]*-\s",body))
    if count != int(match[1]):
        raise ValueError("Native DEF NETS record count mismatch")
    with Path(target).open("x") as f:
        f.write("\n".join(header)+"\n"+body+"\nEND DESIGN\n")
    return count

def canonical_rows(directory, table, omit=()):
    return collections.Counter(tuple(sorted((k,v) for k,v in r.items() if k not in omit))
                               for r in inv.table(directory,table))

def grouped_shapes(directory):
    groups = collections.defaultdict(collections.Counter)
    for row in inv.table(directory,"shapes"):
        # db object IDs/opcode offsets may differ after a legal serialization.
        # All physical rectangles, layer/type, net, and via center are retained.
        key = tuple(sorted((k,v) for k,v in row.items() if k != "object"))
        groups[row["net"]][key] += 1
    return groups

def compare(before, after, targets, allow_target_change):
    result = {"status":"pass","scope":"Exact cell/endpoint/geometry inventory comparison",
              "tables":{}, "changed_nets":[], "forbidden_changes":[]}
    for table in ("instances","masters","master_geometry","layers","via_definitions","iterms","bterms","nets"):
        a,b = canonical_rows(before,table),canonical_rows(after,table)
        same = a == b
        result["tables"][table] = {"equal":same,"removed_rows":sum((a-b).values()),"added_rows":sum((b-a).values())}
        if not same:
            result["forbidden_changes"].append(table)
    bm = {r["key"]:r["value"] for r in inv.table(before,"metadata")}
    am = {r["key"]:r["value"] for r in inv.table(after,"metadata")}
    for key in ("block","dbu_per_um","manufacturing_grid_dbu","die_box","instance_count","net_count"):
        if bm.get(key) != am.get(key):
            result["forbidden_changes"].append("metadata:"+key)
    a,b = grouped_shapes(before),grouped_shapes(after)
    ordinary = {"WIRE","WIRE_VIA","PATCH"}
    for net in sorted(a.keys()|b.keys()):
        removed,added = a[net]-b[net],b[net]-a[net]
        if not removed and not added:
            continue
        changed = {"net":net,"removed_boxes":sum(removed.values()),"added_boxes":sum(added.values()),
                   "before_boxes":sum(a[net].values()),"after_boxes":sum(b[net].values()),
                   "before_by_layer":dict(collections.Counter(dict(k)["layer"] for k in a[net].elements())),
                   "after_by_layer":dict(collections.Counter(dict(k)["layer"] for k in b[net].elements()))}
        result["changed_nets"].append(changed)
        kinds = {dict(k)["kind"] for k in list(removed)+list(added)}
        if not allow_target_change or net not in targets or not kinds <= ordinary:
            result["forbidden_changes"].append("geometry:"+net)
    # Virtual wires are unsupported evidence for this selective physical route.
    for directory in (before,after):
        if any(True for _ in inv.table(directory,"virtual_connections")):
            result["forbidden_changes"].append("virtual_connection_present")
    if result["forbidden_changes"]:
        result["status"] = "fail"
    result["note"] = "Target complete wire reroute can change its M1-M8 shapes. Non-target conductors, PG, BPin, obstacles, and every cell/endpoint must be exact."
    return result

def stage(output, name, env, tool, record, script=None):
    dest = output/name
    dest.mkdir()
    script = script or Path(__file__).with_suffix(".tcl")
    cmd = [tool,"-exit",str(script)]
    runenv = dict(env,HPY_MIG_STAGE=name.split("__")[0],HPY_MIG_OUTPUT=str(dest))
    with (dest/"openroad.log").open("x") as log:
        proc = subprocess.run(cmd,env=runenv,cwd=dest,stdout=log,stderr=subprocess.STDOUT)
    record["stages"].append({"name":name,"command":cmd,"exit_code":proc.returncode,"output":str(dest)})
    if proc.returncode:
        raise RuntimeError("Stage failed: "+name)
    return dest

def native(output, name, odb, env, tool, record, custom):
    dest = output/name
    dest.mkdir()
    native_dir = dest/"native"
    native_dir.mkdir()
    runenv = dict(env,HPY_INVENTORY_ODB=str(odb),HPY_INVENTORY_OUTPUT=str(native_dir))
    cmd = [tool,"-exit",str(Path(__file__).with_name("native_inventory.tcl"))]
    with (dest/"native.log").open("x") as log:
        proc = subprocess.run(cmd,env=runenv,cwd=dest,stdout=log,stderr=subprocess.STDOUT)
    record["stages"].append({"name":name,"command":cmd,"exit_code":proc.returncode,"output":str(dest)})
    if proc.returncode:
        raise RuntimeError("Native inventory failed: "+name)
    summary = inv.summarize(native_dir,custom)
    inv.write_json(dest/"summary.json",summary)
    inv.write_json(dest/"review.json",review.review(native_dir,verify_hashes=False))
    return native_dir,summary

def choose_targets(directory, custom):
    levels = {r["name"]:int(r["routing_level"]) for r in inv.table(directory,"layers")}
    result = set()
    forbidden = []
    for row in inv.table(directory,"shapes"):
        if levels.get(row["layer"],0) not in custom or row["kind"] == "BLOCK_OBS":
            continue
        if row["kind"] not in {"WIRE","WIRE_VIA","PATCH"} or row["sig_type"] in {"POWER","GROUND"}:
            forbidden.append({k:row[k] for k in ("kind","net","sig_type","layer")})
        else:
            result.add(row["net"])
    for row in inv.table(directory,"master_geometry"):
        if row["category"] == "PIN" and levels.get(row["layer"],0) in custom:
            forbidden.append({"kind":"MASTER_PIN","master":row["master"],"layer":row["layer"]})
    if forbidden:
        raise ValueError("Migration needs a reviewed PG/pin adapter: "+repr(forbidden[:5]))
    if not result:
        raise ValueError("No reserved-layer ordinary wires to migrate")
    if any(not x or "\n" in x or "\r" in x for x in result):
        raise ValueError("Unsupported net name encoding")
    return sorted(result)

def qualified_reference(directory, case_id, source_odb_hash, tool_hash, targets, custom, phase):
    """Reuse immutable successful evidence; never silently rerun its stages."""
    directory = Path(directory).resolve(strict=True)
    execution = inv.read_json(directory/"execution.json")
    statuses = {
      "prepared":{"pass_fixed_encoding_qualification_only"},
      "routed":{"pass_route_geometry_and_target_connectivity_checks_pending"}}
    if execution.get("status") not in statuses[phase] or execution.get("case") != case_id:
        raise ValueError("Reference is not a qualified "+phase+" run")
    if execution["tools"]["openroad"]["sha256"] != tool_hash:
        raise ValueError("Reference used another OpenROAD binary")
    if execution["inputs"]["odb"]["sha256"] != source_odb_hash:
        raise ValueError("Reference used another original ODB")
    selection = inv.read_json(directory/"targets.json")
    if selection["nets"] != targets or set(selection["custom_routing_levels"]) != set(custom):
        raise ValueError("Reference selected different nets/layers")
    if phase == "prepared":
        comparison = inv.read_json(directory/"prepare_comparison.json")
        required = ["targets.json","prepare_comparison.json","import_fixed/prepared.odb"]
        native_dir = directory/"prepared_inventory/native"
        odb = directory/"import_fixed/prepared.odb"
    else:
        comparison = inv.read_json(directory/"route_comparison.json")
        required = ["targets.json","route_comparison.json","route_target_geometry.json",
                    "upper_layer_check.json","route/migrated.odb"]
        native_dir = directory/"routed_inventory/native"
        odb = directory/"route/migrated.odb"
        geometry_report = inv.read_json(directory/"route_target_geometry.json")
        occupancy = inv.read_json(directory/"upper_layer_check.json")
        if geometry_report.get("status") != "pass_target_geometry" or set(geometry_report["targets"]) != set(targets):
            raise ValueError("Reference has no qualified target geometry")
        if occupancy["electrical_geometry_boxes"] or occupancy["master_pin_shape_instances"]:
            raise ValueError("Reference contains reserved-layer electrical geometry")
    if comparison["status"] != "pass" or comparison["forbidden_changes"]:
        raise ValueError("Reference physical freeze comparison failed")
    files = list(native_dir.glob("*.tsv.gz"))
    if not files:raise ValueError("Reference native inventory missing")
    required.extend(str(p.relative_to(directory)) for p in files)
    for name in required:
        expected = execution["artifacts"].get(name)
        if not expected or inv.digest(directory/name) != expected["sha256"]:
            raise ValueError("Reference evidence changed: "+name)
    return odb,{"execution":inv.source_record(directory/"execution.json"),
                "database":inv.source_record(odb),"verified_artifact_count":len(required),
                "phase":phase,"source_stages_reused":True}


def run(args):
    cfg = inv.read_json(args.config)
    case = next(x for x in cfg["cases"] if x["id"] == args.case and x["role"] == "primary")
    custom = set(map(int,cfg["custom_routing_levels"]))
    if not custom or min(custom) < 2:
        raise ValueError("Invalid custom routing levels")
    output = inv.safe_new(args.output)
    record = {"started_utc":inv.utc(),"status":"running","case":case["id"],"stages":[],
              "scope":"Selective routing qualification; not a full frozen common base",
              "scheduler_job_id":os.getenv("SLURM_JOB_ID",os.getenv("TASK_JOB_ID")),
              "stop_after":args.stop_after,"source_inputs_read_only":True}
    try:
        if not record["scheduler_job_id"]:
            raise RuntimeError("Scheduler allocation required")
        tool = shutil.which("openroad")
        if not tool:
            raise RuntimeError("OpenROAD unavailable")
        before = Path(args.inventory).resolve(strict=True)
        if before.name != "native":
            raise ValueError("--inventory must point to native inventory directory")
        # Consume only the reviewed, immutable input inventory for exactly this ODB.
        execution = inv.read_json(before.parent/"execution.json")
        src = execution["inputs"]["odb"]
        if Path(src["realpath"]) != Path(case["inputs"]["odb"]).resolve(strict=True):
            raise ValueError("Inventory is for another database")
        if inv.digest(case["inputs"]["odb"]) != src["sha256"]:
            raise ValueError("Database differs from inventory")
        inv.write_json(output/"source_review.json",review.review(before))
        record["tools"] = {"openroad":inv.source_record(tool),
                           "version":subprocess.check_output([tool,"-version"],text=True).strip(),
                           "python":sys.version}
        record["inputs"] = {key:inv.source_record(path) for key,path in
                            dict(config=args.config,odb=case["inputs"]["odb"],sdc=case["inputs"]["sdc"],
                                 **cfg["technology_inputs"]).items()}
        record["code"] = {name:inv.source_record(Path(__file__).with_name(name)) for name in
                          ("migrate.py","migrate.tcl","native_inventory.py","native_inventory.tcl","native_review.py","native_geometry.py")}
        record["code"]["geometry_primitives"] = inv.source_record(Path(__file__).parent/"_vendor/pr45_geometry_core.py")
        targets = choose_targets(before,custom)
        if args.stop_after != "prepare":
            if not args.baseline_geometry:
                raise ValueError("--baseline-geometry is required to reuse original target proof")
            baseline = inv.read_json(args.baseline_geometry)
            if baseline.get("status") != "pass_target_geometry" or set(baseline["targets"]) != set(targets):
                raise ValueError("Original target geometry proof is missing/for different nets")
            if baseline["evidence"]["manifest"]["sha256"] != inv.digest(before.parent/"execution.json"):
                raise ValueError("Original geometry proof is for different inventory evidence")
            record["original_target_geometry"] = inv.source_record(args.baseline_geometry)
        inv.write_json(output/"targets.json",{"nets":targets,"custom_routing_levels":sorted(custom),
                       "selection":"Actual ordinary conductor/via-landing occupancy; excludes OBS",
                       "allowance":"Only these complete ordinary wires may change, including their low layers"})
        (output/"targets.txt").write_text("\n".join(targets)+"\n")
        layers = {int(r["routing_level"]):r["name"] for r in inv.table(before,"layers") if int(r["routing_level"])>0}
        top = min(custom)-1
        if not 1 <= args.signal_bottom <= top or not 1 <= args.clock_bottom <= top:
            raise ValueError("Routing bottom outside fixed stack")
        env = dict(os.environ,HPY_MIG_ODB=case["inputs"]["odb"],HPY_MIG_TARGETS=str(output/"targets.txt"),
                   HPY_MIG_LIBERTY=cfg["technology_inputs"]["cell_liberty"],HPY_MIG_SDC=case["inputs"]["sdc"],
                   HPY_MIG_WIRE_RC=cfg["technology_inputs"]["wire_rc"],HPY_MIG_RC_RULES=cfg["technology_inputs"]["rc_rules"],
                   HPY_MIG_SIGNAL_RANGE=layers[args.signal_bottom]+"-"+layers[top],
                   HPY_MIG_CLOCK_RANGE=layers[args.clock_bottom]+"-"+layers[top],
                   HPY_MIG_DRT_ITERS=str(args.drt_iters),PYTHONDONTWRITEBYTECODE="1")
        if args.routed_run:
            migrated_odb, proof = qualified_reference(args.routed_run,case["id"],src["sha256"],
                                record["tools"]["openroad"]["sha256"],targets,custom,"routed")
            record["routed_reference"] = proof
        else:
            if args.prepared_run:
                prepared_odb, proof = qualified_reference(args.prepared_run,case["id"],src["sha256"],
                                  record["tools"]["openroad"]["sha256"],targets,custom,"prepared")
                record["prepared_reference"] = proof
            else:
                marked = stage(output,"mark_def",env,tool,record)
                filtered = output/"fixed_nets_only.def"
                record["native_def_net_records"] = nets_only_def(marked/"marked.def",filtered)
                env["HPY_MIG_FIXED_DEF"] = str(filtered)
                prepared = stage(output,"import_fixed",env,tool,record)
                prepared_odb = prepared/"prepared.odb"
                prep_native,_ = native(output,"prepared_inventory",prepared_odb,env,tool,record,custom)
                comp = compare(before,prep_native,targets,False)
                inv.write_json(output/"prepare_comparison.json",comp)
                if comp["status"] != "pass":
                    raise RuntimeError("Native DEF FIXED conversion changed physical input")
            record["status"] = "pass_fixed_encoding_qualification_only"
            if args.stop_after == "prepare":
                return
            env["HPY_MIG_ODB"] = str(prepared_odb)
            routed = stage(output,"route",env,tool,record)
            migrated_odb = routed/"migrated.odb"
            after,summary = native(output,"routed_inventory",migrated_odb,env,tool,record,custom)
            comp = compare(before,after,targets,True)
            inv.write_json(output/"route_comparison.json",comp)
            inv.write_json(output/"upper_layer_check.json",summary["upper_layer_occupancy"])
            if comp["status"] != "pass":
                raise RuntimeError("Forbidden physical changes detected after routing")
            occ = summary["upper_layer_occupancy"]
            if occ["electrical_geometry_boxes"] or occ["master_pin_shape_instances"]:
                raise RuntimeError("Reserved layers still contain conductor/pin geometry")
            target_geometry = geometry.analyze(after,set(targets))
            inv.write_json(output/"route_target_geometry.json",target_geometry)
            if target_geometry["status"] != "pass_target_geometry":
                raise RuntimeError("Routed target opens/contacts detected")
            record["status"] = "pass_route_geometry_and_target_connectivity_checks_pending"
            if args.stop_after == "route":
                return
        # Independent fresh reads, same extraction rules and constraints.
        # Preserve errors as separate statuses and attempt other independent checks.
        for variant,odb in (("original",case["inputs"]["odb"]),("migrated",str(migrated_odb))):
            checkenv = dict(env,HPY_MIG_ODB=odb)
            for check in ("drc","rc_sta"):
                try:
                    stage(output,check+"__"+variant,checkenv,tool,record)
                except Exception as exc:
                    record.setdefault("check_errors",[]).append({"check":check,"variant":variant,"error":str(exc)})
        record["status"] = "route_geometry_qualified_reports_require_review"
        if record.get("check_errors"):
            record["status"] = "route_geometry_qualified_some_checks_failed"
    except Exception as exc:
        record["status"] = "fail"
        record["error"] = type(exc).__name__+": "+str(exc)
        raise
    finally:
        record["finished_utc"] = inv.utc()
        record["artifacts"] = {str(p.relative_to(output)):inv.source_record(p) for p in output.rglob("*") if p.is_file()}
        inv.write_json(output/"execution.json",record)
        print(json.dumps({"status":record["status"],"output":str(output)}))

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--config",required=True)
    p.add_argument("--case",required=True)
    p.add_argument("--inventory",required=True)
    p.add_argument("--output",required=True)
    reuse = p.add_mutually_exclusive_group()
    reuse.add_argument("--prepared-run",help="Reuse a qualified immutable preparation run")
    reuse.add_argument("--routed-run",help="Reuse a qualified routed run for independent checks")
    p.add_argument("--baseline-geometry",help="Successful original target geometry JSON to reuse")
    p.add_argument("--stop-after",choices=("prepare","route","checks"),default="prepare")
    p.add_argument("--signal-bottom",type=int,default=2)
    p.add_argument("--clock-bottom",type=int,default=4)
    p.add_argument("--drt-iters",type=int,default=32)
    args=p.parse_args()
    if not 1<=args.drt_iters<=64:
        p.error("--drt-iters must be in 1..64")
    if args.prepared_run and args.stop_after == "prepare":
        p.error("--prepared-run is for routing, not repeating preparation")
    if args.routed_run and args.stop_after != "checks":
        p.error("--routed-run requires --stop-after checks")
    run(args)
if __name__=="__main__":
    main()
