"""Read-only, fail-closed replay of small combinational native-export evidence.

Not a placer, router, full DRC, sequential simulator or arbitrary Block mapper.
"""
import argparse
import csv
import hashlib
import itertools
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
import geometry_reference as g


class Rejected(ValueError):
    def __init__(self, code, detail):
        self.code = code
        super().__init__(detail)


def require(ok, code, detail):
    if not ok:
        raise Rejected(code, detail)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def rows(path):
    with Path(path).open(encoding="utf-8") as stream:
        return list(csv.DictReader(stream, delimiter="\t"))


def read_native(prefix):
 layers={x['layer']:x for x in rows(Path(str(prefix)+'.layers.tsv'))}
 vias=defaultdict(list)
 for v in rows(Path(str(prefix)+'.vias.tsv')):
  vias[v['via']].append((v['layer'],tuple(int(v[k]) for k in ['x1','y1','x2','y2'])))
 vias={k:sorted(set(v)) for k,v in vias.items()}
 text=Path(str(prefix)+'.odb_export.def').read_text()
 ndrs={}
 if re.search(r'^NONDEFAULTRULES\s',text,re.M):
  for rec in g.records(g.section(text,'NONDEFAULTRULES')):
   ndrs[rec.split()[0]]={l:int(w) for l,w in re.findall(r'\+\s+LAYER\s+(\S+)\s+WIDTH\s+(\d+)',rec)}
 allnodes=[];links=[];cuts=[];viauses=[]
 for sec in ['NETS','SPECIALNETS']:
  for rec in g.records(g.section(text,sec)):
   net=rec.split()[0];ns,lk,used=g.decode_routes(rec,net,layers,vias,ndrs,special=sec=='SPECIALNETS')
   offset=len(allnodes);allnodes+=ns;links += [[offset+i for i in part] for part in lk]
   for route in re.finditer(r'(?:\+\s+(?:ROUTED|FIXED|COVER)|\bNEW)\s+(.*?)(?=\bNEW\b|\+\s+[A-Z]|$)',rec,re.S):
    xy=None
    for token in re.findall(r'\([^)]*\)|[^\s]+',route.group(1)):
     if token.startswith('('):
      v=token[1:-1].split()
      if len(v) in [2,3]:xy=[xy[i] if t=='*' else int(t) for i,t in enumerate(v[:2])]
     elif token in vias:
      viauses.append((net,token,xy[:]))
      for layer,box in vias[token]:
       if layers[layer]['type']=='CUT':cuts.append(dict(net=net,layer=layer,box=[box[0]+xy[0],box[1]+xy[1],box[2]+xy[0],box[3]+xy[1]]))
 for t in rows(Path(str(prefix)+'.terminals.tsv')):
  allnodes.append(g.shape(t['layer'],[int(t[k]) for k in ['x1','y1','x2','y2']],t['net'],'terminal',t['terminal']))
 return layers,vias,allnodes,links,cuts,viauses



def canonical_rows(path, columns=None):
    return sorted(tuple((k, row[k]) for k in (columns or sorted(row)))
                  for row in rows(path))


def check_frozen(base, current, cfg):
    """Compare geometry, not net names: customization may merge named nets."""
    bp, b = base
    cp, c = current
    require(canonical_rows(str(bp)+".instances.tsv") ==
            canonical_rows(str(cp)+".instances.tsv"),
            "FROZEN_INSTANCE", "cell inventory, placement or orientation changed")
    require(canonical_rows(str(bp)+".obstructions.tsv") ==
            canonical_rows(str(cp)+".obstructions.tsv"),
            "FROZEN_OBSTRUCTION", "fixed obstructions changed")
    # Net-name merging is permitted only for signal customization, never PG.
    pg = lambda p: sorted(tuple(sorted(row.items()))
                          for row in rows(str(p)+".terminals.tsv")
                          if row["sigtype"] in ("POWER", "GROUND"))
    require(pg(bp) == pg(cp), "FROZEN_POWER", "PG terminal/net assignment changed")
    pg_shapes = lambda data: Counter((n["net"], n["layer"], tuple(n["box"]), n["kind"])
                                      for n in data[2] if n["net"] in set(cfg["power_nets"]))
    require(pg_shapes(b) == pg_shapes(c), "FROZEN_POWER", "PG geometry changed")
    cols = ["terminal", "layer", "x1", "y1", "x2", "y2", "kind", "sigtype"]
    ext = lambda p: sorted(tuple(row[k] for k in cols)
                          for row in rows(str(p)+".terminals.tsv")
                          if row["kind"] == "BTERM")
    require(ext(bp) == ext(cp), "FROZEN_PORT", "external pin geometry changed")
    for layer in b[0]:
        require(c[0].get(layer) == b[0][layer], "TECH_CHANGED", layer)
    for name in b[1]:
        require(c[1].get(name) == b[1][name], "VIA_CHANGED", name)
    fixed = set(cfg["fixed_layers"])
    custom = set(cfg["custom_layers"])
    lower = lambda data: {(n["layer"], tuple(n["box"]), n["kind"])
                          for n in data[2] if n["layer"] in fixed}
    old, new = lower(b), lower(c)
    require(old <= new, "FROZEN_SHAPE_REMOVED", "lower metal/pin shape removed")
    for layer, box, kind in new-old:
        require(layer == cfg["landing_layer"] and kind == "via" and
                any(n["layer"] == layer and n["kind"] == "wire" and
                    g.contained(box, n["box"]) for n in b[2]),
                "LOWER_FOOTPRINT_ADDED", str((layer, box, kind)))
    require(all(n["layer"] in fixed | custom for n in c[2]),
            "LAYER_FORBIDDEN", "conductor outside allowed layer stack")
    allowed = set(cfg["custom_vias"])
    immutable = lambda data: Counter((name, tuple(xy)) for _, name, xy in data[5]
                                     if name not in allowed)
    require(immutable(b) == immutable(c), "FROZEN_VIA", "fixed via use changed")
    for _, name, _ in c[5]:
        if name in allowed:
            expected = set(cfg["custom_vias"][name])
            actual = {layer for layer, _ in c[1][name]
                      if c[0][layer]["type"] == "ROUTING"}
            require(actual == expected, "VIA_STACK", name)
    return {"cell_placement_and_inventory": True, "external_pins": True,
            "lower_shapes_retained": True, "lower_additions_contained": True,
            "fixed_vias_retained": True, "technology_unchanged": True}


