"""Native target-net connectivity and target-vs-all conductor contact checks.

Reuses PR45 rectangle/contact graph primitives (pinned source provenance below).
Uses native dbWire/special-wire boxes and transformed master pin shapes, without
DEF parsing. OBS is excluded. Checks every target against ALL other-net wires,
patches, via cuts/landings, PG and connected/unconnected cell/block pins.
This is conservative geometric evidence, not foundry DRC/LVS/formal equivalence.
"""
import argparse
import collections
import importlib.util
import json
import math
import os
from pathlib import Path
import sys

def load_module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
HERE=Path(__file__).parent
inv=load_module("hpy_geometry_inventory",HERE/"native_inventory.py")
review=load_module("hpy_geometry_review",HERE/"native_review.py")
geom=load_module("hpy_pr45_geometry",HERE/"_vendor/pr45_geometry_core.py")
PROVENANCE={
 "repository":"rayggxia-workspace/LLMHardwareDesign",
 "pull_request":45,
 "commit":"a17a0b61b68fce06e318054aad053ed669c048a5",
 "source_path":"project/experiments/frozen_control_cones/geometry_reference.py",
 "source_sha256":"9cd4d899366c8dd7870ae8cf4232c55e5787fc59d3d1e6130543e8c118e62faa",
 "reuse":"touches, conductive, contained and contact_graph are verbatim; native-table adapter and target-vs-all spatial search are new",
 "changes":"Via cut links are formed per cut and its containing landings, without merging disconnected via islands."}

def label(parts):
    return json.dumps(parts,ensure_ascii=False,separators=(",",":"))

def make_node(layer,box,net,kind,terminal=None,layer_type="ROUTING"):
    box=tuple(box)
    if box[0]>=box[2] or box[1]>=box[3]:
        raise ValueError("Zero/negative area electrical shape: "+str((layer,box,net,kind)))
    return {"layer":layer,"box":box,"net":net,"kind":kind,"terminal":terminal,"layer_type":layer_type}

def verify_manifest(directory,manifest):
    directory=Path(directory).resolve(strict=True)
    manifest=Path(manifest).resolve(strict=True)
    data=inv.read_json(manifest)
    count=0
    for path in sorted(directory.glob("*.tsv.gz")):
        key=str(path.relative_to(manifest.parent))
        entry=data["artifacts"].get(key)
        if not entry or inv.digest(path)!=entry["sha256"]:
            raise ValueError("Inventory evidence differs from manifest: "+key)
        count+=1
    if not count:raise ValueError("No native tables")
    return {"manifest":inv.source_record(manifest),"verified_native_tables":count}

