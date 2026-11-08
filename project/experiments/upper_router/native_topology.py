"""Extract actual frozen M1--M10 conductors, including nested leaf cells.

KLayout worker entry point. Based on the physical-connectivity method in
PR225 native_topology.py; paths, counts and endpoint names are input data.
"""
import hashlib
import json
import os
from pathlib import Path
import time
import pya


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(4<<20),b''):h.update(b)
    return h.hexdigest()


def main():
    started=time.monotonic()
    inventory_path=Path(os.environ['ROUTER_NATIVE_INVENTORY'])
    inv=json.loads(inventory_path.read_text())
    source=Path(os.environ['ROUTER_NATIVE_GDS'])
    assert sha(source)==inv['files']['native/6_final.gds']['sha256']
    out=Path(os.environ['ROUTER_TOPOLOGY_OUT']);out.mkdir()
    layout=pya.Layout();layout.read(str(source));top=layout.top_cell()
    # A geometry-free root is omitted from the extracted netlist, losing the
    # identity of repeated template instances. Keep the hierarchy by giving
    # the extraction root a duplicate of an EXISTING real conductor. Prove its
    # union is unchanged; no dummy conductor or physical source edit is made.
    empty_root=not any(not top.shapes(i).is_empty() for i in layout.layer_indices())
    mode=os.environ.get('ROUTER_TOPOLOGY_ROOT_MODE','duplicate_conductor')
    assert mode in ('duplicate_conductor','promote')
    promoted=False;root_attachment=None
    if empty_root and mode=='promote':
        top.flatten(1);promoted=True
    elif empty_root:
        layer=layout.find_layer(29,0);assert layer is not None
        candidates=[(name,s['rect']) for name,t in sorted(inv['terms'].items())
                    for s in t['shapes'] if s['layer']=='metal10']
        assert candidates,'empty extraction root requires a declared real conductor'
        factor=inv['dbu_per_micron']*layout.dbu
        boxes=[];attachment=pya.Region()
        # Attach every declared M10 terminal, so repeated source instances
        # cannot disappear as floating subcircuits of an otherwise empty root.
        for name,rect in candidates:
            points=[v/factor for v in rect]
            assert all(abs(v-round(v))<1e-8 for v in points),'root attachment would round'
            box=pya.Box(*map(round,points));boxes.append(box);attachment.insert(box)
        before=pya.Region(top.begin_shapes_rec(layer))
        assert (attachment-before).is_empty(),'root attachment is not actual native metal'
        for box in boxes:top.shapes(layer).insert(box)
        after=pya.Region(top.begin_shapes_rec(layer))
        assert (before^after).is_empty(),'extraction root attachment changes conductor union'
        root_attachment={'terminals':sorted({name for name,rect in candidates}),
                         'rectangles':len(boxes),'layer':'metal10',
                         'native_metal_union_xor_zero':True}
        print('ROOT_REAL_CONDUCTOR_ATTACHMENT',len(boxes),flush=True)
    l2n=pya.LayoutToNetlist(top.begin_shapes_rec(layout.layer(11,0)))
    l2n.threads=int(os.environ.get('OMP_NUM_THREADS','1'))
    regions={};counts={}
    for prefix,last in [('metal',10),('via',9)]:
        for i in range(1,last+1):
            name=prefix+str(i);index=layout.find_layer((9 if prefix=='metal' else 10)+2*i,0)
            r=l2n.make_polygon_layer(index,name) if index is not None else l2n.make_layer(name)
            regions[name]=r;counts[name]=r.count();l2n.connect(r)
    for i in range(1,10):
        l2n.connect(regions['metal'+str(i)],regions['via'+str(i)])
        l2n.connect(regions['via'+str(i)],regions['metal'+str(i+1)])
    print('EXTRACT_CONNECTIVITY',source,flush=True)
    l2n.extract_netlist();print('CONNECTIVITY_EXTRACTED',time.monotonic()-started,flush=True)
    l2n.write(str(out/'native.l2n'));print('CONNECTIVITY_SAVED',flush=True)
    assert [c.name for c in l2n.netlist().top_circuits()]==[top.name], 'ambiguous extraction root'
    def probe(layer,point):
        hierarchy=[];net=l2n.probe_net(regions[layer],point,hierarchy)
        assert net is not None,(layer,str(point))
        assert all(s is not None for s in hierarchy),'unresolved extraction hierarchy'
        return [net.circuit().name,int(net.cluster_id),
                [[s.circuit_ref().name,str(s.trans)] for s in hierarchy]]
    probes={}
    for name,term in inv['terms'].items():
        if term['signal_type']!='SIGNAL':continue
        shapes=[s for s in term['shapes'] if s['layer']=='metal10']
        if not shapes:continue
        observed=[]
        for s in shapes:
            a,b,c,d=s['rect'];point=[(a+c)/2/inv['dbu_per_micron'],(b+d)/2/inv['dbu_per_micron']]
            token=probe('metal10',pya.DPoint(*point))
            observed.append({'point_um':point,'token':token})
        assert all(p['token']==observed[0]['token'] for p in observed),('split native pin',name)
        probes[name]={'native_net':term['native_net'],'probes':observed}
    by_native={};by_cluster={}
    for name,row in probes.items():
        token=json.dumps(row['probes'][0]['token'])
        previous=by_native.setdefault(row['native_net'],token)
        assert previous==token,('disconnected native net',name)
        previous=by_cluster.setdefault(token,row['native_net'])
        assert previous==row['native_net'],('native short',name,previous)
    power=[]
    for name,term in inv['terms'].items():
        if term['signal_type'] not in ('POWER','GROUND'):continue
        for s in term['shapes'][:1]:
            a,b,c,d=s['rect'];point=[(a+c)/2/inv['dbu_per_micron'],(b+d)/2/inv['dbu_per_micron']]
            power.append({'label':name,'layer':s['layer'],'point_um':point,
                          'token':probe(s['layer'],pya.DPoint(*point))})
    for i in range(1,11):
        index=layout.find_layer(9+2*i,0)
        if index is None:continue
        for shape in top.shapes(index).each():
            if shape.is_text() and shape.text.string in ('VDD','VSS'):
                p=shape.text.trans.disp;point=[p.x*layout.dbu,p.y*layout.dbu]
                power.append({'label':shape.text.string,'layer':'metal'+str(i),
                              'point_um':point,'token':probe('metal'+str(i),pya.DPoint(*point))})
    assert power,'native PG probes absent'
    power_tokens={json.dumps(p['token']) for p in power}
    assert not power_tokens.intersection(by_cluster),'signal physically shorted to PG'
    result={'source_gds':{'path':str(source),'sha256':sha(source)},
            'inventory_sha256':sha(inventory_path),'dbu':layout.dbu,'top':top.name,
            'database_sha256':sha(out/'native.l2n'),'shape_counts':counts,
            'extraction_only_promoted_root_children':promoted,
            'extraction_only_root_attachment':root_attachment,
            'boundary_probes':probes,'power_probes':power,'passed':True,
            'elapsed_seconds':time.monotonic()-started,
            'scope':'exact frozen M1--M10/via1--9 connectivity, including nested macros; no device/poly extraction'}
    (out/'topology.json').write_text(json.dumps(result,indent=2)+'\n')
    print('PASSED',len(probes),result['elapsed_seconds'],flush=True)


if __name__=='__main__':main()
