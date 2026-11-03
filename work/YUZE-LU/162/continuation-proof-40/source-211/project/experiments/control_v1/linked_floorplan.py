"""Fixed native drive tiles in reserved halos, without resizing any macro.

Placement only. Shortest source-to-link wire is a diagnostic objective; full
native RC, actual route length, clock/reset and complete mask gates still apply.
"""
import copy,math
from boundary_links import xy


def place(manifest,graph,pins,seed,gap,report=None,out=None,capacity_target=0,residual_report=None,local_weight=0,local_model='quantized'):
    from floorplan import place as place_base
    rows=graph['boundary_links']['links'];link_names={r['instance']for r in rows}
    base={n:t for n,t in graph['instances'].items()if n not in link_names}
    leaves=copy.deepcopy(manifest['leaves']);connections=copy.deepcopy(graph['connections'])
    # Contract the recorded payload paths solely for the base placement cost.
    for row in rows:
        for lane in row['lanes']:
            old=str(lane['input_bit']);new=str(lane['output_bit'])
            assert connections[new]['driver']==dict(instance=row['instance'],pin='out_data['+str(lane['lane'])+']',direction='output')
            connections[old]['sinks']+=connections[new]['sinks'];del connections[new]
    for bit,c in list(connections.items()):
        c['sinks']=[s for s in c['sinks']if s['instance']not in link_names]
        if not c['sinks']:del connections[bit]
    size=leaves['control_link8']['die_um'];assert size==[100,100]
    step=108;halo=3*step;sources={r['source_instance']for r in rows}
    assert len({base[s]for s in sources})==len(sources),'Reserve halos per actual source instance'
    for source in sources:
        row=leaves[base[source]];row['die_um']=[v+2*halo for v in row['die_um']]
    positions,base_proof=place_base(base,leaves,connections,seed,pin_maps=pins,gap_um=gap)
    cluster_origins=copy.deepcopy(positions)
    for source in sources:positions[source]=[v+halo for v in positions[source]]
    occupied=[];records=[]
    for name,(x,y)in positions.items():
        w,h=manifest['leaves'][base[name]]['die_um'];occupied.append((name,x,y,w,h))
    def available(x,y):
        return all(x+100<=xx or xx+ww<=x or y+100<=yy or yy+hh<=y for _,xx,yy,ww,hh in occupied)
    for source in sorted(sources):
        sx,sy=positions[source];w,h=manifest['leaves'][base[source]]['die_um'];candidates=set()
        for ring in range(1,4):
            for j in range(-3,math.ceil(max(w,h)/step)+3):
                for x,y in [(-ring*step,j*step),(4*math.ceil(w/4)+(ring-1)*step+8,j*step),
                            (j*step,-ring*step),(j*step,4*math.ceil(h/4)+(ring-1)*step+8)]:
                    if -halo<=x and x+100<=w+halo and -halo<=y and y+100<=h+halo:
                        candidates.add((sx+x,sy+y))
        def source_points(row):
            return[(lane,*xy(pins[base[source]][lane['source_pin']]))for lane in row['lanes']]
        # Place interior/central source groups first; their wire budget is
        # hardest to satisfy. Every placement is an ordinary nonoverlap tile.
        groups=sorted([r for r in rows if r['source_instance']==source],
            key=lambda r:(-max(min(x,w-x,y,h-y)for _,x,y in source_points(r)),r['instance']))
        for row in groups:
            points=source_points(row)
            def metrics(site):
                x,y=site;distances=[];downstream=0
                for lane,px,py in points:
                    ix,iy=xy(pins['control_link8']['in_data['+str(lane['lane'])+']'])
                    distances.append(abs(sx+px-x-ix)+abs(sy+py-y-iy))
                    ox,oy=xy(pins['control_link8']['out_data['+str(lane['lane'])+']'])
                    for sink in graph['connections'][str(lane['output_bit'])]['sinks']:
                        if sink['instance']=='TOP':continue
                        peer=sink['instance'];xx,yy=positions[peer];lx,ly=xy(pins[base[peer]][sink['pin']])
                        downstream+=abs(x+ox-xx-lx)+abs(y+oy-yy-ly)
                penalty=sum(max(0,d-900)**2 for d in distances)
                return(10000*penalty+sum(distances)+.05*downstream,max(distances),sum(distances),x,y)
            options=[site for site in candidates if available(*site)];assert options,('No fixed link tile slot',source,row['instance'])
            chosen=min(options,key=metrics);score=metrics(chosen);positions[row['instance']]=list(chosen)
            occupied.append((row['instance'],*chosen,100,100));candidates.remove(chosen)
            records.append(dict(instance=row['instance'],source=source,origin_um=list(chosen),
                max_source_wire_hpwl_um=score[1],sum_source_wire_hpwl_um=score[2]))
    assert set(positions)==set(graph['instances'])
    proof=dict(algorithm='base-sequence-pair-plus-explicit-native-drive-halos',base=base_proof,
        reserved_halo_um=halo,native_die_sizes_unchanged=True,orientations='N',links=records,
        scope='Candidate physical placement only; no electrical, routing or timing acceptance. Reserved halos are empty placement space, not changes to frozen native masks.')
    if report:
        from electrical_floorplan import place as refine
        parents={name:name for name in base};parents.update({r['instance']:r['source_instance']for r in rows})
        clusters=dict(dimensions={name:leaves[top]['die_um']for name,top in base.items()},
            members={name:dict(parent=parents[name],offset_um=[positions[name][axis]-cluster_origins[parents[name]][axis]for axis in range(2)])for name in positions})
        positions,electrical=refine(manifest,graph,pins,seed,gap,report,out,clusters=clusters,capacity_target=capacity_target,residual_report=residual_report,local_weight=local_weight,local_model=local_model)
        proof['electrical_refinement']=electrical;proof['inputs']=electrical['inputs']
    return positions,proof