def check_overlap(prefix, cfg):
    boxes = []
    for row in rows(str(prefix)+".instances.tsv"):
        model = cfg["cells"].get(row["master"])
        require(model is not None and row["orient"] == "R0",
                "UNSUPPORTED_CELL", str(row))
        w, h = model["size_dbu"]
        require(w > 0 and h > 0, "CELL_SIZE", row["master"])
        x, y = int(row["ox"]), int(row["oy"])
        boxes.append((row["instance"], [x, y, x+w, y+h]))
    for (na, a), (nb, b) in itertools.combinations(boxes, 2):
        require(min(a[2], b[2]) <= max(a[0], b[0]) or
                min(a[3], b[3]) <= max(a[1], b[1]),
                "CELL_OVERLAP", na+" / "+nb)
    return {"rectangular_cell_overlap": False, "supported_orientation": "R0",
            "dimension_source": cfg["cell_model_source"]}


def check_basic(data, cfg):
    layers, _, nodes, _, cuts, _ = data
    grid = cfg["manufacturing_grid_dbu"]
    require(type(grid) is int and grid > 0, "GRID_CONFIG", str(grid))
    require(all(v % grid == 0 for n in nodes+cuts for v in n["box"]),
            "OFF_GRID", "route/pin/cut rectangle off manufacturing grid")
    # Deliberately only scalar LEF spacing, not spacing tables/full foundry DRC.
    for a, b in itertools.combinations(nodes, 2):
        if a["layer"] != b["layer"] or a["net"] == b["net"]:
            continue
        req = int(layers[a["layer"]]["spacing"])
        dx = max(a["box"][0]-b["box"][2], b["box"][0]-a["box"][2], 0)
        dy = max(a["box"][1]-b["box"][3], b["box"][1]-a["box"][3], 0)
        require(dx >= req or dy >= req, "MIN_SPACING", str((a["layer"], req)))
    return {"manufacturing_grid": True, "scalar_metal_spacing": True,
            "full_DRC_RC_STA": "NOT_RUN"}


