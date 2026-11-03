"""Replay one search round and inspect complete paths; never physical acceptance."""
import argparse,array,collections,concurrent.futures,hashlib,json,subprocess,time
from pathlib import Path


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def inputs(path):
    with Path(path).open()as f:
        header=list(map(int,f.readline().split()));assert len(header)==12
        nx,ny,count=header[:3];nets={};limits={}
        for _ in range(count):
            row=f.readline().split();name=row[0];k=int(row[1]);assert name not in nets and len(row)==3+2*k
            nets[name]=[tuple(map(int,row[2+2*i:4+2*i]))for i in range(k)]
            limits[name]=int(row[-1])
        assert not f.read().strip()
    return header,nets,limits


def inspect(path,nets,nx,ny,limits,parents=None):
    plane=nx*ny;usage=array.array('I',[0])*(2*plane);rows=[]
    def parse(f,name,verify):
        fields=f.readline().split();assert len(fields)==2 and fields[0]==name
        points=set();adj=collections.defaultdict(set);wires=set()
        for _ in range(int(fields[1])):
            raw=list(map(int,f.readline().split()));assert raw[0]>=1 and len(raw)==1+raw[0]*3
            last=None
            for j in range(1,len(raw),3):
                x,y,l=raw[j:j+3];assert 4<=x<nx-4 and 4<=y<ny-4 and l in(0,1)
                v=l*plane+y*nx+x;points.add(v)
                if verify and last is not None:
                    a,b,c=last;w=c*plane+b*nx+a
                    assert abs(a-x)+abs(b-y)+abs(c-l)==1
                    if c!=l:assert(x+y)%2==0
                    else:wires.add(tuple(sorted((w,v))))
                    adj[w].add(v);adj[v].add(w)
                last=(x,y,l)
        if verify:
            start=nets[name][0][1]*nx+nets[name][0][0];seen={start};todo=[start]
            while todo:
                for v in adj[todo.pop()]:
                    if v not in seen:seen.add(v);todo.append(v)
            assert seen==points and all(y*nx+x in seen for x,y in nets[name]),('Incomplete tree',name)
            if limits[name]>=0:assert len(wires)<=limits[name],('Wire budget',name)
        return points
    with Path(path).open()as f:
        assert int(f.readline())==len(nets)
        for name in nets:
            points=parse(f,name,True)
            for v in points:usage[v]+=1
            rows.append(dict(net=name,tree_vertices=len(points),terminal_count=len(nets[name])))
        assert not f.read().strip()
    occupied=conflicts=excess=vertices=0;tiles=collections.Counter()
    for v,u in enumerate(usage):
        if not u:continue
        occupied+=1;vertices+=u
        if u>1:
            conflicts+=1;excess+=u-1;x=v%nx;y=(v%plane)//nx;l=v//plane
            tiles[(l,min(31,x*32//nx),min(31,y*32//ny))]+=1
    categories=collections.Counter()
    with Path(path).open()as f:
        assert int(f.readline())==len(nets)
        for row in rows:
            points=parse(f,row['net'],False);row['conflict_vertices']=sum(usage[v]>1 for v in points)
            if parents and row['net']in parents:
                ids=parents[row['net']];row['physical_cluster_count']=len(ids)
                row['category']='within-source-cluster'if len(ids)==1 else'between-clusters-or-TOP'
                categories[row['category']]+=row['conflict_vertices']
        assert not f.read().strip()
    assert sum(r['conflict_vertices']for r in rows)==conflicts+excess
    return dict(conflict_nodes=conflicts,excess_occupancy=excess,occupied_cells=occupied,
        summed_tree_vertices=vertices,grid_cell_capacity=(nx-8)*(ny-8)*2,
        all_trees_flood_verified=True,all_wire_budgets_verified=True,
        conflict_incidence_by_category=dict(categories),
        top_nets=sorted(rows,key=lambda r:r['conflict_vertices'],reverse=True)[:40],
        top_tiles=[dict(layer=l,tile_x=x,tile_y=y,conflict_vertices=n)for(l,x,y),n in tiles.most_common(40)],
        scope='Complete actual search paths, with cross-net conflicts explicitly counted. Diagnostic only; no physical qualification.')


def worker(case,binary,out,parents,full):
    folder=Path(out)/('case-'+str(case['case']));folder.mkdir()
    origin=Path(case['input']);assert sha(origin)==case['input_sha256']
    header,nets,limits=inputs(origin);assert header[4]>=1
    if full:assert len(nets)==8990 and set(nets)==set(parents)
    original_log=Path(case['original_log_snapshot']);assert sha(original_log)==case['original_log_snapshot_sha256']
    original_rounds=[json.loads(l)for l in original_log.read_text().splitlines()if l.startswith('{')and'"conflict_nodes"'in l]
    assert next(r for r in original_rounds if r['round']==0)==case['expected_round0']
    header[4]=1;first,body=origin.read_text().split('\n',1);inp=folder/'input.txt'
    inp.write_text(' '.join(map(str,header))+'\n'+body)
    result=folder/'output.txt';log=folder/'router.log'
    with log.open('w')as f:r=subprocess.run([binary,str(inp),str(result)],stdout=f,stderr=subprocess.STDOUT)
    trace=[]
    for line in log.read_text().splitlines():
        if line.startswith('{'):trace.append(json.loads(line))
    rounds=[d for d in trace if'conflict_nodes'in d];assert len(rounds)==1 and rounds[0]['round']==0
    expected=case['expected_round0'];assert rounds[0]==expected,('Instrumented replay changed actual original search',case['case'],rounds[0],expected)
    assert r.returncode==(1 if expected['conflict_nodes']else 0)
    if r.returncode:assert 'negotiation did not converge'in log.read_text()
    dump=Path(str(result)+'.partial.txt');diagnostic=inspect(dump,nets,*header[:2],limits,parents)
    for key in ['conflict_nodes','excess_occupancy','occupied_cells','summed_tree_vertices','grid_cell_capacity']:assert diagnostic[key]==expected[key]
    diagnostic.update(case=case['case'],original_input=str(origin),original_input_sha256=sha(origin),
        actual_original_round0=expected,replayed_input_sha256=sha(inp),snapshot_path=str(dump),snapshot_bytes=dump.stat().st_size,snapshot_sha256=sha(dump),log_sha256=sha(log),whole_system_qualified=False)
    (folder/'diagnostic.json').write_text(json.dumps(diagnostic,indent=2)+'\n')
    return diagnostic


def main():
    p=argparse.ArgumentParser();p.add_argument('--config',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    receipt=dict(passed=False,stage='complete-search-path-diagnostic-only',whole_system_qualified=False,inputs={str(a.config):sha(a.config)},outputs={},started_at=time.time())
    try:
        config=json.loads(a.config.read_text());assert config['schema']=='control162-complete-path-snapshot-v1'and config['kind']in('full','preflight')
        full=config['kind']=='full';count=len(config['cases']);assert count==(16 if full else 3)
        assert len({r['case']for r in config['cases']})==count
        for row in config['sources']:
            assert sha(row['path'])==row['sha256'];receipt['inputs'][row['path']]=row['sha256']
        source=Path(config['kernel']);assert str(source)in receipt['inputs']
        graph=Path(config['graph']);assert str(graph)in receipt['inputs'];g=json.loads(graph.read_text())
        link_parent={r['instance']:r['source_instance']for r in g['boundary_links']['links']}
        parents={'net_'+bit:sorted({link_parent.get(e['instance'],e['instance'])for e in[c['driver'],*c['sinks']]})for bit,c in g['connections'].items()}
        # Add an observation after each completed round. Search state/order,
        # decisions, input options and original failure remain untouched.
        marker='  if(!conflicts){complete=true;break;}'
        code=source.read_text();assert code.count(marker)==1
        observation=r'''  {
   ofstream snapshot(string(argv[2])+".partial.txt");snapshot<<count<<'\n';
   for(int n=0;n<count;++n){snapshot<<names[n]<<' '<<branches[n].size()<<'\n';
    for(auto& branch:branches[n]){snapshot<<branch.size();for(int v:branch){auto c=coord(v);snapshot<<' '<<c[0]<<' '<<c[1]<<' '<<c[2];}snapshot<<'\n';}}
   if(!snapshot)throw runtime_error("cannot write diagnostic snapshot");
  }
'''
        instrumented=a.out/'instrumented-tree-router.cpp';instrumented.write_text(code.replace(marker,observation+marker))
        binary=a.out/'diagnostic-router';subprocess.run(['g++','-std=c++17','-O2',str(instrumented),'-o',str(binary)],check=True)
        oracle=json.loads(subprocess.check_output([str(binary),'--self-test']));assert oracle['passed']and oracle['exhaustive_distance_checks']==50000
        receipt.update(instrumented_source_sha256=sha(instrumented),binary_sha256=sha(binary),distance_oracle=oracle,
            compiler=subprocess.check_output(['g++','--version'],universal_newlines=True).splitlines()[0])
        with concurrent.futures.ProcessPoolExecutor(max_workers=min(16,count))as pool:
            futures=[pool.submit(worker,c,str(binary),str(a.out),parents,full)for c in config['cases']]
            results=[f.result()for f in futures]
        report=a.out/'complete-path-diagnostics.json';report.write_text(json.dumps(dict(cases=results,whole_system_qualified=False),indent=2)+'\n');receipt['outputs'][report.name]=sha(report)
        receipt['passed']=True
    finally:
        receipt['finished_at']=time.time();(a.out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')


if __name__=='__main__':main()
