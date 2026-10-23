"""Explicit quantized graph, beat accounting and bounded static design search.

This is a deterministic event scheduler, not a calibrated chip simulator. Bank
ports service one 64B beat/port/cycle; one burst cannot hide uncounted transfers.
All variants use one serial RQ, one matrix engine, one vector service engine,
two 64KiB banks, one shared half-duplex 64B/cycle link and the same buffers.
"""
import argparse
import heapq
import itertools
import math
from collections import Counter
from record import provenance,save


def beats(n,offset=0):
    return 0 if n==0 else ((offset%64)+n+63)//64


class Graph:
    def __init__(self,mode):
        self.tasks=[];self.bytes=Counter();self.transfers=[]
        self.capacity={"matrix":1,"vector":1,"rq":1,"link":1}
        for b in (0,1):
            if mode=="1R1W":self.capacity.update({f"b{b}r":1,f"b{b}w":1})
            else:self.capacity[f"b{b}"]=1
        self.mode=mode
    def add(self,resource,duration,deps=()):
        i=len(self.tasks);self.tasks.append((resource,duration,tuple(deps)));return (i,)
    def memory(self,bank,write,n,deps):
        res=f"b{bank}"+("w" if write else "r") if self.mode=="1R1W" else f"b{bank}"
        self.bytes[res]+=n
        self.bytes[res+"_physical"]+=beats(n)*64
        # Nonpreemptive burst arbiter. A 2RW burst stripes over its two ports;
        # directions are not interleaved within that burst. Same policy for all.
        return self.add(res,math.ceil(beats(n)/(2 if self.mode=="2RW" else 1)),deps) if n else deps
    def link(self,n,deps,direction,kind):
        self.bytes["link_payload"]+=n;self.bytes["link_physical"]+=beats(n)*64
        self.transfers.append({"bytes":n,"beats":beats(n),"direction":direction,"kind":kind})
        # Independently aligned packet per tile/field; no free packet coalescing.
        return self.add("link",beats(n),deps) if n else deps
    def schedule(self):
        indegree=[len(t[2]) for t in self.tasks];children=[[] for _ in self.tasks]
        for i,t in enumerate(self.tasks):
            for d in t[2]:children[d].append(i)
        ready=[i for i,n in enumerate(indegree) if n==0];heapq.heapify(ready)
        free=dict(self.capacity);events=[];now=0;finished=0;busy=Counter();ends={}
        while finished<len(self.tasks):
            deferred=[]
            while ready:
                i=heapq.heappop(ready);resource,duration,_=self.tasks[i]
                if free[resource]:
                    free[resource]-=1;heapq.heappush(events,(now+duration,i));busy[resource]+=duration
                else:deferred.append(i)
            for i in deferred:heapq.heappush(ready,i)
            if not events:raise RuntimeError("cycle/deadlock in graph")
            now=events[0][0]
            while events and events[0][0]==now:
                _,i=heapq.heappop(events);free[self.tasks[i][0]]+=1;finished+=1;ends[i]=now
                for c in children[i]:
                    indegree[c]-=1
                    if indegree[c]==0:heapq.heappush(ready,c)
        return now,dict(busy)


