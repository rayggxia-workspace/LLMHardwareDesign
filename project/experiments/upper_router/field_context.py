"""KLayout: exact native conductors plus fresh routed conductors for field RC.

All native metal is present, including nested cells. Unselected native signals
share zero Maxwell excitation, not a physical net. No macro OBS is conductor.
"""
import json
import os
from pathlib import Path
import struct
import sys
import pya
sys.path.insert(0,str(Path(__file__).resolve().parent))
from native_topology import sha


def main():
    out=Path(os.environ['ROUTER_FIELD_OUT']);out.mkdir()
    handoff=Path(os.environ['ROUTER_HANDOFF'])
    topology=Path(os.environ['ROUTER_TOPOLOGY'])
    meta=json.loads((topology/'topology.json').read_text())
    assert meta['passed'] and sha(topology/'native.l2n')==meta['database_sha256']
    binding=json.loads((handoff/'bindings.json').read_text())
    graph=json.loads(Path(os.environ['ROUTER_RC_GRAPH']).read_text())
    l2n=pya.LayoutToNetlist();l2n.read(str(topology/'native.l2n'))
    names=sorted(binding['nets']);ids={n:i for i,n in enumerate(names)}
    names+=['NATIVE_OTHER_SIGNALS','PG'];pg=len(names)-1;other=pg-1
    # Heights/thicknesses come from the accepted research technology LEF.
    import re
    tech=Path(os.environ['ROUTER_TECH_LEF']);raw=tech.read_text();z={}
    for name,body in re.findall(r'(?ms)^LAYER\s+(metal\d+)\s*\n(.*?)^END\s+\1\s*$',raw):
        h=float(re.search(r'(?m)^\s*HEIGHT\s+([\d.]+)',body)[1])
        t=float(re.search(r'(?m)^\s*THICKNESS\s+([\d.]+)',body)[1]);z[name]=[h,h+t]
    for i in range(1,12):z['via'+str(i)]=[z['metal'+str(i)][1],z['metal'+str(i+1)][0]]
    scale=binding['dbu_per_micron'];nodes=[]
    for name in names[:other]:
        row=graph['nets'][binding['nets'][name]['logical_net']]
        nodes.append([[p['at_dbu'][0]/scale,p['at_dbu'][1]/scale,
                       sum(z['metal'+p['layer'][1:]])/2] for p in row['nodes']])
    native_bin=max(map(len,nodes));nodes.extend([[],[]])
    tracked={};objects={}
    def probe(layer,point):
        hierarchy=[];net=l2n.probe_net(l2n.layer_by_name(layer),pya.DPoint(*point),hierarchy)
        assert net is not None
        assert all(sub is not None for sub in hierarchy),'unresolved extraction hierarchy'
        transform=pya.DCplxTrans()
        for sub in hierarchy:transform=transform*sub.trans
        token=(net.circuit().name,int(net.cluster_id),tuple((s.circuit_ref().name,str(s.trans)) for s in hierarchy))
        objects.setdefault(token,(net,pya.ICplxTrans(transform,meta['dbu'])))
        return token
    for name,net in binding['nets'].items():
        for port in [net['driver']]+net['sinks']:
            point=meta['boundary_probes'][port]['probes'][0]['point_um']
            token=probe('metal10',point)
            assert tracked.setdefault(token,ids[name])==ids[name]
    for p in meta['power_probes']:
        token=probe(p['layer'],p['point_um'])
        assert token not in tracked;tracked[token]=pg
    stream=(out/'scene.bin').open('xb');stream.write(struct.pack('<8sIQdI',b'UPPERR23',len(names),0,3.9,native_bin))
    for index,name in enumerate(names):
        value=name.encode();stream.write(struct.pack('<I',len(value)));stream.write(value)
        stream.write(struct.pack('<BI',index==pg,len(nodes[index])))
        for node in nodes[index]:stream.write(struct.pack('<3d',*node))
    count=0;counts={}
    def add(net,group,box):
        nonlocal count
        assert all(box[i]<box[i+3] for i in range(3))
        stream.write(struct.pack('<ii6d',net,group,*box));count+=1
    include_upper=os.environ.get('ROUTER_INCLUDE_UPPER','1')=='1'
    for name,rows in (binding['expected_shapes'].items() if include_upper else []):
        index=ids[name]
        for layer,rect in rows:
            physical={'V10':'via10','V11':'via11','M11':'metal11','M12':'metal12'}[layer]
            a,b,c,d=[x/scale for x in rect];lo,hi=z[physical]
            center=[(a+c)/2,(b+d)/2,(lo+hi)/2]
            node=min(range(len(nodes[index])),key=lambda i:sum((nodes[index][i][k]-center[k])**2 for k in range(3)))
            add(index,node,[a,b,lo,c,d,hi])
    upper_count=count
    all_layers=['metal'+str(i) for i in range(1,11)]+['via'+str(i) for i in range(1,10)]
    layers=os.environ.get('ROUTER_NATIVE_LAYERS',','.join(all_layers)).split(',')
    assert layers and len(set(layers))==len(layers) and set(layers)<=set(all_layers)
    for layer in layers:
        region=l2n.layer_by_name(layer);selected=pya.Region();area=0;counts[layer]=0
        def emit(part,index):
            lo,hi=z[layer]
            for poly in part.each_merged():
                for piece in poly.decompose_trapezoids(0):
                    box=piece.bbox();assert piece.area()==box.area(),'nonrectangular conductor unsupported'
                    add(index,native_bin,[box.left*meta['dbu'],box.bottom*meta['dbu'],lo,
                                          box.right*meta['dbu'],box.top*meta['dbu'],hi]);counts[layer]+=1
        for token,index in tracked.items():
            net,transform=objects[token];part=l2n.shapes_of_net(net,region,True,transform)
            area+=part.area();selected+=part;emit(part,index)
        selected.merge();assert selected.area()==area,'native tracked conductors overlap'
        remaining=region-selected
        assert ((remaining+selected)^region).is_empty(),'native geometry partition changed'
        emit(remaining,other)
        print('EXPORTED',layer,counts[layer],flush=True)
    stream.seek(12);stream.write(struct.pack('<Q',count));stream.close()
    result={'scene_sha256':sha(out/'scene.bin'),'topology_sha256':sha(topology/'topology.json'),
            'graph_sha256':sha(os.environ['ROUTER_RC_GRAPH']),'tech_sha256':sha(tech),
            'names':names,'node_counts':list(map(len,nodes)),'native_origin_bin':native_bin,
            'grounded_indices':[pg],'native_signal_indices':[other],
            'boxes':count,'upper_boxes':upper_count,'native_layer_rectangles':counts,
            'complete_native_context':set(layers)==set(all_layers) and include_upper,
            'scope':'exact frozen M1--M10 and fresh upper conductors; field solve and electrical gates not yet run'}
    (out/'scene.json').write_text(json.dumps(result,indent=2)+'\n')
    (out/'masters.txt').write_text('\n'.join(map(str,range(other)))+'\n')
    print(json.dumps(result),flush=True)


main()
