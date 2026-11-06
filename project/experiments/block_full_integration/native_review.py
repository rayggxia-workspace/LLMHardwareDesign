"""Independent consistency review of native inventory tables, not signoff."""
import argparse
import collections
import importlib.util
import json
from pathlib import Path
import sys

_spec = importlib.util.spec_from_file_location("hpy_native_inventory", Path(__file__).with_name("native_inventory.py"))
inv = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(inv)

def fail(message):
    raise ValueError(message)

def unique(rows, key, label):
    result = {}
    for row in rows:
        name = key(row)
        if name in result:
            fail("Duplicate "+label+": "+str(name))
        result[name] = row
    return result

def bbox(row):
    return tuple(int(row[k]) for k in ("x0","y0","x1","y1"))

def transform_box(box, origin, orient):
    transforms = {
        "R0":lambda x,y:(x,y), "R90":lambda x,y:(-y,x),
        "R180":lambda x,y:(-x,-y), "R270":lambda x,y:(y,-x),
        "MX":lambda x,y:(x,-y), "MY":lambda x,y:(-x,y),
        "MXR90":lambda x,y:(y,x), "MYR90":lambda x,y:(-y,-x)}
    if orient not in transforms:
        fail("Unsupported orientation: "+orient)
    fn = transforms[orient]
    x0,y0,x1,y1 = box
    points = [(x+origin[0],y+origin[1]) for x,y in
              (fn(x0,y0),fn(x0,y1),fn(x1,y0),fn(x1,y1))]
    return min(p[0] for p in points),min(p[1] for p in points),max(p[0] for p in points),max(p[1] for p in points)

def union_box(boxes):
    return min(b[0] for b in boxes),min(b[1] for b in boxes),max(b[2] for b in boxes),max(b[3] for b in boxes)

