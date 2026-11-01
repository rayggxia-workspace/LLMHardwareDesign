"""Bind measured origin-node charge to the sealed real M10 access route.

This integration measures a candidate replacement for the old length-weighted
C estimate on one isolated routed net. It does not qualify capture-node coupling,
window ownership, native/new-layer stitching, or full-block extraction.
"""
import concurrent.futures
import json
import math
from pathlib import Path
import re


def graph_nodes(record, scene, technology):
    """Use the sealed DC graph's exact coordinates in its field scene frame."""
    layers={}
    for name,body in re.findall(r'(?ms)^LAYER\s+(metal\d+)\s*\n(.*?)^END\s+\1\s*$',technology):
        def value(key):
            return float(re.search(r'(?m)^\s*'+key+r'\s+([\d.]+)\s*;',body).group(1))
        layers[name]=value('HEIGHT')+value('THICKNESS')/2
    boxes=[];master=None
    for line in scene.splitlines():
        fields=line.split()
        if fields[:1]==['master']:
            assert master is None and len(fields)==2;master=fields[1]
        elif fields[:1]==['box']:
            assert len(fields)==8;boxes.append((fields[1],list(map(float,fields[2:]))))
        else:
            assert fields==['background','3.9']
    assert master and boxes and {n for n,b in boxes}=={master}
    edges=record['graph_edges'];ordered=sorted({tuple(e[k])for e in edges for k in ['a','b']})
    assert len(ordered)==record['graph_nodes'] and len(edges)==len(ordered)-1
    adjacent={n:set()for n in ordered};seen=set()
    for e in edges:
        a,b=tuple(e['a']),tuple(e['b']);key=frozenset((a,b))
        assert a!=b and key not in seen and math.isfinite(e['resistance_ohm'])and e['resistance_ohm']>0
        seen.add(key);adjacent[a].add(b);adjacent[b].add(a)
    visited=set();stack=[ordered[0]]
    while stack:
        n=stack.pop()
        if n not in visited:visited.add(n);stack.extend(adjacent[n])
    assert visited==set(ordered) and all(1<=len(v)<=2 for v in adjacent.values())
    assert math.isclose(sum(e['resistance_ohm']for e in edges),record['resistance_ohm'],rel_tol=1e-12)
    # The original reader translates by the minimum complete conductor bbox.
    # The known source ports identify the same physical route, never a guessed
    # origin obtained from centerline extrema (wire extensions differ).
    source_xy=[68800,68800];end_xy=[273600,273600]
    assert {n for n,v in adjacent.items()if len(v)==1}=={('metal10',*source_xy),('metal10',*end_xy)}
    # The scene is bound below to the original geometry export, and its shift
    # is read from that source rather than inferred from these endpoints.
    return master,boxes,ordered,layers


def bind_nodes(record,scene,technology,geometry_text):
    master,boxes,ordered,layers=graph_nodes(record,scene,technology)
    coords=[]
    for line in geometry_text.splitlines():
        if not line.startswith('#'):
            alias,layer,kind,*values=line.split('\t');assert alias==master and len(values)==4
            coords.append(list(map(int,values)))
    assert coords
    ox=min(p[0]for p in coords)/2000;oy=min(p[1]for p in coords)/2000
    nodes=[]
    for i,(layer,x,y)in enumerate(ordered):
        point=[x/2000-ox,y/2000-oy,layers[layer]]
        assert all(math.isfinite(v)for v in point)
        assert any(all(b[k]-1e-9<=point[k]<=b[k+3]+1e-9 for k in range(3))for n,b in boxes)
        nodes.append(dict(id='n%d'%i,physical=[layer,x,y],scene_xyz_um=point))
    assert len({tuple(n['scene_xyz_um'])for n in nodes})==len(nodes)
    return master,nodes


