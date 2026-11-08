"""Build a field scene from real native GDS topology and unchanged upper boxes.

Non-interface native signal electrodes are grouped per instance only because
they all have potential zero in each upper-master Maxwell excitation. Such
aggregate columns are diagnostics, never physical signal shorts or SPEF nets.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import time
import pya
sys.path.insert(0,str(Path(__file__).resolve().parent))
from native_scene import SceneWriter


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for b in iter(lambda:stream.read(4 << 20),b''):
            digest.update(b)
    return digest.hexdigest()


def export():
    out = Path(os.environ['COUPLING_OUT'])/'result'
    out.mkdir()
    manifests = json.loads(Path(os.environ['COUPLING_TOPOLOGIES']).read_text())
    minimum = int(os.environ['COUPLING_MIN_LAYER'])
    assert 1 <= minimum <= 10
    references = Path('/public/home/yuzelu/PingyangHuang/issue-215-top-pex-zOz2uxIr/route-206.json')
    refs = json.loads(references.read_text())
    binding = json.loads(Path(refs['artifacts']['case-binding.json']['path']).read_text())['endpoints']
    upper_path = Path('/public/home/yuzelu/PingyangHuang/issue-215-top-pex-zOz2uxIr/job-99157/result/conductors.json')
    assert sha(upper_path) == 'e5839aceea9676633a030a78de98ad9a7f196e56deb812a6fc819b950be49c9f'
    upper = json.loads(upper_path.read_text())
    names = [v['name'] for v in upper]
    assert names == sorted(binding) and len(names) == 2491
    ids = {n:i for i,n in enumerate(names)}
    instances = sorted(refs['native_masks'])
    names += ['NATIVE_SIGNALS_'+n for n in instances] + ['AC_GROUND_PG']
    pg = len(names)-1
    other = {n:2491+i for i,n in enumerate(instances)}
    scene = SceneWriter(out/'scene.bin',names,grounded=[pg])
    lower_scene = SceneWriter(out/'lower-only.bin',names,grounded=[pg])
    for i,row in enumerate(upper):
        for box in row['boxes']:
            scene.add(i,0,box)
    technology = Path(refs['research_tech_lef']['path']).read_text()
    z = {}
    for name,body in re.findall(r'(?ms)^LAYER\s+(metal\d+)\s*\n(.*?)^END\s+\1\s*$',technology):
        h=float(re.search(r'(?m)^\s*HEIGHT\s+([\d.]+)',body)[1])
        t=float(re.search(r'(?m)^\s*THICKNESS\s+([\d.]+)',body)[1])
        z[name]=(h,h+t)
    for i in range(1,10):
        z['via'+str(i)]=(z['metal'+str(i)][1],z['metal'+str(i+1)][0])
    report={}
    started=time.monotonic()
    for kind, manifest_name in sorted(manifests.items()):
        path=Path(manifest_name)
        manifest=json.loads(path.read_text())
        assert manifest['kind']==kind and manifest['layout_to_netlist_controls']['passed']
        database=path.with_name('native.l2n')
        assert sha(database)==manifest['database_sha256']
        l2n=pya.LayoutToNetlist()
        l2n.read(str(database))
        electrode_objects={}

        def probe(layer,point):
            hierarchy=[]
            net=l2n.probe_net(l2n.layer_by_name(layer),point,hierarchy)
            assert net is not None,(kind,layer,str(point))
            transform=pya.DCplxTrans()
            path=[]
            for sub in hierarchy:
                transform=transform*sub.trans
                path.append((sub.circuit_ref().name,str(sub.trans)))
            token=(net.circuit().name,int(net.cluster_id),tuple(path))
            electrode_objects.setdefault(token,(net,pya.ICplxTrans(transform,manifest['dbu'])))
            return token

        # L2N may renumber clusters when serialized. Re-probe coordinates
        # after loading, and retain the subcircuit path for pins inside a leaf.
        power=set()
        original=pya.Layout()
        original.read(manifest['source_gds']['path'])
        original_top=original.top_cell()
        for level in range(1,11):
            index=original.find_layer(9+2*level,0)
            if index is None:continue
            for shape in original_top.shapes(index).each():
                if shape.is_text() and shape.text.string in ('VDD','VSS'):
                    p=shape.text.trans.disp
                    power.add(probe('metal'+str(level),pya.DPoint(p.x*original.dbu,p.y*original.dbu)))
        assert power,(kind,'No verified PG probes')
        original._destroy()
        kind_instances=[n for n in instances if n[0]==kind[0]]
        netmap={n:{} for n in kind_instances}
        for word, ends in binding.items():
            for instance,pin in ends:
                if instance not in netmap: continue
                cluster=probe('metal10',pya.DPoint(*manifest['boundary_probes'][pin]['point_um']))
                assert cluster not in power, (instance,pin,'Signal is shorted to PG')
                previous=netmap[instance].setdefault(cluster,ids[word])
                assert previous==ids[word], (instance,pin,'Different upper nets share native conductor')
        print('BOUND',kind,'native interface electrodes',len(electrode_objects),'circuits',sorted({key[0] for key in electrode_objects}),flush=True)
        counts={};polygons=0;rectangles=0
        tracked=power | {cluster for entries in netmap.values() for cluster in entries}
        assert tracked <= set(electrode_objects)

        def emit(part, layer, cluster):
            nonlocal polygons,rectangles
            z0,z1=z[layer]
            for poly in part.each_merged():
                pieces=poly.decompose_trapezoids(0)
                polygons+=1
                for piece in pieces:
                    box=piece.bbox()
                    assert piece.area()==box.area(), (kind,layer,'Nonrectangular conductor needs exact support')
                    for instance in kind_instances:
                        ox,oy=refs['positions_um'][instance]
                        coords=[box.left*manifest['dbu']+ox,box.bottom*manifest['dbu']+oy,z0,
                                box.right*manifest['dbu']+ox,box.top*manifest['dbu']+oy,z1]
                        electrode=pg if cluster in power else netmap[instance].get(cluster,other[instance])
                        scene.add(electrode,1,coords)
                        lower_scene.add(electrode,1,coords)
                    rectangles+=1;counts[layer]+=1

        for layer in ['metal'+str(i) for i in range(minimum,11)]+['via'+str(i) for i in range(minimum,10)]:
            region=l2n.layer_by_name(layer)
            counts[layer]=0
            selected=pya.Region()
            tracked_area=0
            for cluster in sorted(tracked):
                net,transform=electrode_objects[cluster]
                part=l2n.shapes_of_net(net,region,True,transform)
                tracked_area+=part.area()
                selected+=part
                emit(part,layer,cluster)
            selected.merge()
            assert selected.area()==tracked_area, (kind,layer,'Distinct tracked conductors overlap')
            remaining=region-selected
            assert ((remaining+selected)^region).is_empty(), (kind,layer,'Conductor partition changed native geometry')
            emit(remaining,layer,None)
            print('EXPORTED',kind,layer,counts[layer],flush=True)
        report[kind]=dict(source_topology=str(path),source_topology_sha256=sha(path),
                          source_gds=manifest['source_gds'],instances=kind_instances,
                          polygons=polygons,rectangles_per_instance=rectangles,layer_rectangles=counts,
                          boundary_net_counts={n:len(v) for n,v in netmap.items()})
    scene.close();lower_scene.close()
    included=sorted(n for record in report.values() for n in record['instances'])
    result=dict(minimum_native_layer=minimum,native_layers=list(range(minimum,11)),
                included_native_instances=included,complete_native_instance_context=(included==instances),
                upper_net_count=2491,electrode_names=names,box_count=scene.count,
                scene_sha256=sha(out/'scene.bin'),lower_scene_sha256=sha(out/'lower-only.bin'),
                source_upper_sha256=sha(upper_path),sources=report,
                elapsed_seconds=time.monotonic()-started,
                qualification='Preparation only. Depth convergence, field controls, statistical errors and timing comparison remain separate.')
    (out/'scene.json').write_text(json.dumps(result,indent=2)+'\n')
    (out/'masters.txt').write_text('\n'.join(map(str,range(2491)))+'\n')
    (out/'pilot-masters.txt').write_text('0\n1960\n1974\n')
    print(json.dumps({k:v for k,v in result.items() if k!='electrode_names'}),flush=True)


export()
