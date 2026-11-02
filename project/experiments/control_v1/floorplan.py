"""Sequence-pair candidates from actual fixed dimensions and boundary connectivity.

All rectangles retain their native orientation/size. This only searches placement;
route, actual mask, timing and PG checks are separate mandatory gates.
"""
import bisect,collections,math,random

def place(instances,leaves,connections,seed,iterations=18000,pin_maps=None,gap_um=64):
    names=sorted(instances);n=len(names);rng=random.Random(seed)
    assert gap_um in (64,256,512,1024)
    widths=[4*math.ceil(leaves[instances[k]]["die_um"][0]/4)+gap_um for k in names]
    heights=[4*math.ceil(leaves[instances[k]]["die_um"][1]/4)+gap_um for k in names]
    ids={name:i for i,name in enumerate(names)};weights=collections.Counter()
    for row in connections.values():
        driver=row["driver"]["instance"]
        for sink in row["sinks"]:
            peer=sink["instance"]
            if driver!="TOP" and peer!="TOP" and driver!=peer:weights[tuple(sorted((ids[driver],ids[peer])))]+=1
    edges=[(a,b,w) for (a,b),w in weights.items()]
    offsets=collections.defaultdict(lambda:[[],[]])
    if pin_maps is not None:
        def local(end):
            p=pin_maps[instances[end['instance']]][end['pin']]
            if 'xy_um' in p:return p['xy_um']
            b=p['box_dbu'];return [(b[0]+b[2])/4000,(b[1]+b[3])/4000]
        for row in connections.values():
            driver=row['driver']
            for sink in row['sinks']:
                if driver['instance']=='TOP' or sink['instance']=='TOP' or driver['instance']==sink['instance']:continue
                a,b=ids[driver['instance']],ids[sink['instance']];p,q=local(driver),local(sink)
                if a>b:a,b=b,a;p,q=q,p
                for axis in (0,1):offsets[a,b][axis].append(p[axis]-q[axis])
        assert set(offsets)==set(weights)
        for pair,axes in offsets.items():
            for axis,values in enumerate(axes):
                values.sort();prefix=[0]
                for value in values:prefix.append(prefix[-1]+value)
                axes[axis]=(values,prefix)
        def distance(delta,axis):
            values,prefix=axis;k=bisect.bisect_left(values,-delta)
            return -delta*k-prefix[k]+delta*(len(values)-k)+prefix[-1]-prefix[k]
    positive=list(range(n));negative=list(range(n));rng.shuffle(positive);rng.shuffle(negative)
    def evaluate(pos,neg):
        rank=[0]*n
        for i,k in enumerate(neg):rank[k]=i
        x=[0]*n;y=[0]*n
        for index,a in enumerate(pos):
            for b in pos[index+1:]:
                if rank[a]<rank[b]:x[b]=max(x[b],x[a]+widths[a])
                else:y[b]=max(y[b],y[a]+heights[a])
        width=max(x[i]+widths[i] for i in range(n));height=max(y[i]+heights[i] for i in range(n))
        if pin_maps is None:
            cost=sum(w*(abs(x[a]+widths[a]/2-x[b]-widths[b]/2)+abs(y[a]+heights[a]/2-y[b]-heights[b]/2)) for a,b,w in edges)
        else:
            cost=sum(distance(x[a]-x[b],axes[0])+distance(y[a]-y[b],axes[1]) for (a,b),axes in offsets.items())
        # Penalize long skinny envelopes; unused area alone is not a substitute
        # for reducing the actual high-bit-count endpoint separations.
        cost+=800*(width+height)+.05*width*height+1500*abs(width-height)
        return cost,x,y,width,height
    current=evaluate(positive,negative);best=current;bp=positive[:];bn=negative[:]
    for step in range(iterations):
        p=positive[:];q=negative[:];a,b=rng.sample(range(n),2)
        mode=rng.randrange(3)
        if mode in (0,2):p[a],p[b]=p[b],p[a]
        if mode in (1,2):q[a],q[b]=q[b],q[a]
        proposal=evaluate(p,q)
        temperature=2e6*(1-step/iterations)**3+100
        if proposal[0]<current[0] or rng.random()<math.exp(min(0,(current[0]-proposal[0])/temperature)):
            positive,negative,current=p,q,proposal
        if current[0]<best[0]:best=current;bp=positive[:];bn=negative[:]
    cost,x,y,width,height=best
    actual_wirelength=None
    if pin_maps is not None:
        actual_wirelength=0
        for row in connections.values():
            driver=row['driver']
            for sink in row['sinks']:
                if driver['instance']=='TOP' or sink['instance']=='TOP' or driver['instance']==sink['instance']:continue
                a,b=ids[driver['instance']],ids[sink['instance']];p,q=local(driver),local(sink)
                actual_wirelength+=abs(x[a]+p[0]-x[b]-q[0])+abs(y[a]+p[1]-y[b]-q[1])
        fast=sum(distance(x[a]-x[b],axes[0])+distance(y[a]-y[b],axes[1]) for (a,b),axes in offsets.items())
        assert math.isclose(actual_wirelength,fast,rel_tol=1e-12,abs_tol=1e-5)
    positions={name:[128+x[i],128+y[i]] for i,name in enumerate(names)}
    proof=dict(algorithm="sequence-pair-simulated-annealing",seed=seed,iterations=iterations,
               objective=cost,positive=[names[i] for i in bp],negative=[names[i] for i in bn],
               envelope_um=[width,height],fixed_native_dimensions=True,no_rotation=True,
               actual_native_pin_offsets=pin_maps is not None,inter_block_gap_um=gap_um,
               independently_recomputed_native_pin_manhattan_um=actual_wirelength,
               scope="Placement candidate only, not route or physical qualification")
    return positions,proof
