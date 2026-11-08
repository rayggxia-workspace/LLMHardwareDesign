"""Exact frozen-resource topology composition, under proven disjoint metal.

KLayout worker: compare actual assembled GDS subtrees to every supplied source,
including all direct geometry and hierarchy. Only when transformed conductor
bounds are strictly disjoint may source connectivity be reused. No C is reused.
"""
import json
import os
from pathlib import Path
import sys
import pya
sys.path.insert(0,str(Path(__file__).resolve().parent))
from native_inventory import sha
from resource_base import load_library
from native_identity import verify,references
from assembly_inventory import build as inventory
from native_connectivity_audit import audit


def main():
    base_path=Path(os.environ['ROUTER_ASSEMBLY_BASE'])
    library=load_library(Path(os.environ['ROUTER_RESOURCE_LIBRARY']))
    base=json.loads(base_path.read_text());native=Path(os.environ['ROUTER_NATIVE_GDS'])
    prior=Path(os.environ['ROUTER_SOURCE_TOPOLOGIES']);out=Path(os.environ['ROUTER_TOPOLOGY_OUT']);out.mkdir()
    actual=pya.Layout();actual.read(str(native));top=actual.top_cell()
    assert all(top.shapes(i).is_empty() for i in actual.layer_indices()),'unexpected assembled-root conductor'
    factor=base['dbu_per_micron']*actual.dbu
    expected=[]
    for a in base['assemblies']:
        xy=[v/factor for v in a['translation_dbu']]
        assert all(abs(v-round(v))<1e-8 for v in xy)
        expected.append(('RESOURCE_'+a['template'],str(pya.ICplxTrans(1,0,False,*map(round,xy))),
                         0,0,str(pya.Vector()),str(pya.Vector())))
    assert references(top)==sorted(expected),'actual assembly placement/identity differs'
    sources={};identities={};bboxes={};allowed={top.name}
    for name in sorted({a['template'] for a in base['assemblies']}):
        resource=library[name];source=Path(resource['views']['gds']['path'])
        receipt=prior/name/'topology.json';meta=json.loads(receipt.read_text());database=receipt.with_name('native.l2n')
        assert meta['passed'] and meta['source_gds']['sha256']==sha(source)
        assert meta['database_sha256']==sha(database)
        assert meta['inventory_sha256']==resource['inventory_sha256']
        audit(resource['inventory'],meta)
        reference=pya.Layout();reference.read(str(source));original=reference.top_cell()
        assert reference.dbu==actual.dbu,'source grid differs'
        # copy_tree exports only reachable physical cells, as the original
        # assembly does. Uninstantiated library definitions have no geometry.
        for cell in reference.each_cell():cell.name='SRC_'+name+'_'+cell.name
        original.name='RESOURCE_'+name
        pruned=pya.Layout();pruned.dbu=reference.dbu
        pruned.create_cell(original.name).copy_tree(original)
        observed=pya.Layout();observed.dbu=actual.dbu
        observed.create_cell(original.name).copy_tree(actual.cell(original.name))
        identities[name]=verify(pruned,observed,None)
        allowed.update(c.name for c in pruned.each_cell())
        box=pya.Box()
        for layer in list(range(11,30,2))+list(range(12,29,2)):
            index=reference.find_layer(layer,0)
            if index is not None:
                region=pya.Region(original.begin_shapes_rec(index));box=box+region.bbox()
        assert not box.empty(),'source has no native conductors'
        bboxes[name]=[box.left,box.bottom,box.right,box.top]
        sources[name]={'path':str(receipt),'sha256':sha(receipt),'database':str(database),
                       'database_sha256':sha(database),'source_gds':resource['views']['gds']}
        print('SOURCE_IDENTITY_AND_TOPOLOGY',name,identities[name],flush=True)
        reference._destroy();pruned._destroy();observed._destroy()
    assert {c.name for c in actual.each_cell()}==allowed,'unexpected native GDS cell'
    placed={}
    for a in base['assemblies']:
        dx,dy=[round(v/factor) for v in a['translation_dbu']];b=bboxes[a['template']]
        placed[a['id']]=[b[0]+dx,b[1]+dy,b[2]+dx,b[3]+dy]
    minimum=None
    for name,b in placed.items():
        for other,c in placed.items():
            if other>=name:continue
            dx=max(b[0]-c[2],c[0]-b[2],0);dy=max(b[1]-c[3],c[1]-b[3],0)
            assert dx>0 or dy>0,('native conductor bounds touch/overlap',name,other)
            distance=dx+dy;minimum=distance if minimum is None else min(minimum,distance)
    inv=inventory(base,library,native);inv_path=out/'inventory.json';inv_path.write_text(json.dumps(inv,indent=2)+'\n')
    probes={};power=[]
    for a in base['assemblies']:
        group=a['id'];meta=json.loads(Path(sources[a['template']]['path']).read_text())
        dx,dy=[v/base['dbu_per_micron'] for v in a['translation_dbu']]
        for name,row in meta['boundary_probes'].items():
            full=group+'/'+name;assert full in base['endpoints']
            probes[full]={'native_net':base['endpoints'][full]['native_net'],
                'probes':[{'point_um':[p['point_um'][0]+dx,p['point_um'][1]+dy],
                           'token':[group,p['token']]} for p in row['probes']]}
        for p in meta['power_probes']:
            power.append({**p,'label':group+'/'+p['label'],'point_um':[p['point_um'][0]+dx,p['point_um'][1]+dy],
                          'token':[group,p['token']]})
    result={'schema_version':'composed-native-topology/1','source_gds':{'path':str(native),'sha256':sha(native)},
        'inventory_sha256':sha(inv_path),'base_file':str(base_path),'base_sha256':sha(base_path),
        'dbu':actual.dbu,'dbu_per_micron':base['dbu_per_micron'],'top':top.name,
        'sources':sources,'source_hierarchy_identity':identities,'source_conductor_bboxes':bboxes,
        'placed_conductor_bboxes':placed,'minimum_component_bbox_gap_um':None if minimum is None else minimum*actual.dbu,
        'assemblies':base['assemblies'],'boundary_probes':probes,'power_probes':power,
        'passed':True,'native_components_strictly_disjoint':True,
        'scope':'exact source extraction reused only under actual-GDS subtree identity and strictly disjoint conductor bounds; no capacitance reused'}
    result['connectivity_audit']=audit(inv,result)
    (out/'topology.json').write_text(json.dumps(result,indent=2)+'\n')
    print('COMPOSED_TOPOLOGY_PASSED',len(probes),minimum,flush=True)


if __name__=='__main__':main()