def review(directory, verify_hashes=True):
    directory = Path(directory)
    verified = 0
    if verify_hashes:
        execution = inv.read_json(directory.parent/"execution.json")
        if execution["status"] != "pass_inventory_only":
            fail("Source execution not successful")
        for path in directory.glob("*.tsv.gz"):
            key = str(path.relative_to(directory.parent))
            expected = execution["artifacts"].get(key)
            if not expected or inv.digest(path) != expected["sha256"]:
                fail("Changed/unrecorded native evidence: "+key)
            verified += 1
    instances = unique(inv.table(directory,"instances"),lambda x:x["name"],"instance")
    masters = unique(inv.table(directory,"masters"),lambda x:x["master"],"master")
    nets = unique(inv.table(directory,"nets"),lambda x:x["net"],"net")
    ports = unique(inv.table(directory,"bterms"),lambda x:x["term"],"BTerm")
    meta = {r["key"]:r["value"] for r in inv.table(directory,"metadata")}
    if meta.get("complete") != "true":
        fail("Missing native complete marker")
    if len(instances) != int(meta["instance_count"]) or len(nets) != int(meta["net_count"]):
        fail("Missing instance/net row")
    geometry = collections.defaultdict(list)
    terms = collections.defaultdict(set)
    for row in inv.table(directory,"master_geometry"):
        if row["category"] == "PIN":
            geometry[row["master"],row["term"]].append(bbox(row))
            terms[row["master"]].add(row["term"])
    orientations = collections.Counter()
    endpoint_counts = collections.Counter()
    actual_terms = collections.defaultdict(set)
    unconnected = collections.Counter()
    unconnected_samples = []
    iterm_count = 0
    for term in inv.table(directory,"iterms"):
        iterm_count += 1
        instance = instances.get(term["instance"])
        if instance is None or instance["master"] != term["master"]:
            fail("ITerm instance/master mismatch")
        if term["term"] in actual_terms[term["instance"]]:
            fail("Duplicate ITerm: "+term["instance"]+"/"+term["term"])
        actual_terms[term["instance"]].add(term["term"])
        local = geometry.get((term["master"],term["term"]))
        if not local:
            fail("Missing master pin geometry: "+term["master"]+"/"+term["term"])
        try:
            origin = int(instance["origin_x"]),int(instance["origin_y"])
        except ValueError:
            fail("Native instance origin unavailable")
        expected = union_box([transform_box(b,origin,instance["orient"]) for b in local])
        if bbox(term) != expected:
            fail("Transformed pin bbox mismatch: "+term["instance"]+"/"+term["term"])
        orientations[instance["orient"]] += 1
        if term["net"]:
            if term["net"] not in nets:
                fail("ITerm refers to missing net")
            endpoint_counts[term["net"]] += 1
        else:
            key = term["io_type"],term["sig_type"],term["master"]
            unconnected[key] += 1
            if len(unconnected_samples) < 20:
                unconnected_samples.append({k:term[k] for k in ("instance","master","term","io_type","sig_type")})
    for name,instance in instances.items():
        if instance["master"] not in masters:
            fail("Missing master definition")
        if actual_terms[name] != terms[instance["master"]]:
            fail("Missing/extra ITerm including unconnected pins: "+name)
    port_counts = collections.Counter()
    for port in ports.values():
        if port["net"]:
            if port["net"] not in nets:
                fail("BTerm refers to missing net")
            port_counts[port["net"]] += 1
    for name,net in nets.items():
        if endpoint_counts[name] != int(net["iterm_count"]) or port_counts[name] != int(net["bterm_count"]):
            fail("Endpoint count mismatch on net: "+name)
    definitions = collections.defaultdict(collections.Counter)
    scope = {}
    for row in inv.table(directory,"via_definitions"):
        name = row["name"]
        if name in scope and scope[name] != row["scope"]:
            fail("Ambiguous via name across scopes: "+name)
        scope[name] = row["scope"]
        definitions[name][(row["layer"],row["layer_type"],*bbox(row))] += 1
    shape_counts = collections.Counter()
    via_instances = collections.Counter()
    observed = collections.Counter()
    current = None
    bpin_names = set()
    def close_via(key):
        if key is None:
            return
        name = key[3]
        if name not in definitions or observed != definitions[name]:
            fail("Via boxes do not match complete definition: "+str(key))
        via_instances[key[0]] += 1
    for row in inv.table(directory,"shapes"):
        shape_counts[row["kind"],row["sig_type"],row["layer"],row["layer_type"]] += 1
        b = bbox(row)
        if b[0] > b[2] or b[1] > b[3]:
            fail("Inverted rectangle")
        if row["kind"] == "BPIN":
            port = ports.get(row["object"])
            if port is None or port["net"] != row["net"] or port["sig_type"] != row["sig_type"]:
                fail("BPin port/net/type mismatch")
            bpin_names.add(row["object"])
        if row["kind"] in ("WIRE_VIA","SPECIAL_VIA"):
            key = row["kind"],row["net"],row["object"],row["via"],row["via_x"],row["via_y"]
            if key != current:
                close_via(current)
                current = key
                observed = collections.Counter()
            x,y = int(row["via_x"]),int(row["via_y"])
            observed[row["layer"],row["layer_type"],b[0]-x,b[1]-y,b[2]-x,b[3]-y] += 1
        else:
            close_via(current)
            current = None
            observed = collections.Counter()
    close_via(current)
    expected = {(r["kind"],r["sig_type"],r["layer"],r["layer_type"]):int(r["count"])
                for r in inv.table(directory,"shape_counts")}
    if shape_counts != expected:
        fail("Missing/extra shape row")
    for name,port in ports.items():
        if int(port["pin_count"]) > 0 and name not in bpin_names:
            fail("BTerm reports physical pin but shape is missing: "+name)
    return {"status":"pass_inventory_consistency_only","verified_source_files":verified,
            "source_native_directory":str(directory),"instance_count":len(instances),"iterm_count":iterm_count,
            "transformed_pin_bbox_checks":iterm_count,"orientation_coverage":dict(orientations),
            "complete_via_instance_checks":dict(via_instances),"endpoint_counts_consistent":True,
            "unconnected_iterms":[{"direction":k[0],"signal_type":k[1],"master":k[2],"count":v}
                                  for k,v in sorted(unconnected.items())],
            "unconnected_samples":unconnected_samples,
            "unconnected_inputs":sum(v for k,v in unconnected.items() if k[0]=="INPUT"),
            "unconnected_power_ground":sum(v for k,v in unconnected.items() if k[1] in ("POWER","GROUND")),
            "limitations":[
              "Checks internal consistency of native tables, not physical electrical connectivity.",
              "Logical endpoint presence does not prove routes are continuous or free from shorts.",
              "Bounding-box transform checks do not perform pairwise pin/route DRC.",
              "SDC is captured and hashed by the source run but is not executed by this inventory.",
              "No placement nonoverlap, source equivalence, PG current, RC extraction, or STA claim."]}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input",required=True)
    parser.add_argument("--output",required=True)
    args = parser.parse_args()
    output = Path(args.output).absolute()
    allowed = Path("/public/home/yuzelu/PingyangHuang").resolve(strict=True)
    if allowed not in (output.parent.resolve(strict=True),*output.parent.resolve(strict=True).parents):
        fail("Output outside permitted directory")
    result = {"status":"fail"}
    code = 0
    try:
        result = review(args.input)
    except Exception as exc:
        result["error"] = type(exc).__name__+": "+str(exc)
        code = 1
    inv.write_json(output,result)
    print(json.dumps({"status":result["status"],"output":str(output)}))
    return code

if __name__ == "__main__":
    raise SystemExit(main())
