#!/usr/bin/env python3
"""Conservative geometry graph of actual ODB-exported DEF signal wiring.
No routing/sizing/mutation. Unsupported DEF constructs fail closed.
This is not foundry DRC, LVS or timing signoff.
"""
import argparse,csv,json,re,hashlib
from collections import defaultdict
from pathlib import Path

def rows(p):
    with p.open(encoding="utf-8") as f:return list(csv.DictReader(f,delimiter="\t"))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def touches(a,b):
    return max(a[0],b[0])<=min(a[2],b[2]) and max(a[1],b[1])<=min(a[3],b[3])
def conductive(a,b):
    dx=min(a[2],b[2])-max(a[0],b[0]);dy=min(a[3],b[3])-max(a[1],b[1])
    return dx>=0 and dy>=0 and (dx>0 or dy>0)
def contained(a,b):return a[0]>=b[0] and a[1]>=b[1] and a[2]<=b[2] and a[3]<=b[3]
def segment(p,q,width):
    x,y,e=p;u,v,f=q
    h=width//2
    if width<=0 or width%2:raise ValueError("unsupported nonpositive/odd DBU width")
    e=h if e is None else e;f=h if f is None else f
    if x==u:
        if y<=v:return [x-h,y-e,x+h,v+f]
        return [x-h,v-f,x+h,y+e]
    if y==v:
        if x<=u:return [x-e,y-h,u+f,y+h]
        return [u-f,y-h,x+e,y+h]
    raise ValueError("non-Manhattan segment")
def section(text,name):
    m=re.search(r"^"+name+r"\s+\d+\s*;(.*?)^END\s+"+name+r"\s*$",text,re.M|re.S)
    if not m:raise ValueError("Missing DEF section "+name)
    return m.group(1)
def records(text):
    return re.findall(r"(?:^|\n)\s*-\s+(.*?);",text,re.S)
def shape(layer,box,net,kind,label):
    if len(box)!=4 or box[0]>box[2] or box[1]>box[3]:raise ValueError("bad rectangle")
    return {"layer":layer,"box":box,"net":net,"kind":kind,"label":label}

def decode_routes(body,net,layers,vias,ndrs=None,special=False):
    nodes=[];vlinks=[];used=[]
    ndrs=ndrs or {}
    nm=re.search(r"\+\s+NONDEFAULTRULE\s+(\S+)",body)
    rule=nm.group(1) if nm else None
    if rule and rule not in ndrs:raise ValueError("Unknown NONDEFAULTRULE "+rule)
    rule_widths=ndrs.get(rule,{})
    body=re.sub(r"\+\s+SHAPE\s+[A-Z_]+", "", body)
    routes=list(re.finditer(r"(?:\+\s+(?:ROUTED|FIXED|COVER)|\bNEW)\s+(.*?)(?=\bNEW\b|\+\s+[A-Z]|$)",body,re.S))
    for ri,route in enumerate(routes):
        tok=re.findall(r"\([^)]*\)|[^\s]+",route.group(1).strip())
        if not tok:raise ValueError("empty route")
        layer=tok[0]
        if layer not in layers or layers[layer]["type"]!="ROUTING":raise ValueError("unknown route layer "+layer)
        width=rule_widths.get(layer,int(layers[layer]["width"]));i=1;prev=None;taper=False
        # Explicit width belongs to SPECIALNETS, rejected in signal NETS unless positive.
        if i<len(tok) and re.fullmatch(r"\d+",tok[i]):width=int(tok[i]);i+=1
        while i<len(tok):
            t=tok[i]
            if t.startswith("("):
                coords=t[1:-1].split()
                if len(coords) not in (2,3):raise ValueError("unsupported point "+t)
                xy=[]
                for k,z in enumerate(coords[:2]):
                    if z=="*":
                        if prev is None:raise ValueError("star at first point")
                        xy.append(prev[k])
                    else:xy.append(int(z))
                point=xy+[int(coords[2]) if len(coords)==3 else (0 if special else None)]
                if prev is not None:
                    nodes.append(shape(layer,segment(prev,point,width),net,"wire",str(ri)))
                prev=point;i+=1
            elif t in vias:
                if prev is None:raise ValueError("via before point")
                group=[];rl=[]
                cutboxes=[b for l,b in vias[t] if layers.get(l,{}).get("type")=="CUT"]
                metalboxes=defaultdict(list)
                for l,b in vias[t]:
                    if layers.get(l,{}).get("type")=="ROUTING":metalboxes[l].append(b)
                if len(metalboxes)!=2 or not cutboxes:raise ValueError("via lacks two routing layers and real cut geometry "+t)
                for cut in cutboxes:
                    if cut[0]>=cut[2] or cut[1]>=cut[3]:raise ValueError("zero-area via cut "+t)
                    if any(not any(contained(cut,b) for b in boxes) for boxes in metalboxes.values()):
                        raise ValueError("via cut not contained in each routing metal "+t)
                for lay,box in vias[t]:
                    if lay not in layers:raise ValueError("via unknown layer")
                    if layers[lay]["type"]!="ROUTING":continue
                    q=[box[0]+prev[0],box[1]+prev[1],box[2]+prev[0],box[3]+prev[1]]
                    group.append(len(nodes));rl.append(lay)
                    nodes.append(shape(lay,q,net,"via",t))
                if len(set(rl))!=2:raise ValueError("unsupported non-two-metal via "+t)
                vlinks.append(group);used.append(t)
                if layer not in rl:raise ValueError("via disconnected from current layer "+t)
                layer=next(x for x in rl if x!=layer)
                width=int(layers[layer]["width"]) if taper else rule_widths.get(layer,int(layers[layer]["width"]));i+=1
            elif t=="TAPER":
                if prev is not None:raise ValueError("TAPER after route point")
                taper=True;width=int(layers[layer]["width"]);i+=1
            elif t=="RECT":
                if prev is None or i+1>=len(tok):raise ValueError("RECT without anchor")
                z=tok[i+1]
                if not z.startswith("("):raise ValueError("bad RECT")
                b=[int(x) for x in z[1:-1].split()]
                if len(b)!=4:raise ValueError("bad RECT count")
                b=[b[0]+prev[0],b[1]+prev[1],b[2]+prev[0],b[3]+prev[1]]
                nodes.append(shape(layer,b,net,"patch",str(ri)));i+=2
            else:
                raise ValueError("Unsupported DEF route token "+t+" in net "+net)
    return nodes,vlinks,sorted(set(used))