def build_nodes(directory,targets):
    """Return complete electrical neighbor geometry and target endpoint labels."""
    instances={r["name"]:r for r in inv.table(directory,"instances")}
    layers={r["name"]:r for r in inv.table(directory,"layers")}
    nets={r["net"]:r for r in inv.table(directory,"nets")}
    if not targets or not set(targets)<=nets.keys():
        raise ValueError("Targets absent from native net catalog")
    for net in targets:
        if nets[net]["sig_type"] in ("POWER","GROUND"):
            raise ValueError("Target PG connectivity requires dedicated PG checker")
    expected=collections.defaultdict(set)
    nodes=[]
    via_groups=collections.defaultdict(list)
    synthetic=set()
    def net_key(name,terminal):
        if name:return name
        key="__HPY_UNCONNECTED__/"+terminal
        if key in nets:raise ValueError("Synthetic net identifier collision")
        synthetic.add(key)
        return key
    for port in inv.table(directory,"bterms"):
        if port["net"] in targets:
            expected[port["net"]].add(label(["BTERM",port["term"]]))
    for row in inv.table(directory,"shapes"):
        if row["kind"]=="BLOCK_OBS":continue
        if row["layer"] not in layers or row["layer_type"] not in ("ROUTING","CUT"):
            raise ValueError("Unknown/non-conductive shape layer")
        terminal=label(["BTERM",row["object"]]) if row["kind"]=="BPIN" else None
        net=net_key(row["net"],terminal or label(["SHAPE",row["kind"],row["object"]]))
        node=make_node(row["layer"],review.bbox(row),net,row["kind"],terminal,row["layer_type"])
        idx=len(nodes);nodes.append(node)
        if row["kind"] in ("WIRE_VIA","SPECIAL_VIA"):
            key=(row["kind"],row["net"],row["object"],row["via"],row["via_x"],row["via_y"])
            via_groups[key].append(idx)
    master_pins=collections.defaultdict(list)
    for row in inv.table(directory,"master_geometry"):
        if row["category"]=="PIN":
            if row["layer_type"] not in ("ROUTING","CUT"):
                raise ValueError("Unsupported native master pin layer")
            master_pins[row["master"],row["term"]].append(row)
    term_count=0
    for row in inv.table(directory,"iterms"):
        inst=instances[row["instance"]]
        terminal=label(["ITERM",row["instance"],row["term"]])
        net=net_key(row["net"],terminal)
        if row["net"] in targets:expected[row["net"]].add(terminal)
        boxes=master_pins.get((row["master"],row["term"]))
        if not boxes:raise ValueError("Missing master pin geometry: "+terminal)
        origin=(int(inst["origin_x"]),int(inst["origin_y"]))
        for box in boxes:
            rect=review.transform_box(review.bbox(box),origin,inst["orient"])
            nodes.append(make_node(box["layer"],rect,net,"ITERM_PIN",terminal,box["layer_type"]))
        term_count+=1
    # Link only actual via cuts to the metal landings that enclose each cut.
    # A via with multiple disconnected islands must not connect the islands.
    links=collections.defaultdict(list)
    via_counts=collections.Counter()
    for key,ids in via_groups.items():
        routing=[i for i in ids if nodes[i]["layer_type"]=="ROUTING"]
        cuts=[i for i in ids if nodes[i]["layer_type"]=="CUT"]
        metal_layers={nodes[i]["layer"] for i in routing}
        cut_layers={nodes[i]["layer"] for i in cuts}
        if len(metal_layers)!=2 or len(cut_layers)!=1 or not cuts:
            raise ValueError("Unsupported via stack/layer count: "+str(key))
        levels=sorted(int(layers[x]["routing_level"]) for x in metal_layers)
        if levels[1]!=levels[0]+1:
            raise ValueError("Non-adjacent routing layers in via: "+str(key))
        for cut in cuts:
            containing=[i for i in routing if geom.contained(nodes[cut]["box"],nodes[i]["box"])]
            if {nodes[i]["layer"] for i in containing}!=metal_layers:
                raise ValueError("Via cut lacks complete two-layer containment: "+str(key))
            links[key[1]].append(containing)
        via_counts[key[0]]+=1
    for net in targets:
        wanted=int(nets[net]["iterm_count"])+int(nets[net]["bterm_count"])
        if len(expected[net])!=wanted:
            raise ValueError("Target endpoint count mismatch: "+net)
    return nodes,links,expected,{"native_iterms":term_count,"electrical_nodes":len(nodes),
                "node_kinds":dict(collections.Counter(n["kind"] for n in nodes)),
                "via_instances":dict(via_counts),"unconnected_pin_net_ids":len(synthetic)}

def connectivity(nodes,links,expected,targets):
    bynet=collections.defaultdict(list)
    for i,node in enumerate(nodes):
        if node["net"] in targets and node["layer_type"]=="ROUTING":
            bynet[node["net"]].append(i)
    result=[]
    for net in sorted(targets):
        ids=bynet[net]
        remap={original:local for local,original in enumerate(ids)}
        selected=[nodes[i] for i in ids]
        local_links=[[remap[i] for i in group] for group in links.get(net,[])]
        roots=geom.contact_graph(selected,local_links)
        terminal_roots=collections.defaultdict(set)
        route_roots=set()
        route_boxes=0
        for node,root in zip(selected,roots):
            if node["terminal"] is not None:
                terminal_roots[node["terminal"]].add(root)
            else:
                route_roots.add(root);route_boxes+=1
        missing=sorted(expected[net]-terminal_roots.keys())
        common=None
        for terminal in sorted(expected[net]):
            current=terminal_roots.get(terminal,set())
            common=set(current) if common is None else common&current
        common=common or set()
        floating=route_roots-common
        passed=bool(expected[net]) and not missing and bool(common) and not floating
        result.append({"net":net,"passed":passed,"expected_endpoints":len(expected[net]),
                       "route_rectangles":route_boxes,"common_components":len(common),
                       "missing_endpoint_geometry":missing,"floating_route_components":len(floating),
                       "endpoint_component_count":{name:len(r) for name,r in sorted(terminal_roots.items())}})
    return result

