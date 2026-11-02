"""Negotiated two-layer grid router. Final occupancy must be conflict-free."""
import collections,heapq,random

def route(terminals,nx,ny,seed=0,max_rounds=80):
    rng=random.Random(seed);fixed={};access={}
    for name,ends in terminals.items():
        for x,y in ends:
            assert (x,y,0) not in fixed
            fixed[x,y,0]=name
    for name,ends in terminals.items():
        access[name]=[]
        for x,y in ends:
            sites=[(x,y)] if (x+y)%2==0 else [(x+1,y),(x-1,y),(x,y+1),(x,y-1)]
            for xx,yy in sites:
                if not (4<=xx<nx-4 and 4<=yy<ny-4):continue
                stub=[(x,y,0)]+([(xx,yy,0)] if (xx,yy)!=(x,y) else [])+[(xx,yy,1)]
                if any(fixed.get(v,name)!=name for v in stub):continue
                for v in stub:fixed[v]=name
                access[name].append(stub);break
            else:raise AssertionError(('No reserved access',name,x,y))
    history=collections.Counter();usage=collections.defaultdict(set);paths={};trace=[]
    order=list(terminals);rng.shuffle(order)
    for iteration in range(max_rounds):
        if iteration:
            # Most congested connections get first opportunity after rip-up.
            order.sort(key=lambda n:-sum(max(0,len(usage[v])-1) for v in set(paths[n])))
        for name in order:
            for v in set(paths.get(name,[])):usage[v].discard(name)
            start=access[name][0][-1];goal=access[name][1][-1]
            distance={start:0};parent={};serial=0;queue=[]
            def h(v):return abs(v[0]-goal[0])+abs(v[1]-goal[1])+(3 if v[2]!=goal[2] else 0)
            heapq.heappush(queue,(h(start),0,serial,start))
            while queue:
                _,cost,_,v=heapq.heappop(queue)
                if cost!=distance[v]:continue
                if v==goal:break
                x,y,l=v
                choices=[((x-1,y,l),1 if l==0 else 2),((x+1,y,l),1 if l==0 else 2),
                         ((x,y-1,l),1 if l==1 else 2),((x,y+1,l),1 if l==1 else 2)]
                if (x+y)%2==0:choices.append(((x,y,1-l),3))
                for w,step in choices:
                    xx,yy,ll=w
                    if not (4<=xx<nx-4 and 4<=yy<ny-4) or fixed.get(w,name)!=name:continue
                    penalty=(8+iteration*4)*len(usage[w])+history[w]*4
                    alt=cost+step+penalty
                    if alt<distance.get(w,10**20):
                        distance[w]=alt;parent[w]=v;serial+=1
                        heapq.heappush(queue,(alt+h(w),alt,serial,w))
            else:raise AssertionError(('Disconnected terminal',seed,iteration,name))
            path=[goal]
            while path[-1]!=start:path.append(parent[path[-1]])
            path.reverse();path=access[name][0][:-1]+path+list(reversed(access[name][1]))[1:]
            paths[name]=path
            for v in set(path):usage[v].add(name)
        conflicts={v:len(n)-1 for v,n in usage.items() if len(n)>1}
        trace.append(dict(round=iteration,conflict_nodes=len(conflicts),excess_occupancy=sum(conflicts.values())))
        if not conflicts:
            assert set(paths)==set(terminals)
            for name,path in paths.items():
                assert path[0]==(*terminals[name][0],0) and path[-1]==(*terminals[name][1],0)
                assert all(sum(abs(a-b) for a,b in zip(v,w))==1 for v,w in zip(path,path[1:]))
                assert all(usage[v]=={name} for v in path)
            return paths,dict(seed=seed,rounds=trace,final_conflicts=0)
        history.update(conflicts)
    raise AssertionError(('Negotiated routing failed',seed,trace[-1]))
