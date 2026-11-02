"""Search actual fixed geometry against source-bound output driver budgets."""
import concurrent.futures,hashlib,json,math,os,subprocess
from pathlib import Path


def place(manifest,graph,pins,seed,gap,report,out):
    def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
    receipt=report.parent/'receipt.json';r=json.loads(receipt.read_text());assert r['passed'] and r['stage']=='wire-cap-lower-bound-only'
    assert r['outputs'][report.name]==sha(report)
    for row in manifest['leaves'].values():
        odb=row['final_files']['6_final.odb'];assert r['inputs'][odb['path']]==odb['sha256']==sha(odb['path'])
    d=json.loads(report.read_text());assert d['executed'] and d['research_model']
    drivers={row['net']:row for row in d['rows']}
    limits={name:row['physical_driver']['max_capacitance_ff']for name,row in drivers.items()}
    spec=Path(__file__).resolve().parents[1]/'block_v1/technology-2um-v1.json';technology=json.loads(spec.read_text())
    e=technology['electrical'];g=technology['geometry_um'];ff=.0088541878128*e['relative_permittivity']*(g['width']/g['dielectric_gap']+2*g['thickness']/g['spacing'])*e['estimate_variants']['high']
    names=sorted(graph['instances']);ids={name:i for i,name in enumerate(names)};nets=[]
    def xy(pin):
        if 'xy_um'in pin:return pin['xy_um']
        b=pin['box_dbu'];return[(b[0]+b[2])/4000,(b[1]+b[3])/4000]
    for bit,c in graph['connections'].items():
        name='net_'+bit;ends=[];external=False
        for endpoint in[c['driver'],*c['sinks']]:
            if endpoint['instance']=='TOP':external=True;continue
            top=graph['instances'][endpoint['instance']];x,y=xy(pins[top][endpoint['pin']]);ends.append((ids[endpoint['instance']],x,y))
        assert ends
        if name in limits:assert drivers[name]['driver']==c['driver']
        nets.append((limits.get(name,0)/ff,external,ends))
    source=Path(__file__).with_name('electrical_floorplan.cpp');binary=out/'electrical-floorplanner'
    subprocess.run(['g++','-std=c++17','-O2',source,'-o',binary],check=True)
    inp=out/'electrical-placement-input.txt'
    with inp.open('w')as f:
        f.write(f'{len(names)} {len(nets)} 60000 {gap}\n')
        for name in names:f.write(' '.join(map(str,manifest['leaves'][graph['instances'][name]]['die_um']))+'\n')
        for budget,external,ends in nets:f.write(f'{budget:.17g} {int(external)} {len(ends)} '+' '.join(f'{i} {x:.17g} {y:.17g}'for i,x,y in ends)+'\n')
    trials=min(16,len(os.sched_getaffinity(0)))
    def search(index):
        target=out/('electrical-placement-'+str(index)+'.txt');log=out/('electrical-placement-'+str(index)+'.log');actual_seed=seed*101+index
        with log.open('w')as f:subprocess.run([binary,inp,target,str(actual_seed)],stdout=f,stderr=subprocess.STDOUT,check=True)
        lines=target.read_text().splitlines();assert len(lines)==len(names)+1
        metrics=list(map(float,lines[0].split()));coords=[list(map(float,line.split()))for line in lines[1:]]
        assert all(len(p)==2 and all(v>=0 and abs(v/4-round(v/4))<1e-8 for v in p)for p in coords)
        dimensions=[manifest['leaves'][graph['instances'][name]]['die_um']for name in names]
        W=4*math.ceil((max(p[0]+size[0]for p,size in zip(coords,dimensions))+256)/4);H=4*math.ceil((max(p[1]+size[1]for p,size in zip(coords,dimensions))+256)/4)
        energy=wire=0;violations=0;worst=0
        for budget,external,ends in nets:
            xs=[coords[i][0]+128+x for i,x,y in ends];ys=[coords[i][1]+128+y for i,x,y in ends]
            length=max(xs)-min(xs)+max(ys)-min(ys)
            if external:length+=min(min(xs)-32,W-32-max(xs),min(ys)-32,H-32-max(ys))
            wire+=length;energy+=length
            if budget>0:
                extra=max(0,length-budget);energy+=5000*extra*extra/budget;violations+=extra>1e-7;worst=max(worst,length/budget)
        energy+=800*(W+H)+.05*W*H+1500*abs(W-H)
        expected=[energy,wire,W,H,worst,float(violations)];assert len(metrics)==len(expected)
        assert all(math.isclose(a,b,rel_tol=1e-9,abs_tol=1e-5)for a,b in zip(metrics,expected)),(index,metrics,expected)
        for i,(x,y)in enumerate(coords):
            w,h=dimensions[i]
            for j,(xx,yy)in enumerate(coords[:i]):
                ww,hh=dimensions[j];assert x+w<=xx or xx+ww<=x or y+h<=yy or yy+hh<=y
        return dict(seed=actual_seed,metrics=expected,coordinates=coords,output=str(target),sha256=sha(target),independent_cost_and_nonoverlap_verified=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=trials)as pool:records=list(pool.map(search,range(trials)))
    best=min(records,key=lambda row:row['metrics'][0]);positions={name:[128+x,128+y]for name,(x,y)in zip(names,best['coordinates'])}
    proof=dict(algorithm='actual-driver-high-RC-wire-budget-and-near-boundary-terminal-sequence-pair',seed=seed,
        independent_trials=records,selected_seed=best['seed'],fixed_native_dimensions=True,no_rotation=True,
        inter_block_gap_um=gap,routing_halo_um=128,high_variant_wire_budget_only=True,native_RC_not_in_objective=True,
        inputs={str(report):sha(report),str(receipt):sha(receipt),str(source):sha(source),str(spec):sha(spec)},
        scope='Placement search using optimistic wire-only budgets. No geometry, route or timing acceptance; actual native RC and real terminal assignment remain mandatory.')
    return positions,proof
