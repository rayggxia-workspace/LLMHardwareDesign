"""Compile the source-bound router and independently verify its physical edges."""
import collections,hashlib,json,os,shutil,subprocess,time
from pathlib import Path


def verify_ordinary_seed(config,native,terminals,nx,ny,locked,limits):
    """Independently check a partial physical-grid witness against all terminals."""
    sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
    cfg=json.loads(config.read_text());assert set(cfg)=={'paths','paths_sha256','input_sha256','native_prefix_sha256'}
    paths=Path(cfg['paths']);assert sha(paths)==cfg['paths_sha256']
    assert native and cfg['input_sha256']==native['input_sha256'] and cfg['native_prefix_sha256']==native['prefix_sha256']
    plane=nx*ny;size=2*plane;names=list(terminals);indices={n:i for i,n in enumerate(names)}
    landings={x+nx*y:n for n,ps in terminals.items() for x,y in ps}
    assert len(landings)==sum(map(len,terminals.values()))
    use=bytearray(size)
    def vertices(row):
        raw=list(map(int,row.split()));assert 0<raw[0]<=size and len(raw)==1+3*raw[0]
        pts=[]
        for x,y,l in zip(raw[1::3],raw[2::3],raw[3::3]):
            assert 4<=x<nx-4 and 4<=y<ny-4 and l in (0,1);pts.append(x+nx*y+plane*l)
        return pts
    with Path(native['prefix']).open()as f:
        assert int(f.readline())==len(locked)
        for n in locked:
            name,k=f.readline().split();assert name==n
            for _ in range(int(k)):
                for v in vertices(f.readline()):use[v]=1
        assert not f.read().strip()
    selected=[];nv=0;prior=len(locked)-1
    with paths.open()as f:
        count=int(f.readline());assert 0<count<=len(names)-len(locked)
        for _ in range(count):
            name,k=f.readline().split();idx=indices[name]
            assert k=='2' and idx>prior and len(terminals[name])==2 and limits.get(name,-1)==-1
            prior=idx;a,b=(x+nx*y for x,y in terminals[name])
            assert vertices(f.readline())==[a];path=vertices(f.readline())
            assert len(path)>=2 and path[0]==b and path[-1]==a and len(path)==len(set(path))
            for v,w in zip(path,path[1:]):
                x,y,l=v%nx,(v%plane)//nx,v//plane
                assert abs(x-w%nx)+abs(y-(w%plane)//nx)+abs(l-w//plane)==1
                assert l==w//plane or not (x+y)%2
            for v in path:
                assert not use[v] and (v>=plane or landings.get(v,name)==name)
                use[v]=1
            nv+=len(path);selected.append(name)
        assert not f.read().strip()
    return dict(config=str(config),config_sha256=sha(config),paths=str(paths),paths_sha256=cfg['paths_sha256'],nets=len(selected),vertices=nv,native_prefix_sha256=cfg['native_prefix_sha256'],input_sha256=cfg['input_sha256'],all_true_landings_checked=True,whole_system_qualified=False)

def verify_ordinary_access(config,native,terminals,nx,ny,locked,limits):
    """Validate selected connected access stubs against the exact native warm start."""
    sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
    c=json.loads(config.read_text())
    assert set(c)=={'paths','paths_sha256','input_sha256','native_prefix_sha256'}
    paths=Path(c['paths'])
    assert native and sha(paths)==c['paths_sha256']
    assert c['input_sha256']==native['input_sha256'] and c['native_prefix_sha256']==native['prefix_sha256']
    fixed={(x,y,0):n for n,ps in terminals.items() for x,y in ps}
    assert len(fixed)==sum(map(len,terminals.values()))
    def points(raw):
        k,*data=map(int,raw)
        assert k>0 and len(data)==3*k
        p=list(zip(data[::3],data[1::3],data[2::3]))
        assert all(4<=x<nx-4 and 4<=y<ny-4 and l in (0,1) for x,y,l in p)
        return p
    occupied=set();priority=set(locked)
    with Path(native['prefix']).open()as f:
        assert int(f.readline())==len(locked)
        for n in locked:
            name,k=f.readline().split()
            assert name==n
            for _ in range(int(k)):
                occupied.update(points(f.readline().split()))
        assert not f.read().strip()
    selected=collections.defaultdict(list);starts=set();count=vertices=0
    with paths.open()as f:
        total=int(f.readline());assert 0<total<=5000
        for _ in range(total):
            n,*values=f.readline().split();p=points(values)
            assert n in terminals and n not in priority and limits.get(n,-1)==-1
            assert p[0] not in starts and fixed.get(p[0])==n and len(p)<=1000 and len(set(p))==len(p)
            assert all(v not in occupied for v in p) and all(v not in fixed for v in p[1:])
            for v,w in zip(p,p[1:]):
                assert sum(abs(a-b)for a,b in zip(v,w))==1 and (v[2]==w[2] or not (v[0]+v[1])%2)
            occupied.update(p);starts.add(p[0]);selected[n].append(p);count+=1;vertices+=len(p)
        assert not f.read().strip()
    proof=dict(config=str(config),config_sha256=sha(config),paths=str(paths),paths_sha256=c['paths_sha256'],
        native_prefix_sha256=c['native_prefix_sha256'],input_sha256=c['input_sha256'],
        stubs=count,vertices=vertices,ordinary_nets=len(selected),all_true_landings_checked=True,
        whole_system_qualified=False)
    return proof,selected


def route(terminals,nx,ny,seed,max_rounds,out,trials=1,heuristic_weight=1,locked_names=None,wire_limits=None,negotiated_priority=False,defer_access_vias=False,congestion_scale=0,history_product=False,initial_order=0,bidirectional_two_terminal=False,adaptive_heuristic=False,nonpreferred_cost=2,pareto_wire_budget=False,trial_attempts=0,resource_label_limit=4000000,critical_first=False,ordinary_congestion_scale=0,ordinary_search_margin=0,ordinary_zero_pattern=False,weighted_bidirectional=False,trace_routing_phases=False,weighted_pair_margin=0,ordinary_threshold_pattern_rounds=0,ordinary_endpoint_escape=False,ordinary_zero_maze_budget=0,native_prefix_first=False,pin_access_policy="none",native_zero_maze_budget=0,native_batch_ripup=False,native_refresh_period=0,release_pin_reservations=False,native_prefix_flexible=False,native_prefix_input=None,ordinary_coarse_grid_stride=0,ordinary_coarse_access=False,ordinary_coarse_static=False,global_snapshot_round=0,ordinary_coarse_multicast=False,ordinary_coarse_zero=False,global_batch_ripup=False,ordinary_coarse_neighbors=False,ordinary_coarse_rounds=64,weighted_settle_once=False,coarse_refine=False,ordinary_present_growth=0,ordinary_refresh=0,ordinary_seed_input=None,ordinary_access_input=None):
    assert resource_label_limit in (4000000,8000000)and(resource_label_limit==4000000 or pareto_wire_budget)
    extra_cli=['--resource-labels='+str(resource_label_limit)]if resource_label_limit!=4000000 else[]
    assert trial_attempts==0 or (1<trials<=trial_attempts<=256)
    assert heuristic_weight in (1,4,8,16,32,64,128,256)
    assert congestion_scale in (0,1,4,8,16,32)
    assert initial_order in (0,1,2,3)
    assert nonpreferred_cost in (2,8,32)
    locked_names=list(locked_names or []);wire_limits=wire_limits or {}
    assert not critical_first or(negotiated_priority and defer_access_vias and pareto_wire_budget and locked_names)
    if critical_first:extra_cli.append('--critical-first')
    assert ordinary_congestion_scale in (0,16,64,256)
    assert not ordinary_congestion_scale or(critical_first and pareto_wire_budget and congestion_scale==1 and not bidirectional_two_terminal)
    if ordinary_congestion_scale:extra_cli.append('--ordinary-congestion-scale='+str(ordinary_congestion_scale))
    assert ordinary_search_margin in (0,4,16,64,256)
    assert not ordinary_search_margin or ordinary_congestion_scale
    if ordinary_search_margin:extra_cli.append('--ordinary-search-margin='+str(ordinary_search_margin))
    assert not ordinary_zero_pattern or(critical_first and pareto_wire_budget and negotiated_priority and defer_access_vias and bidirectional_two_terminal and not ordinary_congestion_scale and not ordinary_search_margin)
    if ordinary_zero_pattern:extra_cli.append('--ordinary-zero-pattern')
    assert not weighted_settle_once or(weighted_bidirectional and native_prefix_flexible and ordinary_coarse_access)
    if weighted_settle_once:extra_cli.append('--weighted-settle-once')
    assert not coarse_refine or(weighted_settle_once and ordinary_coarse_access and ordinary_coarse_grid_stride)
    if coarse_refine:extra_cli.append('--ordinary-coarse-refine')
    assert ordinary_refresh in (0,8,16)
    assert not ordinary_refresh or(native_prefix_flexible and coarse_refine and not global_batch_ripup and not ordinary_present_growth)
    if ordinary_refresh:extra_cli.append("--ordinary-refresh="+str(ordinary_refresh))
    assert ordinary_present_growth in (0,4,8)
    assert not ordinary_present_growth or(negotiated_priority and native_prefix_first and native_prefix_flexible and coarse_refine and not history_product and not global_batch_ripup)
    if ordinary_present_growth:extra_cli.append('--ordinary-present-growth='+str(ordinary_present_growth))
    assert not weighted_bidirectional or bidirectional_two_terminal
    if weighted_bidirectional:extra_cli.append('--weighted-bidirectional')
    assert not trace_routing_phases or weighted_bidirectional
    if trace_routing_phases:extra_cli.append('--trace-routing-phases')
    assert weighted_pair_margin in (0,4,16,64,256)and(not weighted_pair_margin or weighted_bidirectional)
    if weighted_pair_margin:extra_cli.append('--weighted-pair-margin='+str(weighted_pair_margin))
    assert ordinary_threshold_pattern_rounds in (0,8,16)and(not ordinary_threshold_pattern_rounds or(ordinary_zero_pattern and weighted_bidirectional))
    if ordinary_threshold_pattern_rounds:extra_cli.append('--ordinary-threshold-pattern-rounds='+str(ordinary_threshold_pattern_rounds))
    assert not ordinary_endpoint_escape or(ordinary_zero_pattern and weighted_bidirectional)
    if ordinary_endpoint_escape:extra_cli.append('--ordinary-endpoint-escape')
    assert ordinary_zero_maze_budget in (0,16384,65536)and(not ordinary_zero_maze_budget or(ordinary_zero_pattern and weighted_bidirectional))
    if ordinary_zero_maze_budget:extra_cli.append('--ordinary-zero-maze='+str(ordinary_zero_maze_budget))
    assert pin_access_policy in ('none','all','after-native','after-native-m12','ordinary-first')
    assert not native_prefix_first or(critical_first and pareto_wire_budget)
    assert pin_access_policy=='none' or native_prefix_first
    if native_prefix_first:extra_cli+=['--native-prefix-first','--pin-access='+pin_access_policy]
    assert native_zero_maze_budget in (0,16384,65536)and(not native_zero_maze_budget or native_prefix_first)
    if native_zero_maze_budget:extra_cli.append('--native-zero-maze='+str(native_zero_maze_budget))
    assert not native_batch_ripup or native_prefix_first
    if native_batch_ripup:extra_cli.append('--native-batch-ripup')
    assert native_refresh_period in (0,8,16)and(not native_refresh_period or(native_prefix_first and native_batch_ripup))
    if native_refresh_period:extra_cli.append('--native-refresh='+str(native_refresh_period))
    assert not release_pin_reservations or(native_prefix_first and pin_access_policy=='ordinary-first')
    if release_pin_reservations:extra_cli.append('--release-pin-reservations')
    assert not native_prefix_flexible or(native_prefix_first and pin_access_policy in ('none','after-native','after-native-m12'))
    assert pin_access_policy!='after-native-m12' or native_prefix_flexible
    assert native_prefix_input is None or native_prefix_flexible
    assert ordinary_access_input is None or (native_prefix_flexible and native_prefix_input and
        ordinary_seed_input is None and pin_access_policy=='none' and defer_access_vias)
    assert ordinary_seed_input is None or (native_prefix_flexible and native_prefix_input and pin_access_policy=='none' and not ordinary_refresh and not global_batch_ripup)
    if native_prefix_flexible:extra_cli.append('--native-prefix-flexible')
    assert ordinary_coarse_grid_stride in (0,8,16,32)and(not ordinary_coarse_grid_stride or(native_prefix_flexible and weighted_bidirectional and ordinary_zero_pattern))
    if ordinary_coarse_grid_stride:extra_cli.append('--ordinary-coarse='+str(ordinary_coarse_grid_stride))
    assert not ordinary_coarse_access or ordinary_coarse_grid_stride
    if ordinary_coarse_access:extra_cli.append('--ordinary-coarse-access')
    assert ordinary_coarse_rounds in (8,16,32,64)
    assert ordinary_coarse_rounds==64 or ordinary_coarse_grid_stride
    if ordinary_coarse_rounds!=64:extra_cli.append("--ordinary-coarse-rounds="+str(ordinary_coarse_rounds))
    assert not ordinary_coarse_neighbors or ordinary_coarse_zero
    if ordinary_coarse_neighbors:extra_cli.append('--ordinary-coarse-neighbors')
    assert not global_batch_ripup or(ordinary_coarse_zero and native_prefix_flexible)
    if global_batch_ripup:extra_cli.append('--global-batch-ripup')
    assert not ordinary_coarse_zero or ordinary_coarse_multicast
    if ordinary_coarse_zero:extra_cli.append('--ordinary-coarse-zero')
    assert not ordinary_coarse_multicast or ordinary_coarse_static
    if ordinary_coarse_multicast:extra_cli.append('--ordinary-coarse-multicast')
    assert not ordinary_coarse_static or ordinary_coarse_access
    if ordinary_coarse_static:extra_cli.append('--ordinary-coarse-static')
    assert global_snapshot_round in (0,8,16,32,64)and(not global_snapshot_round or native_prefix_flexible)
    snapshot_cli=['--global-route-snapshot='+str(global_snapshot_round)]if global_snapshot_round else[]
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
    assert oracle['independent_directional_bidirectional_dijkstra_checks']==200
    assert oracle['independent_weighted_bidirectional_path_checks']==1200
    assert oracle['independent_endpoint_escape_checks']==132
    assert oracle['independent_pin_access_matching_checks']==200
    assert oracle['independent_zero_maze_checks']==800
    assert oracle['independent_resource_product_graph_checks']==120
    assert not pareto_wire_budget or defer_access_vias
    inp=out/'router-input.txt';result=out/'router-output.txt'
    with inp.open('w') as f:
        suffix=(f' {initial_order} 1'if bidirectional_two_terminal else f' {initial_order}'if initial_order else'')
        if adaptive_heuristic:suffix=f' {initial_order} {int(bidirectional_two_terminal)} 1'
        if nonpreferred_cost!=2:suffix=f' {initial_order} {int(bidirectional_two_terminal)} {int(adaptive_heuristic)} {nonpreferred_cost}'
        if pareto_wire_budget:suffix=f' {initial_order} {int(bidirectional_two_terminal)} {int(adaptive_heuristic)} {nonpreferred_cost} 1'
        f.write(f'{nx} {ny} {len(terminals)} {seed} {max_rounds} {heuristic_weight} {len(locked_names)} 1 {int(negotiated_priority)} {int(defer_access_vias)} {congestion_scale} {int(history_product)}{suffix}\n')
        for name,ends in terminals.items():f.write(name+' '+str(len(ends))+' '+' '.join(str(v) for xy in ends for v in xy)+' '+str(wire_limits.get(name,-1))+'\n')
    seed_proof=None
    if native_prefix_input is not None:
        config=Path(native_prefix_input);cfg=json.loads(config.read_text())
        assert set(cfg)=={'prefix','prefix_sha256','input','input_sha256'}
        prefix_source=Path(cfg['prefix']);prior_input=Path(cfg['input'])
        assert hashlib.sha256(prefix_source.read_bytes()).hexdigest()==cfg['prefix_sha256']
        assert hashlib.sha256(prior_input.read_bytes()).hexdigest()==cfg['input_sha256']
        ah,ab=prior_input.read_bytes().split(b'\n',1);zh,zb=inp.read_bytes().split(b'\n',1)
        a=list(map(int,ah.split()));z=list(map(int,zh.split()))
        assert ab==zb and all(a[i]==z[i]for i in (0,1,2,6,7,9)), 'Seed geometry/terminals/wire envelope mismatch'
        from router_conflict_snapshot import inspect
        seed_check=inspect(prefix_source,{n:terminals[n]for n in locked_names},nx,ny,wire_limits)
        assert seed_check['conflict_nodes']==0 and seed_check['all_trees_flood_verified']and seed_check['all_wire_budgets_verified']
        seed_proof=dict(config=str(config),config_sha256=hashlib.sha256(config.read_bytes()).hexdigest(),prefix=str(prefix_source),prefix_sha256=cfg['prefix_sha256'],input=str(prior_input),input_sha256=cfg['input_sha256'],body_byte_exact=True,independent=seed_check)
        extra_cli.append('--native-prefix-input='+str(prefix_source))
    ordinary_seed_proof=None
    if ordinary_seed_input is not None:
        ordinary_seed_proof=verify_ordinary_seed(Path(ordinary_seed_input),seed_proof,terminals,nx,ny,locked_names,wire_limits)
        extra_cli.append('--ordinary-seed-input='+ordinary_seed_proof['paths'])
    ordinary_access_proof=None
    if ordinary_access_input is not None:
        ordinary_access_proof,ordinary_access=verify_ordinary_access(
            Path(ordinary_access_input),seed_proof,terminals,nx,ny,locked_names,wire_limits)
        extra_cli.append('--ordinary-access-input='+ordinary_access_proof['paths'])
    trial_proof=None;selected_seed=seed
    if trials==1:
        with (out/'router.log').open('w') as log:
            subprocess.run([str(binary),str(inp),str(result)]+extra_cli+snapshot_cli,stdout=log,stderr=subprocess.STDOUT,check=True)
    else:
        assert trials<=len(os.sched_getaffinity(0))<=16
        active={};logs={};records={};winner=None;peak_rss=0
        original=inp.read_text();header,body=original.split('\n',1)
        memory={k:int(v.split()[0])*1024 for k,v in (line.split(':',1) for line in Path('/proc/meminfo').read_text().splitlines())}
        forecast_per_trial=4 if weighted_bidirectional else 2
        assert memory['MemAvailable']>(trials*forecast_per_trial*1.2+16)*1024**3
        if trial_attempts:
            from router_trial_pool import run as run_pool
            def launch(index):
                actual_seed=seed*1009+index;folder=out/('trial-'+str(index));folder.mkdir()
                (folder/'input.txt').write_text(f'{nx} {ny} {len(terminals)} {actual_seed} {max_rounds} {heuristic_weight} {len(locked_names)} 1 {int(negotiated_priority)} {int(defer_access_vias)} {congestion_scale} {int(history_product)}{suffix}\n'+body)
                return [str(binary),str(folder/'input.txt'),str(folder/'output.txt')]+extra_cli+(snapshot_cli if index==0 else[]),folder/'router.log'
            trial_proof=run_pool(trials,trial_attempts,launch)
            winner=trial_proof['winner'];records=trial_proof['records']
            for index,row in records.items():row['seed']=seed*1009+index
            trial_proof.update(trials=trials,attempt_seed_stride=1009,available_bytes=memory['MemAvailable'],forecast_gib_per_trial=forecast_per_trial,
                scope='Finite independent own-child attempts refill failures within the same16CPU step; memory forecast depends on active width, not total attempts. All returned routes still require original independent checks.')
        else:
            for index in range(trials):
                actual_seed=seed*101+index;folder=out/('trial-'+str(index));folder.mkdir()
                (folder/'input.txt').write_text(f'{nx} {ny} {len(terminals)} {actual_seed} {max_rounds} {heuristic_weight} {len(locked_names)} 1 {int(negotiated_priority)} {int(defer_access_vias)} {congestion_scale} {int(history_product)}{suffix}\n'+body)
                logs[index]=(folder/'router.log').open('w')
                command=[str(binary),str(folder/'input.txt'),str(folder/'output.txt')]+extra_cli+(snapshot_cli if index==0 else[])
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
        if native_prefix_first:
            for suffix in ('.native-prefix.log','.native-prefix-paths.txt','.pin-access.json'):
                src=folder/('output.txt'+suffix)
                if suffix=='.pin-access.json' and pin_access_policy=='none':continue
                shutil.copyfile(src,Path(str(result)+suffix))
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
    native_proof=None
    if native_prefix_first:
        stages=[r for r in trace if 'native_prefix_stage_passed'in r]
        assert len(stages)==1 and stages[0]['native_prefix_stage_passed']
        assert (stages[0]['frozen_nets']==0 and stages[0]['warm_started_nets']==len(locked_names))if native_prefix_flexible else stages[0]['frozen_nets']==len(locked_names)
        prefix_changed=0
        prefix=Path(str(result)+'.native-prefix-paths.txt')
        with prefix.open()as f:
            assert int(f.readline())==len(locked_names)
            for name in locked_names:
                actual,count=f.readline().split();assert actual==name
                paths=[]
                for _ in range(int(count)):
                    values=list(map(int,f.readline().split()));assert len(values)==1+3*values[0]
                    paths.append([tuple(values[i:i+3])for i in range(1,len(values),3)])
                prefix_changed+=paths!=branches[name]
                if not native_prefix_flexible:assert paths==branches[name],('Frozen prefix differs from final full route',name)
            assert not f.read().strip()
        native_log=Path(str(result)+'.native-prefix.log')
        native_rows=[json.loads(line)for line in native_log.read_text().splitlines()if line.startswith('{')]
        native_rounds=[r for r in native_rows if 'conflict_nodes'in r]
        assert native_rounds and native_rounds[-1]['conflict_nodes']==0
        assert len(native_rounds)==stages[0]['native_rounds']
        plan=Path(str(result)+'.pin-access.json')
        native_proof=dict(stage=stages[0],rounds=native_rounds,pin_release_trace=[r for r in trace if 'unwired_search_reservations_released'in r],refresh_trace=[r for r in native_rows if 'native_refresh_period'in r],batch_trace=[r for r in native_rows if 'native_batch_removed_trees'in r],zero_maze_trace=[r for r in native_rows if 'native_zero_maze_attempts'in r],frozen_prefix_matches_full_route=(not native_prefix_flexible),
                          paths_sha256=sha(prefix),log_sha256=sha(native_log),
                          pin_plan_sha256=sha(plan)if plan.exists()else None)
        if native_prefix_flexible:
            from router_conflict_snapshot import inspect
            initial=inspect(prefix,{n:terminals[n]for n in locked_names},nx,ny,wire_limits)
            assert initial['conflict_nodes']==0 and initial['all_trees_flood_verified']and initial['all_wire_budgets_verified']
            native_proof.update(prefix_is_frozen=False,prefix_kind='M11/M12 search warm start; M1-M10 unchanged',initial_independent=initial,final_native_paths_changed=prefix_changed,seed=seed_proof)
            if seed_proof:assert sha(prefix)==seed_proof['prefix_sha256']
    if ordinary_seed_proof:
        load=[r for r in trace if r.get('ordinary_seed_loaded')]
        iterations=[r for r in trace if 'ordinary_seed_round_skipped'in r]
        assert load==[dict(ordinary_seed_loaded=True,ordinary_seed_nets=ordinary_seed_proof['nets'],ordinary_seed_vertices=ordinary_seed_proof['vertices'],ordinary_seed_frozen=False)]
        assert iterations and iterations[0]['round']==0 and iterations[0]['ordinary_seed_round_skipped']==ordinary_seed_proof['nets']
        assert all(not r['ordinary_seed_round_skipped']for r in iterations[1:])
        ordinary_seed_proof.update(actual_load=load[0],actual_iterations=iterations)
    if ordinary_access_proof:
        load=[row for row in trace if row.get('ordinary_access_loaded')]
        assert load==[dict(ordinary_access_loaded=True,stubs=ordinary_access_proof['stubs'],
                          vertices=ordinary_access_proof['vertices'])]
        for n,paths in ordinary_access.items():
            edges={tuple(sorted((v,w))) for p in branches[n] for v,w in zip(p,p[1:])}
            for p in paths:
                assert all(tuple(sorted((v,w))) in edges for v,w in zip(p,p[1:])), ('Missing real access stub',n)
        ordinary_access_proof.update(actual_load=load[0],all_selected_edges_present_in_final_route=True)
    for name,limit in wire_limits.items():
        edges={tuple(sorted((v,w)))for path in branches[name]for v,w in zip(path,path[1:])if v[2]==w[2]}
        assert len(edges)<=limit,('Independent locked source wire budget exceeded',name,len(edges),limit)
    return branches,dict(seed=selected_seed,placement_seed=seed,trial_search=trial_proof,heuristic_weight=heuristic_weight,
        heuristic_weight_schedule=('high initial weight above max(1,nets//8) conflicts; original annealing every eighth round and near convergence'if adaptive_heuristic else('1+((initial_weight-1)>>min(round//4,8))'if heuristic_weight>32 else'1+((initial_weight-1)>>min(round//4,5))')),
        equal_score_order='larger accumulated path cost then smaller node id',
        negotiated_priority=bool(negotiated_priority),
        defer_access_vias=bool(defer_access_vias),
        congestion_scale=congestion_scale or(heuristic_weight if negotiated_priority else 1),
        congestion_scale_override=congestion_scale,
        ordinary_congestion_scale_override=ordinary_congestion_scale,
        ordinary_congestion_trace=[r for r in trace if 'ordinary_congestion_scale'in r],
        ordinary_search_margin=ordinary_search_margin,
        ordinary_zero_pattern=bool(ordinary_zero_pattern),
        ordinary_zero_pattern_trace=[r for r in trace if 'zero_pattern_attempts'in r],
        ordinary_zero_pattern_header_sha256=sha(source.with_name('ordinary_zero_pattern.h')),
        ordinary_window_trace=[r for r in trace if 'ordinary_search_margin'in r],
        multiplicative_congestion_history=bool(history_product),
        initial_net_order=['seed-shuffle','shortest-span-first','longest-span-first','highest-fanout-first'][initial_order],
        bidirectional_two_terminal=bool(bidirectional_two_terminal),
        weighted_settle_once=bool(weighted_settle_once),weighted_settle_header_sha256=sha(source.with_name('weighted_settled_bidirectional.h')),
        weighted_settle_trace=[r for r in trace if 'weighted_settle_once'in r],
        weighted_bidirectional=bool(weighted_bidirectional),
        weighted_bidirectional_header_sha256=sha(source.with_name('weighted_bidirectional.h')),
        weighted_bidirectional_trace=[r for r in trace if 'weighted_bidirectional_branches_cumulative'in r],
        routing_phase_trace=[r for r in trace if 'routing_phase_event'in r],
        weighted_pair_margin=weighted_pair_margin,
        weighted_pair_window_trace=[r for r in trace if 'weighted_window_branches'in r],
        ordinary_zero_maze_budget=ordinary_zero_maze_budget,
        ordinary_zero_maze_header_sha256=sha(source.with_name('ordinary_zero_maze.h')),
        ordinary_zero_maze_trace=[r for r in trace if 'zero_maze_attempts'in r],
        ordinary_endpoint_escape=ordinary_endpoint_escape,
        ordinary_endpoint_escape_header_sha256=sha(source.with_name('ordinary_endpoint_escape.h')),
        ordinary_endpoint_escape_trace=[r for r in trace if 'endpoint_escape_attempts'in r],
        ordinary_threshold_pattern_rounds=ordinary_threshold_pattern_rounds,
        ordinary_threshold_pattern_trace=[r for r in trace if 'threshold_pattern_phase_active'in r],
        native_prefix_flexible=native_prefix_flexible,native_prefix_seed=seed_proof,release_pin_reservations=release_pin_reservations,native_refresh_period=native_refresh_period,native_batch_ripup=native_batch_ripup,native_zero_maze_budget=native_zero_maze_budget,
        **({'ordinary_seed':ordinary_seed_proof}if ordinary_seed_proof else {}),
        **({'ordinary_access':ordinary_access_proof}if ordinary_access_proof else {}),
        native_prefix_first=native_prefix_first,pin_access_policy=pin_access_policy,native_prefix_proof=native_proof,
        pin_access_header_sha256=sha(source.with_name("pin_access_reservation.h")),
        nonpreferred_search_cost=nonpreferred_cost,pareto_wire_budget=bool(pareto_wire_budget),
        finite_resource_label_memory_envelope=resource_label_limit,
        priority_partition_each_round=bool(critical_first),
        priority_partitions=[r for r in trace if 'constrained_priority_prefix'in r],
        ordinary_coarse_rounds=ordinary_coarse_rounds,coarse_round_limit_trace=[r for r in trace if "coarse_round_limit"in r],
        ordinary_coarse_neighbors=ordinary_coarse_neighbors,coarse_neighbors_trace=[r for r in trace if 'coarse_neighbor_tracks'in r],
        ordinary_refresh=ordinary_refresh,ordinary_refresh_trace=[r for r in trace if 'ordinary_refresh_period'in r],
        ordinary_present_growth=ordinary_present_growth,ordinary_present_trace=[r for r in trace if 'ordinary_present_growth_period'in r],global_batch_ripup=global_batch_ripup,global_batch_trace=[r for r in trace if 'global_batch_native_trees'in r],
        ordinary_coarse_zero=ordinary_coarse_zero,coarse_zero_trace=[r for r in trace if 'coarse_zero_attempts'in r],
        ordinary_coarse_multicast=ordinary_coarse_multicast,coarse_multicast_trace=[r for r in trace if 'coarse_multicast_attempts'in r],
        ordinary_coarse_static=ordinary_coarse_static,coarse_static_trace=[r for r in trace if 'coarse_static_grid'in r],global_snapshot_round=global_snapshot_round,global_snapshot_trial_index=(0 if global_snapshot_round else None),
        ordinary_coarse_access=ordinary_coarse_access,coarse_access_trace=[r for r in trace if 'coarse_local_access'in r],
        ordinary_coarse_grid_stride=ordinary_coarse_grid_stride,ordinary_coarse_trace=[r for r in trace if 'ordinary_coarse_stride'in r],
        ordinary_coarse_header_sha256=sha(source.with_name("ordinary_coarse_grid.h")),
        native_prefix_seed_header_sha256=sha(source.with_name("native_prefix_seed.h")),
        resource_search_header_sha256=sha(source.with_name("resource_search.h")),
        trial_pool_source_sha256=sha(source.with_name("router_trial_pool.py"))if trial_attempts else None,
        keep_currently_clean_trees=bool(negotiated_priority),
        locked_source_nets=[]if negotiated_priority else locked_names,
        prioritized_source_nets=locked_names,optimistic_locked_wire_limits_grid_edges=wire_limits,
        shortest_path_optimality_claimed=False,rounds=[r for r in trace if 'conflict_nodes' in r],final_conflicts=0,
        net_count=len(terminals),terminal_count=sum(map(len,terminals.values())),independent_tree_flood=True,
        independent_cross_net_occupancy=True,checked_edges=global_edges,source_sha256=sha(source),binary_sha256=sha(binary),
        distance_oracle=oracle,compiler=subprocess.check_output(['g++','--version'],text=True).splitlines()[0])