def candidate(rq,partial,state_bank,mode,rows,window,state_bits,state_cells,scale_mode,links="bidirectional"):
    m,n,k=32,16,1024;kparts=4;rq_bank=0 if rq=="near" else 1
    # Full weight residency, one tile input per live slot, explicit accumulator
    # and output boundary buffers. All strategies receive the same 2KiB budget.
    boundary=window*rows*n*(4+1)
    params=5*n*(1 if scale_mode=="static" else m)
    banks=[n*k+window*rows*k,0];banks[state_bank]+=state_cells*(state_bits//8)
    banks[rq_bank]+=params
    banks[1]+=window*rows*n*4 # shared vector reduction/RQ workspace reserved for both
    banks[0]+=window*rows*n*4 # matrix workspace reserved for both
    descriptor=dict(rq=rq,partial=partial,state_bank=state_bank,port_mode=mode,tile_rows=rows,window=window,
                    state_bits=state_bits,state_cells=state_cells,scale_mode=scale_mode,static_links=links)
    required={"M->V"}
    if (partial=="cross" and rq=="near") or state_bank==0:required.add("V->M")
    rejection=[]
    state_working=state_cells*(state_bits//8)
    if boundary>2048:rejection.append("finite boundary buffer")
    if state_working>32768:rejection.append("private state working capacity")
    if any(b>65536 for b in banks):rejection.append("per-bank capacity")
    if links=="forward_only" and "V->M" in required:rejection.append("static connection unreachable")
    base={**descriptor,"bank_resident_bytes":banks,"boundary_bytes":boundary,"state_working_bytes":state_working,"rq_parameter_bytes":params,
          "required_connections":sorted(required),"feasible":not rejection,"rejected":rejection}
    if rejection:return base
    g=Graph(mode);previous=[() for _ in range(window)];last_state=()
    for tile,start in enumerate(range(0,m,rows)):
        nr=min(rows,m-start);elements=nr*n;launch=previous[tile%window];part_deps=launch;reduction=()
        for part in range(kparts):
            read=g.memory(0,False,nr*(k//kparts)+n*(k//kparts),part_deps)
            matrix=g.add("matrix",math.ceil(nr*n*(k//kparts)/256),read)
            part_deps=matrix
            if partial=="cross":
                stored=g.memory(0,True,elements*4,matrix)
                partial_read=g.memory(0,False,elements*4,stored)
                sent=g.link(elements*4,partial_read,"M->V","INT32 partial")
                arrived=g.memory(1,True,elements*4,sent)
                readback=g.memory(1,False,elements*4,arrived+reduction)
                reduction=g.add("vector",elements if part else 1,readback)
                reduction=g.memory(1,True,elements*4,reduction)
        if partial=="internal":
            acc=g.memory(0,True,elements*4,part_deps)
            if rq_bank==1:
                src=g.memory(0,False,elements*4,acc)
                acc=g.memory(1,True,elements*4,g.link(elements*4,src,"M->V","INT32 final"))
        else:
            acc=reduction
            if rq_bank==0:
                src=g.memory(1,False,elements*4,acc)
                acc=g.memory(0,True,elements*4,g.link(elements*4,src,"V->M","INT32 final"))
        rq_inputs=g.memory(rq_bank,False,elements*4,acc)
        rq_params=g.memory(rq_bank,False,5*n*(nr if scale_mode=="dynamic_row" else 1),launch)
        # Observed RQ interface service: latency26, min initiation interval28.
        quantized=g.add("rq",28*elements,rq_inputs+rq_params)
        qstore=g.memory(rq_bank,True,elements,quantized)
        if rq_bank==0:
            qread=g.memory(0,False,elements,qstore)
            qstore=g.memory(1,True,elements,g.link(elements,qread,"M->V","INT8 requantized"))
        qread=g.memory(1,False,elements,qstore)
        # Fixed V engine owns the update. A remote state has to cross both ways.
        # One sequential state update per token, independent of tiling. No
        # uncounted private register file that magically reuses a whole state.
        for token in range(nr):
            sr=g.memory(state_bank,False,state_cells*(state_bits//8),launch+last_state)
            if state_bank==0:sr=g.link(state_cells*(state_bits//8),sr,"M->V","wide state read")
            updated=g.add("vector",1+state_cells,qread+sr)
            if state_bank==0:updated=g.link(state_cells*(state_bits//8),updated,"V->M","wide state write")
            done=g.memory(state_bank,True,state_cells*(state_bits//8),updated)
            last_state=done
        previous[tile%window]=done
    cycles,busy=g.schedule()
    return {**base,"cycles":cycles,"resource_busy":busy,"traffic_bytes":dict(g.bytes),
            "link_beats":sum(t["beats"] for t in g.transfers),"nodes":len(g.tasks)}


def main():
    p=argparse.ArgumentParser();p.add_argument("--output",required=True);a=p.parse_args()
    rows=[]
    for combo in itertools.product(("near","shared"),("internal","cross"),(0,1),("1RW","1R1W","2RW"),(1,4,8,16),(1,2),(16,32),(1024,8192,16384),("static","dynamic_row"),("forward_only","bidirectional")):
        rows.append(candidate(*combo))
    save(a.output,{"producer":provenance("placement.py"),"schema":"quantized-placement-c1/1","candidates":rows,
                  "inventory":{"banks":2,"bank_bytes":65536,"beat_bytes":64,"matrix_mac_per_cycle_assumed":256,
                               "state_working_bytes":32768,"state_working_port_assumption":"1R1W, each 64B/cycle; extra to banks and boundary buffers",
                               "rq_units":1,"rq_service_cycles_per_scalar":28,"vector_units":1,"half_duplex_links":1,"boundary_bytes":2048},
                  "limits":["Mixed operator fixture, not end-to-end Qwen model","No calibrated RTL for banks/vector/nonlinear in this graph; no PPA/timing/energy claim",
                            "Deterministic earliest-ready task order is identical, not globally optimal; static design candidates searched",
                            "Bank bursts are nonpreemptive; 2RW stripes one burst over both ports, without mixed-direction interleaving. Link packets are nonpreemptive",
                            "State16 and state32 are separate precision profiles, not a claimed accuracy-equivalent speedup",
                            "Synthetic fixed state-update service is state_cells+1 cycles/token; cannot replace true recurrence costs",
                            "All RQ parameters assumed preloaded; read traffic counted. Model loading/setup is outside measured fixture",
                            "Private 32KiB state scratch is explicitly budgeted in all variants; whole-state staging is not free. No macro/PPA established"]})
    print({"candidates":len(rows),"feasible":sum(r["feasible"] for r in rows)})


if __name__=="__main__":main()