def contact_graph(nodes,vlinks):
    parent=list(range(len(nodes)))
    def find(i):
        while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
        return i
    def union(a,b):
        a,b=find(a),find(b)
        if a!=b:parent[b]=a
    for group in vlinks:
        for x in group[1:]:union(group[0],x)
    byl=defaultdict(list)
    for i,n in enumerate(nodes):byl[n["layer"]].append(i)
    for ids in byl.values():
        active=[]
        for i in sorted(ids,key=lambda x:nodes[x]["box"][0]):
            b=nodes[i]["box"]
            active=[j for j in active if nodes[j]["box"][2]>=b[0]]
            for j in active:
                if conductive(b,nodes[j]["box"]):union(i,j)
            active.append(i)
    return [find(i) for i in range(len(nodes))]

def find_shorts(nodes,limit=100):
    byl=defaultdict(list);bad=[];total=0
    for n in nodes:byl[n["layer"]].append(n)
    for layer,ns in byl.items():
        active=[]
        for n in sorted(ns,key=lambda n:n["box"][0]):
            active=[m for m in active if m["box"][2]>=n["box"][0]]
            for m in active:
                if n["net"]!=m["net"] and touches(n["box"],m["box"]):
                    total+=1
                    if len(bad)<limit:bad.append({"layer":layer,"net_a":m["net"],"net_b":n["net"],"box_a":m["box"],"box_b":n["box"],"kind_a":m["kind"],"kind_b":n["kind"]})
            active.append(n)
    return total,bad