def bins(box,size):
    x0,y0,x1,y1=box
    # Include upper boundary bins to catch exact touching at a grid boundary.
    for x in range(x0//size,x1//size+1):
        for y in range(y0//size,y1//size+1):
            yield x,y

def target_contacts(nodes,targets,bin_dbu=8000,max_comparisons=100_000_000,max_examples=100):
    if bin_dbu<=0:raise ValueError("Spatial bin must be positive")
    index=collections.defaultdict(list)
    for i,node in enumerate(nodes):
        for x,y in bins(node["box"],bin_dbu):
            index[node["layer"],x,y].append(i)
    total=0;examples=[];comparisons=0
    bytypes=collections.Counter()
    for i,node in enumerate(nodes):
        if node["net"] not in targets:continue
        candidates=set()
        for x,y in bins(node["box"],bin_dbu):
            candidates.update(index[node["layer"],x,y])
        for j in sorted(candidates):
            other=nodes[j]
            if node["net"]==other["net"]:continue
            if other["net"] in targets and j<i:continue
            comparisons+=1
            if comparisons>max_comparisons:
                raise RuntimeError("Short check incomplete: candidate comparison budget exhausted")
            if geom.touches(node["box"],other["box"]):
                total+=1
                bytypes[node["kind"]+"/"+other["kind"]]+=1
                if len(examples)<max_examples:
                    examples.append({"layer":node["layer"],"net_a":node["net"],"net_b":other["net"],
                                     "box_a":node["box"],"box_b":other["box"],
                                     "kind_a":node["kind"],"kind_b":other["kind"],
                                     "terminal_a":node["terminal"],"terminal_b":other["terminal"]})
    return {"count":total,"first_examples":examples,"contact_kind_pairs":dict(bytypes),
            "candidate_comparisons":comparisons,"spatial_bin_dbu":bin_dbu,"all_neighbors_indexed":len(nodes),
            "scope":"Every target conductor and terminal vs all other-net conductor/terminal shapes, including PG, cut layers and unconnected pins; unrelated non-target-to-non-target contacts excluded.",
            "corner_policy":"Any corner/edge/area touch between different nets is conservatively reported."}

def analyze(directory,targets,bin_dbu=8000,max_comparisons=100_000_000):
    consistency=review.review(directory,verify_hashes=False)
    nodes,links,expected,counts=build_nodes(directory,set(targets))
    net_results=connectivity(nodes,links,expected,set(targets))
    contacts=target_contacts(nodes,set(targets),bin_dbu,max_comparisons)
    passed=all(x["passed"] for x in net_results) and contacts["count"]==0
    return {"status":"pass_target_geometry" if passed else "fail_target_geometry",
            "targets":sorted(targets),"nets":net_results,"different_net_contacts":contacts,
            "counts":counts,"inventory_consistency":consistency,"source_method":PROVENANCE,
            "limitations":[
              "Connectivity is proved only for the explicitly selected nets; global source netlist/RTL equivalence is separate.",
              "All neighboring native electrical shapes are considered for target contacts; non-target-to-non-target shorts are outside this incremental check.",
              "Same-pin disconnected access shapes are not automatically joined through hidden cell-internal metal.",
              "Same-layer connectivity needs positive-area or positive-length edge contact; corner-only contact does not connect.",
              "Via cuts require nonzero area and zero-margin enclosure by both adjacent landings; full enclosure/spacing rules require DRC.",
              "OBS is not counted as conductor; placement/OBS and minimum spacing checks remain separate.",
              "PG current capacity, analog behavior, transistor-level LVS, extracted timing and foundry signoff are not established."]}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input",required=True)
    p.add_argument("--manifest",required=True)
    p.add_argument("--targets",required=True,help="JSON containing a nets string list")
    p.add_argument("--output",required=True,help="New output JSON file")
    p.add_argument("--spatial-bin-um",type=float,default=4)
    p.add_argument("--max-comparisons",type=int,default=100_000_000)
    a=p.parse_args()
    output=Path(a.output).absolute()
    allowed=Path("/public/home/yuzelu/PingyangHuang").resolve(strict=True)
    parent=output.parent.resolve(strict=True)
    if allowed not in (parent,*parent.parents):raise ValueError("Output outside permitted directory")
    if output.exists() or output.is_symlink():raise FileExistsError(output)
    result={"status":"fail"}
    try:
        if not os.getenv("SLURM_JOB_ID",os.getenv("TASK_JOB_ID")):
            raise RuntimeError("Native geometry check requires a scheduler allocation")
        evidence=verify_manifest(a.input,a.manifest)
        meta={r["key"]:r["value"] for r in inv.table(a.input,"metadata")}
        dbu=int(meta["dbu_per_um"])
        if not math.isfinite(a.spatial_bin_um) or a.spatial_bin_um<=0:
            raise ValueError("Invalid spatial bin")
        targets=inv.read_json(a.targets)["nets"]
        if len(targets)!=len(set(targets)):raise ValueError("Duplicate target names")
        result=analyze(a.input,targets,max(1,round(a.spatial_bin_um*dbu)),a.max_comparisons)
        result["evidence"]=evidence
        result["targets_source"]=inv.source_record(a.targets)
        result["code"]={str(path.relative_to(HERE)):inv.source_record(path) for path in
                         (Path(__file__),HERE/"_vendor/pr45_geometry_core.py",HERE/"native_inventory.py",HERE/"native_review.py")}
    except Exception as exc:
        result["error"]=type(exc).__name__+": "+str(exc)
    inv.write_json(output,result)
    print(json.dumps({"status":result["status"],"output":str(output)}))
    return 0 if result["status"]=="pass_target_geometry" else 1
if __name__=="__main__":raise SystemExit(main())
