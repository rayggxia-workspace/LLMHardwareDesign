"""Actual routed internal-M10 access probe -> full geometry field row and RC view.

Capacitance totals use the complete qualified geometry. The distributed C
partition remains an explicit length-weighted approximation; this is not a
qualification of full-block distributed extraction.
"""
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import re


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(root,out,cpus,run):
    base=out.parents[2]
    geometry=base/'block-v1-20261027-043/tasks/geometry-reader-full'
    prior=json.loads((geometry/'receipt.json').read_text());assert prior['passed']is True
    for name in ['geometry-R0.tsv','odb-geometry.json']:
        assert sha(geometry/name)==prior['outputs'][name]
    assert json.loads((geometry/'odb-geometry.json').read_text())['passed']is True
    original=base/'block-v1-20261027-009/tasks/route-probe'
    bound=json.loads((original/'receipt.json').read_text());assert bound['passed']is True
    for name in ['probe/routed.odb','probe/routed.def','overlay/research12.tech.lef']:
        assert sha(original/name)==bound['outputs'][name]
    tech=(original/'overlay/research12.tech.lef').read_text();layers={}
    for name,body in re.findall(r'(?ms)^LAYER\s+(metal\d+)\s*\n(.*?)^END\s+\1\s*$',tech):
        def value(key):return float(re.search(r'(?m)^\s*'+key+r'\s+([\d.]+)\s*;',body).group(1))
        layers[name]=dict(height=value('HEIGHT'),thickness=value('THICKNESS'),width=value('WIDTH'),rsheet=value('RESISTANCE RPERSQ'))
    boxes=set();aliases={}
    for line in(geometry/'geometry-R0.tsv').read_text().splitlines():
        if line.startswith('# NET '):
            _,_,alias,encoded=line.split();aliases[alias]=bytes.fromhex(encoded).decode();continue
        if line.startswith('#'):continue
        alias,layer,kind,*coordinates=line.split('\t');x0,y0,x1,y1=[int(v)/2000 for v in coordinates]
        if layer.startswith('metal'):
            z0=layers[layer]['height'];z1=z0+layers[layer]['thickness']
        else:
            number=int(layer.removeprefix('via'));lo=layers['metal%d'%number];hi=layers['metal%d'%(number+1)]
            z0=lo['height']+lo['thickness'];z1=hi['height']
        assert z1>z0
        boxes.add((alias,x0,y0,z0,x1,y1,z1))
    assert len(aliases)==1 and list(aliases.values())==['link']
    alias=next(iter(aliases));ox=min(b[1]for b in boxes);oy=min(b[2]for b in boxes)
    scene='background 3.9\nmaster '+alias+'\n'
    for net,x0,y0,z0,x1,y1,z1 in sorted(boxes):
        scene+='box '+net+' '+' '.join('%.12g'%v for v in [x0-ox,y0-oy,z0,x1-ox,y1-oy,z1])+'\n'
    (out/'routed-scene.txt').write_text(scene)
    solver=base/'block-v1-20261027-013/tasks/fsv-build'
    solver_receipt=json.loads((solver/'receipt.json').read_text());assert solver_receipt['passed']is True
    assert sha(solver/'fsv-qualified.json')==solver_receipt['outputs']['fsv-qualified.json']
    tool=json.loads((solver/'fsv-qualified.json').read_text());binary=Path(tool['binary']);assert sha(binary)==tool['binary_sha256']
    run([str(binary),'scene3d',str(cpus),'routed-scene.txt'],'routed-field.jsonl')
    rows=[json.loads(line)for line in(out/'routed-field.jsonl').read_text().splitlines()]
    assert rows.pop()=={'status':'PASS','mode':'scene3d'}and len(rows)==1
    row=rows[0];entries={v['net']:v for v in row['entries']}
    total=entries[alias]['cap'];ground=-entries['ground']['cap']
    assert total>0 and ground>0 and abs(total-ground)<=5*entries[alias]['sigma']+.005*total
    # Decode the real route's bounded, unbranched Manhattan grammar. Reject
    # NDR/patch/branch constructs instead of guessing their resistance.
    text=(original/'probe/routed.def').read_text()
    section=re.search(r'(?ms)^NETS\s+1\s*;(.*?)^END NETS',text).group(1)
    parts=re.split(r'\b(?:ROUTED|NEW)\s+',section)[1:]
    spec=json.loads((root/'project/experiments/block_v1/technology.json').read_text())
    edges=[];graph=defaultdict(list)
    def edge(a,b,resistance,weight):
        assert a!=b and resistance>0 and weight>0
        edges.append(dict(a=a,b=b,resistance_ohm=resistance,c_partition_weight_um=weight))
        graph[a].append(b);graph[b].append(a)
    for part in parts:
        match=re.fullmatch(r'(metal\d+)\s+(.*?)\s*;?\s*',part,re.S);assert match
        layer,body=match.groups();points=[]
        def point(match):
            x,y=match.groups();assert points or '*'not in(x,y)
            points.append((int(x)if x!='*'else points[-1][0],int(y)if y!='*'else points[-1][1]));return ''
        tail=re.sub(r'\(\s*([\d*]+)\s+([\d*]+)\s*\)',point,body).strip().rstrip(';').strip()
        if len(points)==2 and not tail:
            a,b=points;length=(abs(a[0]-b[0])+abs(a[1]-b[1]))/2000
            assert (a[0]==b[0])!=(a[1]==b[1])
            ls=layers[layer];edge((layer,*a),(layer,*b),ls['rsheet']*length/ls['width'],length)
        else:
            assert len(points)==1 and tail in ('BV1_via10','BV1_via11'),part
            number=int(tail.removeprefix('BV1_via'));xy=points[0]
            edge(('metal%d'%number,*xy),('metal%d'%(number+1),*xy),spec['electrical']['via_resistance_ohm'],spec['geometry_um']['cut_width'])
    ends=[n for n,neighbors in graph.items()if len(neighbors)==1]
    assert set(ends)=={('metal10',68800,68800),('metal10',273600,273600)}
    assert all(len(v)in(1,2)for v in graph.values())and len(edges)==len(graph)-1
    visited=set();stack=[ends[0]]
    while stack:
        node=stack.pop()
        if node not in visited:visited.add(node);stack.extend(graph[node])
    assert visited==set(graph)
    ordered=sorted(graph);node_ids={n:'*1:%d'%(i+1)for i,n in enumerate(ordered)}
    node_ids[('metal10',68800,68800)]='*2:p';node_ids[('metal10',273600,273600)]='*3:p'
    weights=defaultdict(float)
    for e in edges:
        weights[e['a']]+=e['c_partition_weight_um']/2;weights[e['b']]+=e['c_partition_weight_um']/2
    normalization=sum(weights.values());resistance=sum(e['resistance_ohm']for e in edges)
    spef='*SPEF "IEEE 1481-1998"\n*DESIGN "landing_probe"\n*DATE "2026-10-27"\n*VENDOR "LLMHardwareDesign"\n*PROGRAM "routed-field-probe"\n*VERSION "1"\n'
    spef+='*DESIGN_FLOW "DISTRIBUTED_R_LENGTH_WEIGHTED_C_CANDIDATE"\n*DIVIDER /\n*DELIMITER :\n*BUS_DELIMITER [ ]\n*T_UNIT 1 NS\n*C_UNIT 1 FF\n*R_UNIT 1 OHM\n*L_UNIT 1 UH\n'
    spef+='*NAME_MAP\n*1 link\n*2 U0\n*3 U1\n\n*D_NET *1 %.17g\n*CONN\n*I *2:p O\n*I *3:p I\n*CAP\n'%ground
    for i,n in enumerate(ordered):spef+='%d %s %.17g\n'%(i+1,node_ids[n],ground*weights[n]/normalization)
    spef+='*RES\n'
    for i,e in enumerate(edges):spef+='%d %s %s %.17g\n'%(i+1,node_ids[e['a']],node_ids[e['b']],e['resistance_ohm'])
    spef+='*END\n';(out/'routed-field.spef').write_text(spef)
    script='read_db {'+str(original/'probe/routed.odb')+'}\nbench_read_spef routed-field.spef\n'
    script+='set net [[ord::get_db_block] findNet link]\nset stream [open readback.tsv w]\nputs $stream "[$net getTotalResistance]\\t[$net getTotalCapacitance]\\t[$net getTotalCouplingCap]"\nclose $stream\nwrite_db received.odb\n'
    (out/'receive.tcl').write_text(script)
    run(['openroad','-no_init','-exit','receive.tcl'],'receive.log')
    values=list(map(float,(out/'readback.tsv').read_text().split()))
    assert all(abs(a-b)<=2e-5*max(1,abs(a))for a,b in zip([resistance,ground,0],values))
    (out/'routed-field.json').write_text(json.dumps(dict(schema='block-v1-routed-field/1',passed=True,
        geometry_sha256=sha(geometry/'geometry-R0.tsv'),gds_geometry_check_sha256=sha(geometry/'odb-geometry.json'),
        routed_def_sha256=sha(original/'probe/routed.def'),scene_sha256=sha(out/'routed-scene.txt'),solver_sha256=sha(binary),
        unique_conductor_boxes=len(boxes),graph_nodes=len(graph),graph_edges=edges,resistance_ohm=resistance,
        measured_ground_ff=ground,readback=values,
        scope='Actual routed fixed-M10 access geometry, full field total C, series DC graph and SPEF binding; local C partition is a length-weighted estimate and full-block distributed RC remains unqualified'),indent=2)+'\n')