def check(prefix):
    prefix=Path(prefix)
    paths={s:Path(str(prefix)+"."+s) for s in ["layers.tsv","vias.tsv","terminals.tsv","nets.tsv","odb_export.def","pg_calls.tsv"]}
    layers={x["layer"]:x for x in rows(paths["layers.tsv"])}
    vias=defaultdict(list)
    for x in rows(paths["vias.tsv"]):vias[x["via"]].append((x["layer"],[int(x[k]) for k in ["x1","y1","x2","y2"]]))
    # Deduplicate identical via rows; different definitions with the same name are rejected by layer-count/connectivity checks.
    vias={k:sorted(set((lay,tuple(b)) for lay,b in v)) for k,v in vias.items()}
    terms=defaultdict(list);pgterms=defaultdict(list)
    for x in rows(paths["terminals.tsv"]):
        b=[int(x[k]) for k in ["x1","y1","x2","y2"]]
        dest=pgterms if x["sigtype"] in ("POWER","GROUND") else terms
        dest[x["net"]].append(shape(x["layer"],b,x["net"],"terminal",x["terminal"]))
    nets={x["net"]:x for x in rows(paths["nets.tsv"]) if x["sigtype"] not in ("POWER","GROUND")}
    text=paths["odb_export.def"].read_text()
    units=int(re.search(r"UNITS DISTANCE MICRONS (\d+)",text).group(1))
    body={r.split()[0]:r for r in records(section(text,"NETS"))}
    ndrs={}
    if re.search(r"^NONDEFAULTRULES\s",text,re.M):
        for rec in records(section(text,"NONDEFAULTRULES")):
            name=rec.split()[0]
            ndrs[name]={l:int(w) for l,w in re.findall(r"\+\s+LAYER\s+(\S+)\s+WIDTH\s+(\d+)",rec)}
            if not ndrs[name]:raise ValueError("Empty NDR widths "+name)

    report={"method":"Actual ODB re-exported DEF, routing rectangles/via metal enclosures, transformed LEF terminal shapes, conservative component graph","dbu_per_micron":units,
      "limitations":["not foundry DRC/LVS/timing","signal and PG routing plus terminal contact overlay; PG connectivity independently reported by native checker","does not credit hidden intrinsic conduction between separate same-pin shapes","positive-length edge or positive-area contact accepted; corner-only contact does not connect","via cut presence/nonzero area and zero-margin metal containment checked; minimum enclosure/spacing/cut rules depend on separate DRT","no routing netlist functional equivalence inferred"],"nets":[],"errors":[]}
    allnodes=[]
    for name,meta in sorted(nets.items()):
        try:
            if name not in body:raise ValueError("ODB signal net absent from exported DEF")
            ns,links,used=decode_routes(body[name],name,layers,vias,ndrs)
            nr=len(ns);ns+=terms[name]
            roots=contact_graph(ns,links)
            terminal_roots=defaultdict(set)
            for i,n in enumerate(ns):
                if n["kind"]=="terminal":terminal_roots[n["label"]].add(roots[i])
            expected=meta["terminals"].split(",") if meta["terminals"] else []
            missing=sorted(set(expected)-set(terminal_roots))
            common=None
            for pin in expected:
                rr=terminal_roots.get(pin,set())
                common=set(rr) if common is None else common&rr
            common=common or set()
            floating=sorted(set(roots[:nr])-common) if expected else sorted(set(roots[:nr]))
            ok=not missing and (bool(common) or not expected) and not floating
            report["nets"].append({"net":name,"terminals":len(expected),"terminal_names":expected,"route_rectangles":nr,"vias_used":used,"connected_common_components":len(common),"missing_terminal_geometry":missing,"floating_route_components":len(floating),"passed":ok})
            allnodes+=ns
        except Exception as exc:
            report["errors"].append({"net":name,"error":str(exc)})
            report["nets"].append({"net":name,"passed":False,"unsupported_or_invalid":str(exc)})
    orphan_terms=[s for n,ss in terms.items() if n.startswith("__UNCONNECTED__/") for s in ss]
    allnodes+=orphan_terms
    report["unconnected_output_geometry"]=orphan_terms
    report["unconnected_output_policy"]="Only exact clkload0 INV_X1 ZN OUTPUT, justified by CTS-0207 dummy load record; input A remains required."
    report["ndr_widths_dbu"]=ndrs
    pg_shapes=[];pg_route_counts={}
    try:
        for rec in records(section(text,"SPECIALNETS")):
            name=rec.split()[0]
            if name not in pgterms:
                raise ValueError("SPECIALNET lacks exported PG terminals: "+name)
            cleaned=re.sub(r"\+\s+SHAPE\s+[A-Z_]+", "", rec)
            ns,links,used=decode_routes(cleaned,name,layers,vias,special=True)
            pg_route_counts[name]=len(ns)
            pg_shapes+=ns+pgterms[name]
    except Exception as exc:
        report["errors"].append({"power_geometry":str(exc)})
    allnodes+=pg_shapes
    report["pg_route_rectangles"]=pg_route_counts
    report["signal_pg_contacts_checked"]=True
    total,examples=find_shorts(allnodes)
    report["different_net_contacts"]={"count":total,"first_examples":examples}
    report["pg_calls"]=rows(paths["pg_calls.tsv"])
    pg_log=Path(str(prefix.parent/"openroad_export.log")).read_text()
    report["power_grid_connected"]=all(
      "[INFO PSM-0040] All shapes on net "+n+" are connected." in pg_log
      and any(r["net"]==n and r["command_available"]=="1" and r["catch_code"]=="0" for r in report["pg_calls"])
      for n in ("VDD","VSS"))
    report["power_grid_accepted"]=report["power_grid_connected"] and not total and not report["errors"]
    report["pg_note"]="Acceptance covers geometric connectivity and signal-PG contacts only; no IR-drop, EM, LVS, full-foundry DRC or transistor-level PG proof."
    report["signal_geometry_passed"]=not report["errors"] and bool(report["nets"]) and all(n["passed"] for n in report["nets"]) and total==0
    report["geometry_conventions"]={"NETS_default_extension":"half path width","SPECIALNETS_default_extension":"zero","reference":"https://coriolis.lip6.fr/doc/lefdef/lefdefref/DEFSyntax.html"}
    report["source_receipts"]=[{"path":str(p),"bytes":p.stat().st_size,"sha256":sha(p)} for p in paths.values()]
    for suffix,obj in [("geometry.json",{"dbu_per_micron":units,"source":"actual ODB-exported DEF plus ODB terminals","shapes":allnodes}),("connectivity.json",report)]:
        with Path(str(prefix)+"."+suffix).open("x",encoding="utf-8") as f:json.dump(obj,f,indent=2);f.write("\n")
    print(json.dumps({"prefix":str(prefix),"signal_geometry_passed":report["signal_geometry_passed"],"net_count":len(report["nets"]),"failed_nets":sum(not n["passed"] for n in report["nets"]),"short_contacts":total,"unsupported_errors":report["errors"][:3]}))
    return report["signal_geometry_passed"]

