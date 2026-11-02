"""Compile the source-bound router and independently verify its physical edges."""
import collections,hashlib,json,subprocess
from pathlib import Path


def route(terminals,nx,ny,seed,max_rounds,out):
    source=Path(__file__).with_name('tree_router.cpp');binary=out/'router'
    subprocess.run(['g++','-std=c++17','-O2',str(source),'-o',str(binary)],check=True)
    inp=out/'router-input.txt';result=out/'router-output.txt'
    with inp.open('w') as f:
        f.write(f'{nx} {ny} {len(terminals)} {seed} {max_rounds}\n')
        for name,ends in terminals.items():f.write(name+' '+str(len(ends))+' '+' '.join(str(v) for xy in ends for v in xy)+'\n')
    with (out/'router.log').open('w') as log:
        subprocess.run([str(binary),str(inp),str(result)],stdout=log,stderr=subprocess.STDOUT,check=True)
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
    return branches,dict(seed=seed,rounds=[r for r in trace if 'conflict_nodes' in r],final_conflicts=0,
        net_count=len(terminals),terminal_count=sum(map(len,terminals.values())),independent_tree_flood=True,
        independent_cross_net_occupancy=True,checked_edges=global_edges,source_sha256=sha(source),binary_sha256=sha(binary),
        compiler=subprocess.check_output(['g++','--version'],text=True).splitlines()[0])
