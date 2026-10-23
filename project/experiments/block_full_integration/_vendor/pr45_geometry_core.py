"""Selected unchanged geometry primitives from project PR45.
Source commit: a17a0b61b68fce06e318054aad053ed669c048a5
Source path: project/experiments/frozen_control_cones/geometry_reference.py
Source whole-file SHA-256: 9cd4d899366c8dd7870ae8cf4232c55e5787fc59d3d1e6130543e8c118e62faa
Functions reused verbatim: touches, conductive, contained, contact_graph.
This is reuse of existing rectangle/contact graph methods, not a novel algorithm.
"""
from collections import defaultdict

def touches(a,b):
    return max(a[0],b[0])<=min(a[2],b[2]) and max(a[1],b[1])<=min(a[3],b[3])

def conductive(a,b):
    dx=min(a[2],b[2])-max(a[0],b[0]);dy=min(a[3],b[3])-max(a[1],b[1])
    return dx>=0 and dy>=0 and (dx>0 or dy>0)

def contained(a,b):return a[0]>=b[0] and a[1]>=b[1] and a[2]<=b[2] and a[3]<=b[3]

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
