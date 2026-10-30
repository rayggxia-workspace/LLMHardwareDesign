"""Read exact current630 routes before considering same-net via replacements.

This exports observed paths and conservative eligibility only; no layout edits,
native DRC, terminal-connectivity or timing qualification are claimed.
"""
from collections import defaultdict
import json


def inspect(root,out,cpus,run):
    from io_slots import file_sha
    from native_escape import records
    from revision300_v_transition import decode
    from revision300_v_via_batch import name_of,token_hash,pairs,contains
    from revision300_v_clearance_corners import intersect,outside_area
    assert cpus==16
    base=out.parents[2]
    prior=base/'block-v1-20261031-655/tasks/revision300-v-repaired-neighborhood'
    receipt=json.loads((prior/'receipt.json').read_text());assert receipt['passed']
    for n in ('revision300-v-current-neighborhood.json','neighborhood.tsv','net-aliases.tsv','layer-dimensions.tsv','via-footprints.tsv'):
        assert file_sha(prior/n)==receipt['outputs'][n]
    report=json.loads((prior/'revision300-v-current-neighborhood.json').read_text())
    assert report['passed']and report['source_native_count']==471 and report['original_inputs_unchanged']
    source=base/'block-v1-20261031-630/tasks/revision300-final-source-v'
    assert str(source)==report['source_final_task']and file_sha(source/'receipt.json')==report['source_receipt_sha256']
    results=source/'flow/results/nangate45/bv1_block_v1_v/base'
    for n,h in report['source_inputs_sha256'].items():assert file_sha(results/n)==h
    wanted={m['net']for m in report['markers']};nets={};count=0
    for record in records(results/'6_final.def'):
        count+=1;name=name_of(record)
        if name not in wanted:continue
        assert name not in nets
        header,paths,rects=decode(record)
        nets[name]=dict(header=header,nonrect_paths=paths,rectangles=list(rects.elements()),
                        original_record_token_sha256=token_hash(record))
    assert set(nets)==wanted and count==report['normal_net_count']
    aliases={bytes.fromhex(v).decode().replace('\\',''):a for a,v in(line.split('\t')for line in(prior/'net-aliases.tsv').read_text().splitlines())}
    shapes=defaultdict(list)
    for line in(prior/'neighborhood.tsv').read_text().splitlines():
        if not line or line.startswith('#'):continue
        i,alias,layer,kind,*box=line.split('\t')
        shapes[int(i)].append(dict(alias=alias,layer=layer,shape=kind,bbox_dbu=list(map(int,box))))
    dimensions={l:(int(w),int(s))for l,w,s in(line.split('\t')for line in(prior/'layer-dimensions.tsv').read_text().splitlines())}
    footprints=defaultdict(list)
    for line in(prior/'via-footprints.tsv').read_text().splitlines():
        name,layer,*box=line.split('\t');footprints[name].append([layer,list(map(int,box))])
    selected=[];skipped=[];seen=set()
    for i,m in enumerate(report['markers']):
        if m['layer']!='metal3':continue
        own=aliases[m['net']];paths=nets[m['net']]['nonrect_paths']
        row=dict(marker=m,same_net_nearby_rectangles=[s for s in shapes[i]if s['alias']==own and s['layer']=='metal3'])
        options=[]
        for a,b in pairs(row):
            wires=[p for p in paths if contains(p,'metal3',a,b)]
            if not wires:continue
            av=[p for p in paths if p['layer']=='metal2'and p['via']and len(p['points'])==1 and tuple(p['points'][0][:2])==a]
            bv=[p for p in paths if p['layer']=='metal2'and p['via']and len(p['points'])==1 and tuple(p['points'][0][:2])==b]
            if len(av)!=1 or len(bv)!=1 or av[0]['via']!=bv[0]['via']:continue
            if not all(any(contains(p,'metal2',point,point)for p in paths)for point in(a,b)):continue
            if any(v is not None for p in paths for x,y,v in p['points']):continue
            via=av[0]['via'];assert {l for l,box in footprints[via]if l.startswith('metal')}=={'metal2','metal3'}
            width,spacing=dimensions['metal2'];assert width%2==0 and spacing>0
            half=width//2;box=[min(a[0],b[0])-half,min(a[1],b[1])-half,max(a[0],b[0])+half,max(a[1],b[1])+half]
            wx0,wy0,wx1,wy1=report['windows'][i]['bbox_dbu']
            if box[0]-spacing<wx0 or box[1]-spacing<wy0 or box[2]+spacing>wx1 or box[3]+spacing>wy1:continue
            coverage=[s['bbox_dbu']for s in shapes[i]if s['alias']==own and s['layer']=='metal2'and not s['shape'].endswith('obstruction')]
            collision=False
            for s in shapes[i]:
                if s['alias']==own or s['layer']!='metal2':continue
                x0,y0,x1,y1=s['bbox_dbu'];overlap=intersect(box,[x0-spacing,y0-spacing,x1+spacing,y1+spacing])
                if overlap and outside_area(coverage,overlap)>0:collision=True;break
            if collision:continue
            key=(m['net'],a,b)
            if key in seen:continue
            options.append(dict(index=i,net=m['net'],a=a,b=b,removed_via=av[0],retained_via=bv[0],
                                preserved_source_wires=wires,added_m2_wire=dict(layer='metal2',points=[(*a,None),(*b,None)],via=None),
                                conservative_m2_bbox_dbu=box,actual_via_footprints=footprints[via]))
        if options:
            chosen=options[0];selected.append(chosen);seen.add((m['net'],tuple(chosen['a']),tuple(chosen['b'])))
        else:skipped.append(i)
    (out/'observed-routes.json').write_text(json.dumps(nets,indent=2)+'\n')
    (out/'via-candidate-plan.json').write_text(json.dumps(dict(selected=selected,skipped=skipped,physical_qualified=False),indent=2)+'\n')
    unchanged=all(file_sha(results/n)==h for n,h in report['source_inputs_sha256'].items())
    result=dict(passed=unchanged,physical_qualified=False,diagnostic_only=True,
                source_receipt_sha256=report['source_receipt_sha256'],neighborhood_receipt_sha256=file_sha(prior/'receipt.json'),
                source_inputs_sha256=report['source_inputs_sha256'],normal_net_count=count,observed_net_count=len(nets),
                selected_marker_count=len(selected),skipped_m3_marker_count=len(skipped),original_inputs_unchanged=unchanged,
                scope='Readonly actual630 DEF topology and same-via2-pair eligibility with full current655 foreign geometry pruning. Source M3 wire retained and explicit alternate M2 path proposed. No edit or native/fullGDS/connectivity/RCX/STA/function/LEC/delivery qualification. Combined fill interactions and every final gate remain mandatory.')
    (out/'revision300-v-repaired-topology.json').write_text(json.dumps(result,indent=2)+'\n')
    assert result['passed']
