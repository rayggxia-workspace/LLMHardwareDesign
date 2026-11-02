"""Sequence-pair candidates from actual fixed dimensions and boundary connectivity.

All rectangles retain their native orientation/size. This only searches placement;
route, actual mask, timing and PG checks are separate mandatory gates.
"""
import collections,math,random

def place(instances,leaves,connections,seed,iterations=18000):
    names=sorted(instances);n=len(names);rng=random.Random(seed)
    widths=[4*math.ceil(leaves[instances[k]]["die_um"][0]/4)+64 for k in names]
    heights=[4*math.ceil(leaves[instances[k]]["die_um"][1]/4)+64 for k in names]
    ids={name:i for i,name in enumerate(names)};weights=collections.Counter()
    for row in connections.values():
        driver=row["driver"]["instance"]
        for sink in row["sinks"]:
            peer=sink["instance"]
            if driver!="TOP" and peer!="TOP" and driver!=peer:weights[tuple(sorted((ids[driver],ids[peer])))]+=1
    edges=[(a,b,w) for (a,b),w in weights.items()]
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
        cost=sum(w*(abs(x[a]+widths[a]/2-x[b]-widths[b]/2)+abs(y[a]+heights[a]/2-y[b]-heights[b]/2)) for a,b,w in edges)
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
    positions={name:[128+x[i],128+y[i]] for i,name in enumerate(names)}
    proof=dict(algorithm="sequence-pair-simulated-annealing",seed=seed,iterations=iterations,
               objective=cost,positive=[names[i] for i in bp],negative=[names[i] for i in bn],
               envelope_um=[width,height],fixed_native_dimensions=True,no_rotation=True,
               scope="Placement candidate only, not route or physical qualification")
    return positions,proof