def verify(root,out,cpus,run):
    from io_slots import file_sha
    assert cpus>=12 and cpus%3==0
    base=out.parents[2]
    def accepted(folder,names):
        receipt=json.loads((folder/'receipt.json').read_text());assert receipt['passed']is True
        for name in names:
            assert file_sha(folder/name)==receipt['outputs'][name],name
        return receipt
    science=base/'block-v1-20261027-091/tasks/graph-geometry-group'
    accepted(science,['graph-geometry-group.json'])
    proof=json.loads((science/'graph-geometry-group.json').read_text());assert proof['passed']is True
    assert len(proof['children'])==2 and all(c['passed']for c in proof['children'])
    prior=base/'block-v1-20261027-051/tasks/routed-field'
    accepted(prior,['routed-field.json','routed-scene.txt','routed-field.spef','routed-field.jsonl'])
    record=json.loads((prior/'routed-field.json').read_text());assert record['passed']is True
    geometry=base/'block-v1-20261027-043/tasks/geometry-reader-full'
    accepted(geometry,['geometry-R0.tsv','odb-geometry.json'])
    assert file_sha(geometry/'geometry-R0.tsv')==record['geometry_sha256']
    original=base/'block-v1-20261027-009/tasks/route-probe'
    accepted(original,['probe/routed.odb','probe/routed.def','overlay/research12.tech.lef'])
    assert file_sha(original/'probe/routed.def')==record['routed_def_sha256']
    scene=(prior/'routed-scene.txt').read_text();technology=(original/'overlay/research12.tech.lef').read_text()
    assert file_sha(prior/'routed-scene.txt')==record['scene_sha256']
    master,nodes=bind_nodes(record,scene,technology,(geometry/'geometry-R0.tsv').read_text())
    (out/'scene.txt').write_text(scene)
    (out/'nodes.txt').write_text(''.join(n['id']+' '+' '.join('%.12g'%v for v in n['scene_xyz_um'])+'\n'for n in nodes))
    solver=base/'block-v1-20261027-090/tasks/fsv-graph-build'
    accepted(solver,['fsv-qualified.json'])
    qualified=json.loads((solver/'fsv-qualified.json').read_text())
    binary=Path(qualified['graph_binary']);assert file_sha(binary)==qualified['graph_binary_sha256']
    offsets=[.5,.25,.125];walks=33554432
    def solve(offset):
        name='offset-'+str(offset)+'.json'
        run([str(binary),str(cpus//3),str(offset),str(walks),str(out/'scene.txt'),str(out/'nodes.txt')],name)
        return json.loads((out/name).read_text())
    with concurrent.futures.ThreadPoolExecutor(max_workers=3)as pool:
        rows=list(pool.map(solve,offsets))
    assert all(r['nodes']==[n['id']for n in nodes]and r['master']==master for r in rows)
    entries=[{e['net']:e for e in r['entries']}for r in rows]
    assert all(set(e)=={master,'ground'}for e in entries)
    last=entries[-1];before=entries[-2];total=last[master]['cap']
    charges=[-c for c in last['ground']['partial']]
    sigma=last['ground']['partial_sigma']
    oldrows=[json.loads(line)for line in(prior/'routed-field.jsonl').read_text().splitlines()]
    assert oldrows.pop()=={'status':'PASS','mode':'scene3d'}and len(oldrows)==1
    oldentry={e['net']:e for e in oldrows[0]['entries']}
    assert set(oldentry)=={master,'ground'}
    gates=dict(positive_total=math.isfinite(total)and total>0,
        physical_local_signs=all(math.isfinite(c)and c>0 for c in charges),
        precision=all(math.isfinite(s)and 0<=s<=.001*total for s in sigma),
        exact_row_conservation=all(abs(sum(e['partial'])-e['cap'])<=1e-10*max(1,abs(e['cap']))for row in entries for e in row.values()),
        offset_convergence=all(abs(a-b)<=.01*total+5*math.hypot(sa,sb)
            for name in last for a,b,sa,sb in zip(last[name]['partial'],before[name]['partial'],last[name]['partial_sigma'],before[name]['partial_sigma'])),
        prior_total_consistency=abs(sum(charges)-record['measured_ground_ff'])<=.01*total+5*math.hypot(sum(sigma),
            # Old full-row uncertainty is read from its original sealed field output.
            oldentry['ground']['sigma']))
    result=dict(schema='block-v1-routed-graph-field/1',passed=all(gates.values()),gates=gates,
        nodes=nodes,edges=record['graph_edges'],local_ground_ff=charges,local_sigma_ff=sigma,
        field_rows=rows,offsets=offsets,walks_per_offset=walks,
        source_geometry_sha256=file_sha(geometry/'geometry-R0.tsv'),source_dc_graph_sha256=file_sha(prior/'routed-field.json'),
        source_receipt_sha256=file_sha(prior/'receipt.json'),
        graph_fixture_receipt_sha256=file_sha(science/'receipt.json'),scene_sha256=file_sha(out/'scene.txt'),
        node_file_sha256=file_sha(out/'nodes.txt'),solver_sha256=file_sha(binary),
        qualified_full_block=False,qualified_node_pair_coupling=False,
        independent_local_fv_on_this_route=False,
        scope='Measured origin-node charge on one isolated real access net; convergence and source binding only, not general distributed RC qualification')
    (out/'routed-graph-field.json').write_text(json.dumps(result,indent=2)+'\n')
    assert result['passed'],'Real-route origin charge gate failed; preserve all measurements'
