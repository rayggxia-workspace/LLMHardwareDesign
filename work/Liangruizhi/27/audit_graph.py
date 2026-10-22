"""Read-only graph review, independent reachability/bytes checks and negative probes."""
import copy
import hashlib
import importlib.util
import itertools
import json
from pathlib import Path

ROOT = Path("D:/Projects/LLMHardwareDesign-stateport/project/experiments/state_ports/graph.py")
OUT = Path(__file__).resolve().parent


def main():
    raw = ROOT.read_bytes()
    source_hash = hashlib.sha256(raw).hexdigest()
    snapshot = OUT / ("graph-snapshot-"+source_hash[:12]+".py")
    snapshot.write_bytes(raw)
    spec = importlib.util.spec_from_file_location("audited_graph",snapshot)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    config = dict(key_tile=4,max_query_tile=4,bank_ports="1R1W",bank_bytes=[4096,4096],
        scratch_bytes={"M":4096,"V":4096},bank_port_bytes_per_cycle=16,
        link_bytes_per_cycle=16,external_bytes_per_cycle=16,burst_setup_cycles=1,
        matrix_macs_per_cycle=4,vector_elements_per_cycle=4)
    workload = dict(queries=2,keys=5,head_dim=4)
    placement = dict(O=0,m=1,l=1)
    assertions = 0
    relation_counts = dict(RAW=0,WAR=0,WAW=0)
    normal_cases = []

    def verify(condition, message):
        nonlocal assertions
        assertions += 1
        if not condition:
            raise AssertionError(message)

    def serial(graph):
        events=[]
        cursor=0
        for task in graph["tasks"]:
            events.append({"id":task["id"],"start":cursor,"end":cursor+task["duration"]})
            cursor += task["duration"]
        return {"events":events}

    def inspect(graph,w):
        task_by_id = {t["id"]:t for t in graph["tasks"]}
        verify(len(task_by_id)==len(graph["tasks"]),"duplicate task")
        ancestors={}
        for task in graph["tasks"]:
            verify(all(dep in ancestors for dep in task["deps"]),"not topological/unknown dependency")
            ancestors[task["id"]]=set(task["deps"])
            for dep in task["deps"]:
                ancestors[task["id"]].update(ancestors[dep])
        last_write, readers = {},{}
        for access in graph["accesses"]:
            name,tid=access["object"],access["id"]
            slot=graph["slots"][name]
            verify(access["bank"]==slot["bank"] and access["offset"]==slot["offset"],"address binding")
            verify(type(access["bytes"]) is int and 0<access["bytes"]<=slot["bytes"] and access["bytes"]%4==0,"extent")
            if access["direction"]=="R":
                verify(name in last_write,"uninitialized read")
                write=last_write[name]
                verify(write["id"] in ancestors[tid],"missing RAW closure")
                verify(access["bytes"]<=write["bytes"],"latest version has unwritten bytes")
                relation_counts["RAW"]+=1
                readers.setdefault(name,[]).append(tid)
            else:
                for read in readers.pop(name,[]):
                    verify(read in ancestors[tid],"missing WAR closure")
                    relation_counts["WAR"]+=1
                if name in last_write:
                    verify(last_write[name]["id"] in ancestors[tid],"missing WAW closure")
                    relation_counts["WAW"]+=1
                last_write[name]=access
        verify(not module.verify_access_order(graph,serial(graph)),"production checker rejects serial witness")
        q,n,d=[w[k] for k in ("queries","keys","head_dim")]
        tiles=(n+config["key_tile"]-1)//config["key_tile"]
        expected={"D":(2*q*d+2*n*d)*4,
                  "M":(2*tiles*q*d+2*n*d+2*q*n)*4,
                  "V":(3*q*d+3*q+2*q*n+tiles*(3*q*d+6*q))*4}
        verify(graph["traffic"]==expected,"traffic closed form")
        verify(graph["matrix_macs"]==2*q*n*d,"MAC closed form")
        for bank in (0,1):
            intervals=sorted((s["offset"],s["offset"]+s["bytes"]) for s in graph["slots"].values() if s["bank"]==bank)
            verify(all(a[1]<=b[0] for a,b in zip(intervals,intervals[1:])),"slot overlap")
            verify(all(a>=0 and z<=graph["bank_capacity_bytes"][bank] for a,z in intervals),"capacity")
        # All inputs and outputs of a transaction may coexist in engine scratch.
        prior={}
        operations={}
        for task in graph["tasks"]:
            if task["kind"]=="compute":
                prefix=task["id"][:-len(".compute")]
                operations[prefix]=task["engine"]
        for prefix,engine in operations.items():
            ins=[a for a in graph["accesses"] if a["id"].startswith(prefix+".r")]
            outs=[a for a in graph["accesses"] if a["id"].startswith(prefix+".w")]
            verify(sum(a["bytes"] for a in ins+outs)<=graph["scratch_reserved_bytes"][engine],"scratch capacity")
            if engine in prior:
                for access in ins:
                    verify(all(end in ancestors[access["id"]] for end in prior[engine]),"scratch reuse before transaction drained")
            prior[engine]=[a["id"] for a in outs] or [prefix+".compute"]

    for port,placement_values,w in itertools.product(
        ("1RW","1R1W","2RW"),itertools.product((0,1),repeat=3),
        (dict(queries=1,keys=1,head_dim=3),dict(queries=1,keys=7,head_dim=4),
         dict(queries=2,keys=8,head_dim=3),dict(queries=4,keys=9,head_dim=4))):
        cfg={**config,"bank_ports":port}
        p=dict(zip(("O","m","l"),placement_values))
        graph=module.make_graph(cfg,w,p)
        inspect(graph,w)
        normal_cases.append({"port":port,"placement":p,"workload":w,"tasks":len(graph["tasks"])})

    invalid=[]
    def reject(label,cfg=config,w=workload,p=placement,disabled=()):
        try:
            module.make_graph(cfg,w,p,disabled)
            invalid.append({"case":label,"rejected":False})
        except (ValueError,TypeError,KeyError,ZeroDivisionError) as error:
            invalid.append({"case":label,"rejected":True,"exception":type(error).__name__})
    bad_values=(0,-1,1.5,float("nan"),True)
    for name in ("key_tile","max_query_tile","bank_port_bytes_per_cycle","link_bytes_per_cycle",
                 "external_bytes_per_cycle","matrix_macs_per_cycle","vector_elements_per_cycle"):
        for value in bad_values:
            reject(name+"="+repr(value),cfg={**config,name:value})
    for value in (-1,1.5,float("nan"),True):
        reject("setup="+repr(value),cfg={**config,"burst_setup_cycles":value})
        reject("bank_capacity="+repr(value),cfg={**config,"bank_bytes":[value,4096]})
        reject("scratch_capacity="+repr(value),cfg={**config,"scratch_bytes":{"M":value,"V":4096}})
    for key in ("queries","keys","head_dim"):
        for value in bad_values:
            reject("workload."+key+"="+repr(value),w={**workload,key:value})
    for value in (True,2,0.5):
        reject("placement.O="+repr(value),p={**placement,"O":value})
    reject("unknown_disabled",disabled=("TYPO",))
    reject("duplicate_disabled",disabled=("M0","M0"))
    verify(all(v["rejected"] for v in invalid),"invalid config accepted")

    base=module.make_graph(config,workload,placement)
    result=serial(base)
    probes=[]
    def mutate(label,callback):
        graph=copy.deepcopy(base)
        callback(graph)
        errors=module.verify_access_order(graph,result)
        probes.append({"case":label,"rejected":bool(errors),"errors":errors})
    def access(graph,tid):
        return next(a for a in graph["accesses"] if a["id"]==tid)
    mutate("wrong_access_bank",lambda g:access(g,"entry.Q").update(bank=1))
    mutate("wrong_access_offset",lambda g:access(g,"entry.Q").update(offset=64))
    mutate("read_beyond_slot",lambda g:access(g,"t1.qk.rK").update(bytes=g["slots"]["K"]["bytes"]+4))
    mutate("read_unwritten_tail_within_slot",lambda g:access(g,"t1.qk.rK").update(bytes=g["slots"]["K"]["bytes"]))
    mutate("shortened_latest_write",lambda g:access(g,"t1.loadK").update(bytes=4))
    def bad_bank(graph):
        graph["slots"]["Q"]["bank"]=2
        for a in graph["accesses"]:
            if a["object"]=="Q":a["bank"]=2
    mutate("slot_and_access_unknown_bank",bad_bank)
    mutate("invalid_direction_treated_as_write",lambda g:access(g,"entry.Q").update(direction="X"))
    output={"status":"PASS" if all(p["rejected"] for p in probes) else "GAPS_FOUND",
        "source_sha256":source_hash,"scope":"Independent dependency closure/bytes/scratch checks and production-checker rejection probes; no scheduler optimization or model arithmetic.",
        "normal_cases":len(normal_cases),"assertions":assertions,"dependency_relations":relation_counts,
        "invalid_config_probes":invalid,"checker_probes":probes,"cases":normal_cases}
    path=OUT/"graph-audit-results.json"
    path.write_text(json.dumps(output,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:output[k] for k in ("status","source_sha256","normal_cases","assertions","dependency_relations","checker_probes")},indent=2))
    print("invalid_config_rejected="+str(len(invalid)))
    print("result_sha256="+hashlib.sha256(path.read_bytes()).hexdigest())


if __name__=="__main__":
    main()