def self_test():
    assert touches([0,0,2,2],[2,1,4,3])
    assert not touches([0,0,2,2],[3,1,4,3])
    assert segment([0,0,None],[10,0,0],2)==[-1,-1,10,1]
    assert segment([10,0,0],[0,0,None],2)==[-1,-1,10,1]
    a=[shape("m1",[0,0,2,2],"a","wire",""),shape("m2",[0,0,2,2],"a","wire","")]
    assert len(set(contact_graph(a,[])))==2
    assert len(set(contact_graph(a,[[0,1]])))==1
    b=a+[shape("m1",[1,1,3,3],"b","wire","")]
    assert find_shorts(b)[0]==1
    layers={"m1":{"type":"ROUTING","width":"2"},"m2":{"type":"ROUTING","width":"2"},"c":{"type":"CUT","width":"0"}}
    via={"v":[("m1",(-1,-1,1,1)),("m2",(-1,-1,1,1)),("c",(-1,-1,1,1))]}
    ns,vl,_=decode_routes("a ( PIN a ) + ROUTED m1 ( 0 0 ) ( 10 * ) NEW m1 ( 10 0 ) v NEW m2 ( 10 0 ) ( * 10 )","a",layers,via)
    assert len(set(contact_graph(ns,vl)))==1
    try:decode_routes("a + ROUTED m1 ( 0 0 ) BAD","a",layers,via)
    except ValueError:pass
    else:raise AssertionError("unknown token not rejected")
    assert not conductive([0,0,1,1],[1,1,2,2])
    assert conductive([0,0,1,1],[1,0,2,1])
    ns,_,_=decode_routes("p + ROUTED m1 2 ( 0 0 ) ( 10 0 )","p",layers,{},special=True)
    assert ns[0]["box"]==[0,-1,10,1]
    print("GEOMETRY_CHECKER_SELF_TEST_PASS")

if __name__=="__main__":
    ap=argparse.ArgumentParser();ap.add_argument("--prefix");ap.add_argument("--self-test",action="store_true");a=ap.parse_args()
    if a.self_test:self_test()
    elif a.prefix:raise SystemExit(0 if check(a.prefix) else 1)
    else:ap.error("choose --prefix or --self-test")
