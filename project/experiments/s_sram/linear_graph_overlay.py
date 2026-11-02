"""Isolated OpenRAM graph-list optimization with exact mutation controls.

Leaves the installed package and running compilers unchanged. Only replaces
the quadratic list-removal loop; neighbor removal order and survivor order
remain identical. No routing, geometric, electrical or verification rule changes.
"""
import argparse
import ast
import copy
import hashlib
import json
import os
from pathlib import Path
import random
import shutil
import time

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def method(text,cls,name):
    c=next(n for n in ast.parse(text).body if isinstance(n,ast.ClassDef) and n.name==cls)
    return next(n for n in c.body if isinstance(n,ast.FunctionDef) and n.name==name)

def function(node):
    ns={};exec(compile(ast.fix_missing_locations(ast.Module(body=[node],type_ignores=[])),'<verified-method>','exec'),ns)
    return ns[node.name]

def build(source,destination,out):
    assert os.environ.get('SLURM_JOB_ID')
    source=source.resolve();destination=destination.resolve()
    assert destination.is_relative_to(Path('/public/home/yuzelu/opt/eda'))
    assert not destination.exists()
    graph=source/'compiler/router/graph.py';nodes=source/'compiler/router/graph_node.py'
    text=graph.read_text();old=method(text,'graph','remove_blocked_nodes')
    original=function(old)
    replacement='''    def remove_blocked_nodes(self):
        """Remove blocked nodes without repeated linear list searches."""
        for node in reversed(self.nodes):
            if node.remove:
                node.remove_all_neighbors()
        self.nodes[:] = [node for node in self.nodes if not node.remove]
'''
    new=method('class graph:\n'+replacement,'graph','remove_blocked_nodes')
    optimized=function(new)
    # Execute the actual vendor neighbor-removal method, including its exact
    # current list-mutation behavior; do not fix another algorithm implicitly.
    remove_neighbors=function(method(nodes.read_text(),'graph_node','remove_all_neighbors'))
    class Node:
        def __init__(self,i):self.id=i;self.remove=False;self.neighbors=[]
        def remove_all_neighbors(self):remove_neighbors(self)
    class Graph:pass
    def state(g):return ([n.id for n in g.nodes],[[v.id for v in n.neighbors] for n in g.all_nodes])
    rng=random.Random(155)
    for case in range(1000):
        g=Graph();g.nodes=[Node(i) for i in range(1+rng.randrange(100))];g.all_nodes=g.nodes[:]
        for n in g.nodes:n.remove=bool(rng.randrange(2))
        for _ in range(len(g.nodes)*3):
            a,b=rng.sample(g.nodes,2) if len(g.nodes)>1 else (g.nodes[0],g.nodes[0])
            if a is not b and b not in a.neighbors:a.neighbors.append(b);b.neighbors.append(a)
        fast=copy.deepcopy(g);before=g.nodes;fast_before=fast.nodes
        original(g);optimized(fast)
        assert g.nodes is before and fast.nodes is fast_before
        assert state(g)==state(fast),(case,'Graph mutation differs')
    g=Graph();g.nodes=[Node(i) for i in range(30000)];g.all_nodes=g.nodes[:]
    for n in g.nodes:n.remove=n.id%3!=0
    fast=copy.deepcopy(g);times={}
    for name,fn,obj in [('vendor',original,g),('linear',optimized,fast)]:
        start=time.monotonic();fn(obj);times[name]=time.monotonic()-start
    assert state(g)==state(fast)
    # This is only a list-loop benchmark, not a promised macro run speedup.
    shutil.copytree(source,destination/'openram',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    lines=text.splitlines(keepends=True)
    patched=''.join(lines[:old.lineno-1])+replacement+''.join(lines[old.end_lineno:])
    ast.parse(patched)
    target=destination/'openram/compiler/router/graph.py';target.write_text(patched)
    changed=[];manifest={}
    for p in source.rglob('*'):
        if not p.is_file() or '__pycache__' in p.parts or p.suffix=='.pyc':continue
        relative=p.relative_to(source);q=destination/'openram'/relative
        a=sha(p);b=sha(q);manifest[str(relative)]=dict(original=a,overlay=b)
        if a!=b:changed.append(str(relative))
    assert changed==['compiler/router/graph.py'],changed
    record=dict(passed=True,original_package=str(source),overlay_pythonpath=str(destination),
        changed_files=changed,original_graph_sha256=sha(graph),overlay_graph_sha256=sha(target),
        actual_neighbor_method_file_sha256=sha(nodes),random_graph_cases=1000,
        list_identity_survivor_and_all_neighbor_order_equal=True,benchmark_30000_nodes_seconds=times,
        package_manifest=manifest,
        scope='Only graph node list removal optimized. Exact original neighbor mutation semantics retained; macro route/DRC/LVS/SPICE remain required.')
    out.write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps({k:v for k,v in record.items() if k!='package_manifest'},indent=2))

if __name__=='__main__':
    ap=argparse.ArgumentParser()
    for k in ('source','destination','out'):ap.add_argument('--'+k,required=True,type=Path)
    a=ap.parse_args();build(a.source,a.destination,a.out)
