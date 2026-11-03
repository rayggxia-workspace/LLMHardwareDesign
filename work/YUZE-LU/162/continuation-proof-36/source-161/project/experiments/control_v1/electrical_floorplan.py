"""Search actual fixed geometry against source-bound output driver budgets."""
import concurrent.futures,hashlib,json,math,os,subprocess
from pathlib import Path


def place(manifest,graph,pins,seed,gap,report,out,rotate=False,clusters=None,capacity_target=0,residual_report=None):
    assert capacity_target==0 or .35<=capacity_target<=.8
    from placement_orientation import shift,transform
    def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
    receipt=report.parent/'receipt.json';r=json.loads(receipt.read_text());assert r['passed'] and r['stage']=='wire-cap-lower-bound-only'
    assert r['outputs'][report.name]==sha(report)
    for row in manifest['leaves'].values():
        odb=row['final_files']['6_final.odb'];assert r['inputs'][odb['path']]==odb['sha256']==sha(odb['path'])
    d=json.loads(report.read_text());assert d['executed'] and d['research_model']
    drivers={row['net']:row for row in d['rows']}
    limits={name:row['physical_driver']['max_capacitance_ff']for name,row in drivers.items()}
    residual_inputs={}
    if residual_report:
        from placement_residual_budget import budgets
        limits,residual_inputs=budgets(residual_report,drivers)
    spec=Path(__file__).resolve().parents[1]/'block_v1/technology-2um-v1.json';technology=json.loads(spec.read_text())
    e=technology['electrical'];g=technology['geometry_um'];ff=.0088541878128*e['relative_permittivity']*(g['width']/g['dielectric_gap']+2*g['thickness']/g['spacing'])*e['estimate_variants']['high']
    if clusters:
        assert not rotate and set(clusters['members'])==set(graph['instances'])
        names=sorted(clusters['dimensions']);assert {r['parent']for r in clusters['members'].values()}==set(names)
        dimensions=[clusters['dimensions'][name]for name in names]
    else:
        names=sorted(graph['instances']);dimensions=[manifest['leaves'][graph['instances'][name]]['die_um']for name in names]
    ids={name:i for i,name in enumerate(names)};nets=[]
    def xy(pin):
        if 'xy_um'in pin:return pin['xy_um']
        b=pin['box_dbu'];return[(b[0]+b[2])/4000,(b[1]+b[3])/4000]
    for bit,c in graph['connections'].items():
        name='net_'+bit;ends=[];external=False
        for endpoint in[c['driver'],*c['sinks']]:
            if endpoint['instance']=='TOP':external=True;continue
            instance=endpoint['instance'];top=graph['instances'][instance];x,y=xy(pins[top][endpoint['pin']])
            if clusters:
                member=clusters['members'][instance];dx,dy=member['offset_um'];x+=dx;y+=dy;instance=member['parent']
                w,h=clusters['dimensions'][instance];assert 0<=x<=w and 0<=y<=h
            ends.append((ids[instance],x,y))
        assert ends
        if name in limits:assert drivers[name]['driver']==c['driver']
        nets.append((limits.get(name,0)/ff,external,ends))
    source=Path(__file__).with_name('electrical_floorplan.cpp');binary=out/'electrical-floorplanner'
    subprocess.run(['g++','-std=c++17','-O2',source,'-o',binary],check=True)
    inp=out/'electrical-placement-input.txt'
    with inp.open('w')as f:
        f.write(f'{len(names)} {len(nets)} 60000 {gap} {int(rotate)} {capacity_target:.17g}\n')
        for size in dimensions:f.write(' '.join(map(str,size))+'\n')
        for budget,external,ends in nets:f.write(f'{budget:.17g} {int(external)} {len(ends)} '+' '.join(f'{i} {x:.17g} {y:.17g}'for i,x,y in ends)+'\n')
    trials=min(16,len(os.sched_getaffinity(0)))
    def search(index):
        target=out/('electrical-placement-'+str(index)+'.txt');log=out/('electrical-placement-'+str(index)+'.log');actual_seed=seed*101+index
        with log.open('w')as f:subprocess.run([binary,inp,target,str(actual_seed)],stdout=f,stderr=subprocess.STDOUT,check=True)
        lines=target.read_text().splitlines();assert len(lines)==len(names)+1
        metrics=list(map(float,lines[0].split()));raw=[list(map(float,line.split()))for line in lines[1:]]
        assert all(len(p)==3 and p[2]in range(4)and(rotate or p[2]==0)and all(v>=0 and abs(v/4-round(v/4))<1e-8 for v in p[:2])for p in raw)
        rotations=[int(p[2])for p in raw]
        assert all(w==h for w,h in dimensions)
        coords=[[p[i]+shift(size,r)[i]for i in range(2)]for p,size,r in zip(raw,dimensions,rotations)]
        W=4*math.ceil((max(p[0]+size[0]for p,size in zip(coords,dimensions))+256)/4);H=4*math.ceil((max(p[1]+size[1]for p,size in zip(coords,dimensions))+256)/4)
        energy=wire=0;violations=0;worst=0
        for budget,external,ends in nets:
            actual=[(i,*transform((x,y),dimensions[i],rotations[i]))for i,x,y in ends]
            xs=[coords[i][0]+128+x for i,x,y in actual];ys=[coords[i][1]+128+y for i,x,y in actual]
            length=max(xs)-min(xs)+max(ys)-min(ys)
            if external:length+=min(min(xs)-32,W-32-max(xs),min(ys)-32,H-32-max(ys))
            wire+=length;energy+=length
            if budget>0:
                extra=max(0,length-budget);energy+=5000*extra*extra/budget;violations+=extra>1e-7;worst=max(worst,length/budget)
        energy+=800*(W+H)+.05*W*H+1500*abs(W-H)
        if capacity_target:energy+=1e8*max(0,2*wire/(W*H)-capacity_target)**2
        expected=[energy,wire,W,H,worst,float(violations)];assert len(metrics)==len(expected)
        assert all(math.isclose(a,b,rel_tol=1e-9,abs_tol=1e-5)for a,b in zip(metrics,expected)),(index,metrics,expected)
        for i,(x,y)in enumerate(coords):
            w,h=dimensions[i]
            for j,(xx,yy)in enumerate(coords[:i]):
                ww,hh=dimensions[j];assert x+w<=xx or xx+ww<=x or y+h<=yy or yy+hh<=y
        return dict(seed=actual_seed,metrics=expected,coordinates=coords,rotations=rotations,output=str(target),sha256=sha(target),independent_cost_and_nonoverlap_verified=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=trials)as pool:records=list(pool.map(search,range(trials)))
    if residual_report:
        # A finite annealing penalty may prefer a smaller but infeasible
        # placement even when another independently checked trial is clear.
        best=min(records,key=lambda row:(row['metrics'][5],row['metrics'][0]))
    else:best=min(records,key=lambda row:row['metrics'][0])
    positions={name:[128+x,128+y]for name,(x,y)in zip(names,best['coordinates'])}
    proof=dict(algorithm='actual-driver-high-RC-wire-budget-and-near-boundary-terminal-sequence-pair',seed=seed,
        independent_trials=records,selected_seed=best['seed'],fixed_native_dimensions=True,no_rotation=not rotate,
        rotations={name:r for name,r in zip(names,best['rotations'])},
        inter_block_gap_um=gap,routing_halo_um=128,high_variant_wire_budget_only=True,native_RC_not_in_objective=True,
        capacity_target=capacity_target,capacity_proxy='2*wire_bbox_sum_um/die_area_um2; placement objective only, not a routability proof',
        inputs={str(report):sha(report),str(receipt):sha(receipt),str(source):sha(source),str(spec):sha(spec),
                str(Path(__file__).with_name('placement_orientation.py')):sha(Path(__file__).with_name('placement_orientation.py'))},
        scope='Placement search using optimistic wire-only budgets. No geometry, route or timing acceptance; actual native RC and real terminal assignment remain mandatory.')
    if clusters:
        positions={name:[positions[row['parent']][axis]+row['offset_um'][axis]for axis in range(2)]for name,row in clusters['members'].items()}
        proof['clusters']=clusters
        proof['rotations']={name:0 for name in graph['instances']}
        proof['scope']='Actual native pin/driver budgets with explicitly recorded rigid placement clusters. Cluster rectangles reserve empty space only; individual original masks, all active instances and their actual RC remain mandatory.'
    if residual_report:
        proof['inputs'].update(residual_inputs)
        proof['trial_selection']='Fewest measured necessary-bound violations, then search energy; zero still grants no physical qualification'
        proof['native_ground_and_minimum_input_caps_in_objective']=True
        proof['distributed_native_RC_not_in_objective']=True
        proof['search_budget']='Driver maximum minus actual native ground and minimum actual input pin capacitance; necessary bound only. Detours/vias/coupling and complete RC acceptance still required.'
    return positions,proof
