"""Inspect actual complete intermediate wiring on a compute node; diagnostic only."""
from pathlib import Path
import array,collections,hashlib,json
from router_conflict_snapshot import inspect


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def validate_graph_grid(header,nets,graph):
    # Closed inventory of the two already reconstructed 345-instance scenes.
    # This only selects diagnostic input dimensions; the complete SHA binding,
    # path/landing/budget checks and original round counters remain mandatory.
    assert len(graph['instances'])==345 and 'macro_r'in graph['instances']
    assert len(nets)==header[2]==11149
    assert tuple(header[:2])in((2345,2345),(3070,3252))


def inputs(path):
    # The older replay helper predates weighted bidirectional cost8/32. Parse
    # the current production format directly, keeping all tree/budget checks.
    with Path(path).open()as f:
        h=list(map(int,f.readline().split()));assert len(h)==17
        assert h[0]>8 and h[1]>8 and h[2]>0 and h[3]>=0 and 0<h[4]<=80
        assert h[5]in(*range(1,33),64,128,256)and 0<h[6]<=h[2]
        assert h[7:10]==[1,1,1]and 0<=h[10]<=32 and h[11]in(0,1)
        assert 0<=h[12]<=3 and h[13]==1 and h[14]in(0,1)and h[15]in(2,8,32)and h[16]==1
        nets={};limits={}
        for _ in range(h[2]):
            row=f.readline().split();assert len(row)>=3;k=int(row[1]);assert k>=2 and len(row)==3+2*k and row[0]not in nets
            points=[tuple(map(int,row[2+2*i:4+2*i]))for i in range(k)]
            assert all(4<=x<h[0]-4 and 4<=y<h[1]-4 for x,y in points)
            limit=int(row[-1]);assert limit>=-1
            nets[row[0]]=points;limits[row[0]]=limit
        assert not f.read().strip()
    assert all(limits[name]>=0 for name in list(nets)[:h[6]])
    assert all(limits[name]==-1 for name in list(nets)[h[6]:])
    return h,nets,limits


def phase_conflicts(snapshot,nets,nx,ny,locked,stride):
    assert stride in(8,16,32)
    plane=nx*ny;usage=array.array('H',[0])*(2*plane);groups=array.array('Q',[0])*(2*plane)
    native_bit=1<<stride;multi_bit=2<<stride
    with Path(snapshot).open()as f:
        assert int(f.readline())==len(nets)
        for index,(name,terminals)in enumerate(nets.items()):
            fields=f.readline().split();assert fields[0]==name
            group=native_bit if index<locked else(multi_bit if len(terminals)!=2 else 1<<(index%stride))
            points=set()
            for _ in range(int(fields[1])):
                raw=list(map(int,f.readline().split()));assert len(raw)==1+3*raw[0]
                for j in range(1,len(raw),3):points.add(raw[j+2]*plane+raw[j+1]*nx+raw[j])
            for v in points:usage[v]+=1;groups[v]|=group
        assert not f.read().strip()
    counts=collections.Counter();occupancies=collections.Counter()
    for v,u in enumerate(usage):
        if u<2:continue
        mask=groups[v];pair_mask=mask&(native_bit-1);special=mask&(native_bit|multi_bit)
        category='ordinary-pairs-one-phase'if not special and pair_mask and not(pair_mask&(pair_mask-1))else('ordinary-pairs-multiple-phases'if not special else('includes-native'if mask&native_bit else'includes-ordinary-multicast'))
        counts[category]+=1;occupancies[str(u)]+=1
    return dict(conflict_nodes=sum(counts.values()),categories=dict(counts),occupancy_histogram=dict(occupancies),stride=stride,scope='Actual conflicted vertices classified by fixed ordinary candidate-lattice phase; diagnostic only.')


def run(config,out):
    config=Path(config);cfg=json.loads(config.read_text());out=Path(out);out.mkdir()
    assert cfg['schema']=='control162-global-round-diagnostic-v1'
    paths={key:Path(cfg[key])for key in ('input','snapshot','log','graph')}
    for key,p in paths.items():assert sha(p)==cfg[key+'_sha256']
    graph=json.loads(paths['graph'].read_text())
    header,nets,limits=inputs(paths['input']);validate_graph_grid(header,nets,graph)
    round_number=cfg['round'];assert round_number in(8,16,32,64)
    trace=[json.loads(l)for l in paths['log'].read_text().splitlines()if l.startswith('{')]
    expected=next(r for r in trace if r.get('round')==round_number-1 and 'conflict_nodes'in r)
    assert any(r.get('global_snapshot_round')==round_number and r.get('global_snapshot_nets')==len(nets)and r.get('diagnostic_only')is True for r in trace)
    diagnostic=inspect(paths['snapshot'],nets,*header[:2],limits)
    for key in ('conflict_nodes','excess_occupancy','occupied_cells','summed_tree_vertices','grid_cell_capacity'):assert diagnostic[key]==expected[key]
    if cfg.get('phase_stride'):
        assert any(r.get('coarse_static_grid')is True and r.get('grid_phase')==header[3]for r in trace)
        phases=phase_conflicts(paths['snapshot'],nets,*header[:2],header[6],cfg['phase_stride'])
        assert phases['conflict_nodes']==diagnostic['conflict_nodes'];diagnostic['candidate_phase_conflicts']=phases
    result=dict(passed=True,whole_system_qualified=False,route_qualified=False,stage='actual-global-round-diagnostic-only',round=round_number,diagnostic=diagnostic,inputs={str(p):sha(p)for p in [config,Path(__file__),Path(__file__).with_name('router_conflict_snapshot.py'),*paths.values()]})
    (out/'receipt.json').write_text(json.dumps(result,indent=2));return result
