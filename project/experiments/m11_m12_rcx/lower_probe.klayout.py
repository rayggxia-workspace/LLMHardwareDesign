"""Resolve individually named near-upper native electrodes in existing L2N.

M8--M10 selection is an explicitly bounded first extraction tier. Lower-tier
nets are counted, never declared unaffected merely because they were omitted.
"""
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import sys
import time
import pya

KINDS=('C0','F0','J0','P0','T0','U0')
RECORD=struct.Struct('<ii6d')
BASE=Path('/public/home/yuzelu/PingyangHuang')
SCENE=BASE/'issue-222-coupling-DuSb4uk1/job-100170/result'

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(8<<20),b''):h.update(b)
    return h.hexdigest()

def run():
    started=time.monotonic();index=int(os.environ['LOWER_INDEX'])
    config_path=Path(os.environ.get('LOWER_CONFIG',str(Path(os.environ['LOWER_TASK_ROOT'])/'work/huangpingyang04-lgtm/222/lower-rc/lower-inputs.json')))
    config=json.loads(config_path.read_text())
    case=config['cases'][index] if 'cases' in config else {}
    kind=case.get('root_kind',KINDS[index]);label=case.get('label',kind)
    minimum=int(config.get('minimum_highest_metal',8));assert 1<=minimum<=10
    out=Path(os.environ['LOWER_OUT']);out.mkdir()
    inv=Path(case['inventory'] if case else config['inventories'][kind]);imeta=json.loads((inv/'inventory.json').read_text())
    assert imeta['kind']==case.get('source_kind',kind) and sha(inv/'net-inventory.jsonl.gz')==imeta['inventory_sha256']
    def parent_point(point):
        if 'transform' not in case:return point
        t=case['transform'];return [t['offset_um'][d]+sum(t['matrix'][d][k]*point[k] for k in range(2)) for d in range(2)]
    records=[]
    with gzip.open(inv/'net-inventory.jsonl.gz','rt') as f:
        for line in f:
            row=json.loads(line)
            if case:row['relative_instance_path']=case['instance_path']
            if row['highest_metal']>=minimum:records.append(row)
    meta=json.loads((SCENE/'scene.json').read_text());source=meta['sources'][kind]
    manifest=Path(source['source_topology']);assert sha(manifest)==source['source_topology_sha256']
    topology=json.loads(manifest.read_text());database=manifest.with_name('native.l2n')
    assert sha(database)==topology['database_sha256']
    l2n=pya.LayoutToNetlist();l2n.read(str(database));objects={}
    def probe(layer,point):
        hierarchy=[];net=l2n.probe_net(l2n.layer_by_name(layer),pya.DPoint(*point),hierarchy)
        assert net is not None,(kind,layer,point)
        transform=pya.DCplxTrans();path=[]
        for sub in hierarchy:
            transform=transform*sub.trans;path.append((sub.circuit_ref().name,str(sub.trans)))
        key=(net.circuit().name,int(net.cluster_id),tuple(path))
        objects.setdefault(key,(net,pya.ICplxTrans(transform,topology['dbu'])))
        return key
    # Resolve grounded electrodes using already accepted top-level VDD/VSS
    # ports and verify every PG candidate, rather than treating an OBS as PG.
    ports=json.loads((inv/'ports.json').read_text());pg=set()
    by_name={r['name']:r for r in records}
    with gzip.open(inv/'net-inventory.jsonl.gz','rt') as f:
        for line in f:
            row=json.loads(line)
            if any(p in row.get('ports',[]) for p in ['VDD','VSS']):
                pg.add(probe(row['probe_layer'],parent_point(row['probe'])))
    assert pg,(kind,'No grounded electrode identity')
    refs=json.loads((BASE/'issue-215-top-pex-zOz2uxIr/route-206.json').read_text())
    binding=json.loads(Path(refs['artifacts']['case-binding.json']['path']).read_text())['endpoints']
    boundaries={}
    for word,ends in binding.items():
        for instance,pin in ends:
            if instance!=kind:continue
            key=probe('metal10',topology['boundary_probes'][pin]['point_um'])
            assert key not in pg
            old=boundaries.setdefault(key,word);assert old==word
    previously_selected=set();previous_proof=[]
    previous_paths=case.get('previous_probes',[])
    if kind in config.get('previous_probes',{}):previous_paths=[*previous_paths,config['previous_probes'][kind]]
    for prior in previous_paths:
        previous=Path(prior);old=json.loads((previous/'probe.json').read_text())
        assert old['source_topology_sha256']==sha(manifest)
        assert sha(previous/'targets.json')==old['targets_sha256']
        added={json.dumps(t['physical_token'],sort_keys=True) for t in json.loads((previous/'targets.json').read_text())}
        previously_selected.update(added)
        previous_proof.append(dict(path=str(previous),probe_sha256=sha(previous/'probe.json'),previously_selected_electrodes=len(added)))
    groups={};excluded=[]
    for row in records:
        key=probe(row['probe_layer'],parent_point(row['probe']))
        if key in pg:excluded.append(dict(name=row['name'],reason='grounded_power'));continue
        if key in boundaries:excluded.append(dict(name=row['name'],reason='original_boundary',word=boundaries[key]));continue
        if json.dumps(key,sort_keys=True) in previously_selected:
            excluded.append(dict(name=row['name'],reason='already_selected_previous_tier'));continue
        groups.setdefault(key,[]).append(row)
    tech=Path(refs['research_tech_lef']['path']).read_text();z={}
    for name,body in re.findall(r'(?ms)^LAYER\s+(metal\d+)\s*\n(.*?)^END\s+\1\s*$',tech):
        h=float(re.search(r'(?m)^\s*HEIGHT\s+([\d.]+)',body)[1]);t=float(re.search(r'(?m)^\s*THICKNESS\s+([\d.]+)',body)[1]);z[name]=(h,h+t)
    for level in range(1,10):z['via'+str(level)]=(z['metal'+str(level)][1],z['metal'+str(level+1)][0])
    targets=[];boxes=0
    with (out/'selected-boxes.bin').open('xb') as stream:
        for index,(key,aliases) in enumerate(groups.items()):
            net,transform=objects[key];counts={};volume=0.
            for layer in [*['metal'+str(i) for i in range(1,11)],*['via'+str(i) for i in range(1,10)]]:
                region=l2n.shapes_of_net(net,l2n.layer_by_name(layer),True,transform)
                count=0;z0,z1=z[layer]
                for poly in region.each_merged():
                    for piece in poly.decompose_trapezoids(0):
                        b=piece.bbox();assert b.area()==piece.area(),(kind,layer,'Unsupported nonrectangle')
                        coords=[b.left*topology['dbu'],b.bottom*topology['dbu'],z0,b.right*topology['dbu'],b.top*topology['dbu'],z1]
                        stream.write(RECORD.pack(index,1,*coords));count+=1;boxes+=1
                        volume+=(coords[3]-coords[0])*(coords[4]-coords[1])*(z1-z0)
                counts[layer]=count
            assert sum(counts.values())>0
            targets.append(dict(local_id=index,physical_token=key,aliases=aliases,layer_box_counts=counts,volume_um3=volume))
            if index%100==0:print('NATIVE_TARGET',kind,index,len(groups),boxes,flush=True)
    (out/'targets.json').write_text(json.dumps(targets,indent=2)+'\n')
    (out/'excluded.json').write_text(json.dumps(excluded,indent=2)+'\n')
    report=dict(kind=kind,inventory_kind=label,minimum_highest_metal=minimum,selected_input_nets=len(records),selected_physical_electrodes=len(targets),excluded_nets=len(excluded),
        boundary_electrodes=len(boundaries),grounded_electrodes=len(pg),selected_boxes=boxes,
        inventory=str(inv/'inventory.json'),inventory_sha256=sha(inv/'inventory.json'),source_topology=str(manifest),source_topology_sha256=sha(manifest),
        selected_boxes_sha256=sha(out/'selected-boxes.bin'),targets_sha256=sha(out/'targets.json'),elapsed_seconds=time.monotonic()-started,
        original_inventory_nets=imeta['native_net_count'],original_highest_metal_counts=imeta['highest_metal_counts'],
        previous_tier=previous_proof,configuration_sha256=sha(config_path),
        not_selected_lower_layers=('All root ODB nets considered; earlier-tier and boundary exclusions are explicit. Nested-only child internal nets remain outside this inventory.' if minimum==1 else 'Not declared unaffected. Additional extraction tiers and nested-only internal nets are outside this first tier.'),
        scope='Exact existing GDS conductor identity and whole M1-M10 shapes for explicitly selected original ODB nets; no field result yet.')
    (out/'probe.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)

run()
