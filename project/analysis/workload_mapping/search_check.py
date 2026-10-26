"""Independent replay of a search plan: no search.advance/solve calls.

Checks every charged load/write, dependencies, pinned RAM and workspace, clean
LRU policy, complete execution and pool capabilities. Symbolic output digests
check pure-DAG equivalence, not floating-point model quality or hardware RTL.
"""
import hashlib
import json
from collections import Counter, OrderedDict

from .resource_bridge import account


def replay(w, h, result, check_upstream=True):
    resident = {r: OrderedDict() for r in h.names}
    done = set()
    available = {v.id for v in w.values.values() if v.producer < 0}
    remaining = Counter(v for t in w.tasks for v in t.reads)
    traffic = []
    charges = []
    peaks = dict.fromkeys(h.names,0)
    totals = dict(load_payload_bytes=0, output_payload_bytes=0, weight_load_bytes=0,
                  activation_load_bytes=0, messages=0)
    def check(ok, message):
        if not ok:
            raise ValueError(message)
    for entry in result["plan"]:
        i,r=entry["task"],entry["resource"]
        check(type(i) is int and 0 <= i < len(w.tasks),"task id")
        t=w.tasks[i]
        check(i not in done and set(t.dependencies)<=done,"duplicate/premature task")
        check(r in h.resources(t),"capability placement")
        check(set(t.reads)<=available,"read before production")
        cache=resident[r]
        missing=[v for v in t.reads if v not in cache]
        check(entry["loads"]==missing,"omitted/invented/duplicate load")
        pinned=set(t.reads)
        needed=sum(w.values[v].size for v in missing)+w.values[t.output].size+t.workspace+h.control_bytes
        expected_evictions=[]
        for v in list(cache):
            if sum(cache.values())+needed<=h.cap(r):
                break
            if v not in pinned:
                del cache[v]
                expected_evictions.append(v)
        check(entry["evictions"]==expected_evictions,"non-LRU or omitted eviction")
        peak=sum(cache.values())+needed
        check(peak<=h.cap(r) and peak==entry["peak_bytes"],"RAM/workspace capacity")
        peaks[r]=max(peaks[r],peak)
        for v in t.reads:
            cache.pop(v,None)
            cache[v]=w.values[v].size
            remaining[v]-=1
        cache[t.output]=w.values[t.output].size
        expected_dead=[v for v in cache if remaining[v]==0]
        check(entry["dead"]==expected_dead,"last-use release")
        for v in expected_dead:
            del cache[v]
        done.add(i)
        available.add(t.output)  # charged durable write, never free spilled state
        for v in missing:
            size=w.values[v].size
            totals["load_payload_bytes"]+=size
            totals["weight_load_bytes" if w.values[v].role=="weight" else "activation_load_bytes"]+=size
            traffic.append((v,["S",r]))
        totals["output_payload_bytes"]+=w.values[t.output].size
        traffic.append((t.output,[r,"S"]))
        charges.append((len(missing)+1,entry["wire_bytes"]))
    check(len(done)==len(w.tasks),"incomplete execution")
    totals["messages"]=len(traffic)
    if check_upstream:
        records=[dict(id=f"message_{i}",path=path,shape=list(w.values[v].shape),
                      logical_bits=w.values[v].bits,storage_bits=w.values[v].bits,
                      metadata_bytes=0,messages=1) for i,(v,path) in enumerate(traffic)]
        ledger=account(records)
        wire=sum(c["wire_bytes"] for c in ledger["transfers"])
        cursor=0
        for count,claimed in charges:
            check(sum(x['wire_bytes'] for x in ledger['transfers'][cursor:cursor+count])==claimed,
                  'per-task packet charge mismatch')
            cursor+=count
    else:
        # Separate literal format oracle for exhaustive small-case tests only.
        def packet(n):
            total=0
            while n:
                part=min(n,1984)
                total+=64+((part+63)//64)*64
                n-=part
            return total
        wire=sum(packet(w.values[v].size) for v,_ in traffic)
    check(wire==result["wire_bytes"],"packet ledger or total mismatch")
    totals.update(wire_bytes=wire,peak_ram_bytes=peaks,task_count=len(done),
                  macs=sum(t.macs for t in w.tasks),end_to_end_seconds=None,
                  clock_hz=None,physical_qualified=False)
    # A canonical semantic digest includes all task operands/constraints and
    # immutable outputs; scheduling cannot change task definitions.
    totals["functional_dag_sha256"]=w.digest()
    return totals


def export(w,h,result):
    """Emit the actual supported workload-mapping/1 contract, including copies.

    Workspaces/control are explicit byte allocations, not omitted scratch.
    No candidate M/V numerical ability or physical placement is asserted.
    """
    from .core import build
    from .consumer import verify_mapping
    graph=dict(schema_version="workload-mapping/1",id=w.name,
        evidence=dict(kind="config_derived",status="derived",source=w.config.get("evidence","synthetic")),
        scope="Synthetic serial shape-DAG mapping; pure kernel declarations, no model numeric/timing proof",
        nodes=[],calls=[],tensors=[],storages=[],states=[],events=[],transfers=[],resource_input=None)
    resources=[]
    links=[]
    for r in ("S",)+h.names:
        ops={t.op for t in w.tasks if r in h.resources(t)} if r!="S" else {"route"}
        ops.add("route")
        resources.append(dict(id=r,kind="external" if r=="S" else "compute",capacity_bytes=None if r=="S" else h.cap(r),
            capabilities=[dict(semantic=op,status="declared",source="synthetic functional pool, not verified Block hardware") for op in sorted(ops)],
            ports=[dict(id="rx",direction="input",protocol="ready_valid",width_bits=128,fifo_bytes=h.fifo_bytes),
                   dict(id="tx",direction="output",protocol="ready_valid",width_bits=128,fifo_bytes=h.fifo_bytes)]))
        if r!="S":
            links.extend([dict(id=f"S_to_{r}",source="S",source_port="tx",destination=r,destination_port="rx",protocol="ready_valid"),
                          dict(id=f"{r}_to_S",source=r,source_port="tx",destination="S",destination_port="rx",protocol="ready_valid")])
    blocks=dict(schema_version="workload-blocks/1",id=w.name+"_hw",evidence=graph["evidence"],resources=resources,links=links)
    held={r:{} for r in h.names}
    host={}
    tensors={}
    current_phase="prefill"
    def event(kind,ref):
        eid="e"+str(len(graph["events"]))
        graph["events"].append(dict(id=eid,kind=kind,ref=ref,step=len(graph["events"]),phase=current_phase))
        return eid
    def alloc(resource,size):
        sid="s"+str(len(graph["storages"]))
        data=dict(id=sid,resource=resource,size_bytes=size,begin=None,end=None)
        graph["storages"].append(data)
        return data
    def tensor(v,s):
        t=dict(id=v.id,shape=list(v.shape),axes=["axis"+str(i) for i in range(len(v.shape))],layout="row_major",
            logical_bits=v.bits,storage_bits=v.bits,metadata_bytes=0,storage=s["id"],offset_bytes=0,
            producer=None if v.producer<0 else "call_"+str(v.producer),consumers=[],role=v.role,initial=v.producer<0,alias_of=None)
        graph["tensors"].append(t);tensors[v.id]=t
    for v in w.values.values():
        if v.producer<0:
            host[v.id]=alloc("S",v.size);tensor(v,host[v.id])
    def copy(v,src,dst,source,destination):
        xid="transfer_"+str(len(graph["transfers"]))
        graph["transfers"].append(dict(id=xid,tensor=v,source_storage=src["id"],destination_storage=dst["id"],
                                     path=[f"{source}_to_{destination}"],messages=1))
        at=event("transfer",xid)
        if dst["begin"] is None:dst["begin"]=at
        return at
    for entry in result["plan"]:
        i,r=entry["task"],entry["resource"]
        t=w.tasks[i]
        current_phase=t.phase
        for v in entry["evictions"]:
            held[r].pop(v)["end"]=graph["events"][-1]["id"]
        for v in entry["loads"]:
            slot=alloc(r,w.values[v].size);held[r][v]=slot
            copy(v,host[v],slot,"S",r)
        output=alloc(r,w.values[t.output].size);held[r][t.output]=output
        tensor(w.values[t.output],output)
        cid="call_"+str(i)
        graph["nodes"].append(dict(id="node_"+str(i),semantic=t.op,contract="shape-declared pure kernel; numerical implementation unverified"))
        graph["calls"].append(dict(id=cid,node="node_"+str(i),resource=r,reads=list(t.reads),writes=[t.output]))
        for v in t.reads:tensors[v]["consumers"].append(cid)
        at=event("call",cid);output["begin"]=at
        scratch=alloc(r,t.workspace+h.control_bytes);scratch["begin"]=scratch["end"]=at
        host[t.output]=alloc("S",w.values[t.output].size)
        end=copy(t.output,output,host[t.output],r,"S")
        for v in entry["dead"]:
            held[r].pop(v)["end"]=end
    first,last=graph["events"][0]["id"],graph["events"][-1]["id"]
    for s in graph["storages"]:
        s["begin"]=s["begin"] or first;s["end"]=s["end"] or last
    mapped=build(graph,blocks)
    verify_mapping(mapped["mapping_request"])
    return graph,blocks,mapped