def evaluate(prefix, data, cfg, case):
    _, _, nodes, links, _, _ = data
    count, _ = g.find_shorts(nodes)
    require(count == 0, "SHORT", str(count)+" different-net contacts")
    roots = g.contact_graph(nodes, links)  # global; never group by declared net!
    pins = defaultdict(set)
    for i, node in enumerate(nodes):
        if node["kind"] == "terminal":
            pins[node["label"]].add(roots[i])
    def root(pin):
        require(len(pins[pin]) == 1, "PIN_ACCESS", pin)
        return next(iter(pins[pin]))
    terminal_rows = rows(str(prefix)+".terminals.tsv")
    inputs, outputs = cfg["input_ports"], cfg["output_ports"]
    external = {r["terminal"] for r in terminal_rows
                if r["kind"] == "BTERM" and r["sigtype"] == "SIGNAL"}
    require(external == set(inputs+outputs), "PORT_SCHEMA", str(external))
    instances = rows(str(prefix)+".instances.tsv")
    gates, driver_roots = [], [root(pin) for pin in inputs]
    for row in instances:
        model = cfg["cells"].get(row["master"])
        require(model is not None, "UNSUPPORTED_CELL", row["master"])
        name = row["instance"]
        ins = [root(name+"/"+p) for p in model["inputs"]]
        out = root(name+"/"+model["output"])
        actual = {r["terminal"].split("/", 1)[1] for r in terminal_rows
                  if r["kind"] == "ITERM" and
                  r["terminal"].startswith(name+"/") and r["sigtype"] == "SIGNAL"}
        require(actual == set(model["inputs"]+[model["output"]]),
                "CELL_INTERFACE", name)
        require(len(model["truth_table"]) == 2**len(ins) and
                all(type(v) is int and v in (0, 1) for v in model["truth_table"]),
                "CELL_MODEL", row["master"])
        gates.append((name, ins, out, model["truth_table"]))
        driver_roots.append(out)
    require(len(driver_roots) == len(set(driver_roots)),
            "MULTIPLE_DRIVERS", "two active drivers contact")
    require(all(r in driver_roots for _, ins, _, _ in gates for r in ins),
            "OPEN", "floating cell input")
    require(all(root(p) in driver_roots for p in outputs),
            "OPEN", "floating external output")
    require(type(cfg["maximum_exhaustive_inputs"]) is int and
            0 < cfg["maximum_exhaustive_inputs"] <= 16 and
            len(inputs) <= cfg["maximum_exhaustive_inputs"],
            "ENUMERATION_LIMIT", "use a qualified SAT/sequential backend instead")
    observed = []
    for bits in itertools.product((0, 1), repeat=len(inputs)):
        values = dict(zip((root(p) for p in inputs), bits))
        pending = list(gates)
        while pending:
            remaining = []
            for name, ins, out, table in pending:
                if all(pin in values for pin in ins):
                    index = 0
                    for pin in ins:
                        index = index*2 + values[pin]
                    values[out] = table[index]
                else:
                    remaining.append((name, ins, out, table))
            require(len(remaining) < len(pending), "COMBINATIONAL_CYCLE",
                    "no topological progress")
            pending = remaining
        observed.append([values[root(p)] for p in outputs])
    require(observed == case["expected"], "FUNCTION_MISMATCH",
            json.dumps({"observed": observed, "expected": case["expected"]}))
    return {"observed": observed, "binary_vectors": len(observed),
            "source_net_names_used_for_logic": False,
            "logic_model": "explicit config tables; original Liberty SAT evidence indexed separately"}


def validate(base_prefix, case_prefix, cfg, case):
    try:
        base, current = read_native(base_prefix), read_native(case_prefix)
        freeze = check_frozen((base_prefix, base), (case_prefix, current), cfg)
        overlap = check_overlap(case_prefix, cfg)
        # Faults such as shorts should be diagnosed before scalar spacing.
        functional = evaluate(case_prefix, current, cfg, case)
        basic = check_basic(current, cfg)
        return {"status": "PASS_SCOPED_REPLAY", "freeze": freeze,
                "overlap": overlap, "functional": functional, "basic": basic}
    except Rejected as exc:
        return {"status": "REJECTED", "reason": exc.code, "detail": str(exc)}
    except (ValueError, KeyError, OSError, TypeError, IndexError) as exc:
        return {"status": "REJECTED", "reason": "UNSUPPORTED_OR_INVALID_INPUT",
                "detail": str(exc)}


def run(config, fixture_root=None):
    path = Path(config).resolve()
    cfg = json.loads(path.read_text())
    root = Path(fixture_root).resolve() if fixture_root else (path.parent / cfg["fixture_root"]).resolve()
    require(cfg["schema_version"] == 1, "SCHEMA_VERSION", "only schema 1")
    require(set(cfg["fixed_layers"]).isdisjoint(cfg["custom_layers"]),
            "LAYER_CONFIG", "fixed/custom layer overlap")
    require(len(cfg["input_ports"]) == len(set(cfg["input_ports"])) and
            set(cfg["input_ports"]).isdisjoint(cfg["output_ports"]),
            "PORT_SCHEMA", "duplicate/input-output aliases")
    def prefix(rel):
        p = (root / rel).resolve()
        require(p.is_relative_to(root), "PATH_ESCAPE", rel)
        return p
    result = {"scope": "small, scalar, combinational native-export replay",
              "config_sha256": digest(path), "cases": {}}
    for case in cfg["cases"]:
        name = case["id"]
        require(name not in result["cases"], "DUPLICATE_CASE", name)
        result["cases"][name] = validate(prefix(cfg["base_prefix"]),
                                         prefix(case["prefix"]), cfg, case)
    result["passed"] = bool(result["cases"]) and all(
        r["status"] == "PASS_SCOPED_REPLAY" for r in result["cases"].values())
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    parser.add_argument("--fixture-root")
    parser.add_argument("--out", required=True,
                        help="new directory; existing directories are never overwritten")
    args = parser.parse_args()
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=False)
    try:
        result = run(args.config, args.fixture_root)
    except (Rejected, ValueError, OSError) as exc:
        result = {"passed": False, "error": str(exc)}
    with (out/"replay.json").open("x") as stream:
        json.dump(result, stream, indent=2); stream.write("\n")
    print(json.dumps(result))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
