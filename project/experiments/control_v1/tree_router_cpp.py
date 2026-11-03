"""Compile the source-bound router and independently verify its physical edges."""
import collections,hashlib,json,os,shutil,subprocess,time
from pathlib import Path


def route(terminals,nx,ny,seed,max_rounds,out,trials=1,heuristic_weight=1,locked_names=None,wire_limits=None,negotiated_priority=False,defer_access_vias=False,congestion_scale=0,history_product=False,initial_order=0,bidirectional_two_terminal=False,adaptive_heuristic=False,nonpreferred_cost=2):
    assert heuristic_weight in (1,4,8,16,32)
    assert congestion_scale in (0,1,4,8,16,32)
    assert initial_order in (0,1,2,3)
    assert nonpreferred_cost in (2,8,32)
    assert nonpreferred_cost==2 or not bidirectional_two_terminal
    locked_names=list(locked_names or []);wire_limits=wire_limits or {}
    assert len(set(locked_names))==len(locked_names)and set(locked_names)<=set(terminals)
    assert set(wire_limits)<=set(locked_names)and all(isinstance(v,int)and v>=0 for v in wire_limits.values())
    terminals={name:terminals[name]for name in locked_names+[n for n in terminals if n not in set(locked_names)]}
    source=Path(__file__).with_name('tree_router.cpp');binary=out/'router'
    subprocess.run(['g++','-std=c++17','-O2',str(source),'-o',str(binary)],check=True)
    with (out/'router-distance-oracle.json').open('w') as log:
        subprocess.run([str(binary),'--self-test'],stdout=log,check=True)
    oracle=json.loads((out/'router-distance-oracle.json').read_text())
    assert oracle['passed'] and oracle['exhaustive_distance_checks']==50000
    assert oracle['independent_bidirectional_dijkstra_checks']==100
    inp=out/'router-input.txt';result=out/'router-output.txt'
    with inp.open('w') as f:
        suffix=(f' {initial_order} 1'if bidirectional_two_terminal else f' {initial_order}'if initial_order else'')
        if adaptive_heuristic:suffix=f' {initial_order} {int(bidirectional_two_terminal)} 1'
        if nonpreferred_cost!=2:suffix=f' {initial_order} {int(bidirectional_two_terminal)} {int(adaptive_heuristic)} {nonpreferred_cost}'
        f.write(f'{nx} {ny} {len(terminals)} {seed} {max_rounds} {heuristic_weight} {len(locked_names)} 1 {int(negotiated_priority)} {int(defer_access_vias)} {congestion_scale} {int(history_product)}{suffix}\n')
        for name,ends in terminals.items():f.write(name+' '+str(len(ends))+' '+' '.join(str(v) for xy in ends for v in xy)+' '+str(wire_limits.get(name,-1))+'\n')
    trial_proof=None;selected_seed=seed
    if trials==1:
        with (out/'router.log').open('w') as log:
            subprocess.run([str(binary),str(inp),str(result)],stdout=log,stderr=subprocess.STDOUT,check=True)
    else:
        assert trials<=len(os.sched_getaffinity(0))<=16
        active={};logs={};records={};winner=None;peak_rss=0
        original=inp.read_text();header,body=original.split('\n',1)
        memory={k:int(v.split()[0])*1024 for k,v in (line.split(':',1) for line in Path('/proc/meminfo').read_text().splitlines())}
        assert memory['MemAvailable']>(trials*2*1.2+16)*1024**3
        for index in range(trials):
            actual_seed=seed*101+index;folder=out/('trial-'+str(index));folder.mkdir()
            (folder/'input.txt').write_text(f'{nx} {ny} {len(terminals)} {actual_seed} {max_rounds} {heuristic_weight} {len(locked_names)} 1 {int(negotiated_priority)} {int(defer_access_vias)} {congestion_scale} {int(history_product)}{suffix}\n'+body)
            logs[index]=(folder/'router.log').open('w')
            command=[str(binary),str(folder/'input.txt'),str(folder/'output.txt')]
            active[index]=subprocess.Popen(command,stdout=logs[index],stderr=subprocess.STDOUT)
            records[index]=dict(seed=actual_seed,command=command,pid=active[index].pid)
        while active and winner is None:
            rss=0
            for index,process in list(active.items()):
                try:
                    for line in Path('/proc/'+str(process.pid)+'/status').read_text().splitlines():
                        if line.startswith('VmRSS:'):rss+=int(line.split()[1])*1024
                except OSError:pass
                rc=process.poll()
                if rc is not None:
                    records[index]['returncode']=rc;logs[index].close();del active[index]
                    if rc==0:winner=index;break
            peak_rss=max(peak_rss,rss)
            if active and winner is None:time.sleep(2)
        for index,process in active.items():
            process.terminate();records[index]['termination_reason']='Another own trial completed; awaiting independent verification'
        for index,process in active.items():
            records[index]['returncode']=process.wait();logs[index].close()
        trial_proof=dict(trials=trials,winner=winner,available_bytes=memory['MemAvailable'],forecast_gib_per_trial=2,
                         sampled_peak_aggregate_rss_bytes=peak_rss,records=records,
                         scope='Independent single-thread searches share this 16-CPU step; no acceptance before Python tree/occupancy verification')
        (out/'trial-index.json').write_text(json.dumps(trial_proof,indent=2)+'\n')
        assert winner is not None,'All independent own search trials failed'
        folder=out/('trial-'+str(winner));selected_seed=records[winner]['seed']
        for before,after in [('input.txt',inp),('output.txt',result),('router.log',out/'router.log')]:shutil.copyfile(folder/before,after)
    branches={};occupied={};global_edges=0
    with result.open() as f:
        assert int(f.readline())==len(terminals)
        for name,ends in terminals.items():
            actual,count=f.readline().split();assert actual==name
            paths=[];adjacency=collections.defaultdict(set);seen_points=set()
            for _ in range(int(count)):
                values=list(map(int,f.readline().split()));assert len(values)==1+3*values[0]
                path=[tuple(values[i:i+3]) for i in range(1,len(values),3)];assert path
                for x,y,l in path:
                    assert 4<=x<nx-4 and 4<=y<ny-4 and l in (0,1)
                    assert occupied.setdefault((x,y,l),name)==name,('Cross-net short',name,x,y,l)
                    seen_points.add((x,y,l))
                for v,w in zip(path,path[1:]):
                    assert sum(abs(a-b) for a,b in zip(v,w))==1
                    if v[2]!=w[2]:assert (v[0]+v[1])%2==0
                    adjacency[v].add(w);adjacency[w].add(v);global_edges+=1
                paths.append(path)
            start=(*ends[0],0);seen={start};todo=[start]
            while todo:
                for w in adjacency[todo.pop()]:
                    if w not in seen:seen.add(w);todo.append(w)
            assert seen==seen_points and all((*xy,0) in seen for xy in ends),('Missing physical sink',name)
            branches[name]=paths
        assert not f.read().strip()
    def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
    trace=[json.loads(line) for line in (out/'router.log').read_text().splitlines() if line.startswith('{')]
    assert trace and trace[-1]['conflict_nodes']==0
    for name,limit in wire_limits.items():
        edges={tuple(sorted((v,w)))for path in branches[name]for v,w in zip(path,path[1:])if v[2]==w[2]}
        assert len(edges)<=limit,('Independent locked source wire budget exceeded',name,len(edges),limit)
    return branches,dict(seed=selected_seed,placement_seed=seed,trial_search=trial_proof,heuristic_weight=heuristic_weight,
        heuristic_weight_schedule=('high initial weight above max(1,nets//8) conflicts; original annealing every eighth round and near convergence'if adaptive_heuristic else'1+((initial_weight-1)>>min(round//4,5))'),
        equal_score_order='larger accumulated path cost then smaller node id',
        negotiated_priority=bool(negotiated_priority),
        defer_access_vias=bool(defer_access_vias),
        congestion_scale=congestion_scale or(heuristic_weight if negotiated_priority else 1),
        congestion_scale_override=congestion_scale,
        multiplicative_congestion_history=bool(history_product),
        initial_net_order=['seed-shuffle','shortest-span-first','longest-span-first','highest-fanout-first'][initial_order],
        bidirectional_two_terminal=bool(bidirectional_two_terminal),
        nonpreferred_search_cost=nonpreferred_cost,
        keep_currently_clean_trees=bool(negotiated_priority),
        locked_source_nets=[]if negotiated_priority else locked_names,
        prioritized_source_nets=locked_names,optimistic_locked_wire_limits_grid_edges=wire_limits,
        shortest_path_optimality_claimed=False,rounds=[r for r in trace if 'conflict_nodes' in r],final_conflicts=0,
        net_count=len(terminals),terminal_count=sum(map(len,terminals.values())),independent_tree_flood=True,
        independent_cross_net_occupancy=True,checked_edges=global_edges,source_sha256=sha(source),binary_sha256=sha(binary),
        distance_oracle=oracle,compiler=subprocess.check_output(['g++','--version'],text=True).splitlines()[0])
