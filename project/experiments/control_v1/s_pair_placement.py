"""Allocated-node S-only translation proposals; never physical qualification."""
import argparse,concurrent.futures,hashlib,json,math,os,time
from pathlib import Path


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def scan(data):
    columns,ys,obstacles,size,gap,old,pairs=data
    result=[];feasible=0
    for x in columns:
        for y in ys:
            w,h=size
            if any(not(x+w+gap<=xx or xx+ww+gap<=x or y+h+gap<=yy or yy+hh+gap<=y)for xx,yy,ww,hh in obstacles):continue
            lengths=[abs(a+x-old[0]-c)+abs(b+y-old[1]-d)for a,b,c,d in pairs]
            score=(sum(lengths),max(lengths),abs(x-old[0])+abs(y-old[1]),x,y)
            feasible+=1;result.append(score)
    return dict(feasible=feasible,best=sorted(result)[:16])


def main():
    p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path,required=True);p.add_argument('--graph',type=Path,required=True);p.add_argument('--base',type=Path,required=True);p.add_argument('--queue-dir',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--step-um',type=int,choices=[16,64],default=64);p.add_argument('--gap-um',type=int,choices=[16,64],default=64);a=p.parse_args()
    assert os.environ.get('SLURM_JOB_ID')and len(os.sched_getaffinity(0))==16
    a.out.mkdir(parents=True,exist_ok=False);receipt=dict(passed=False,stage='s-pair-local-move-diagnostic-only',whole_system_qualified=False,inputs={},outputs={})
    def bind(path):receipt['inputs'][str(path)]=sha(path)
    try:
        for path in [Path(__file__),a.manifest,a.graph,a.base/'receipt.json',a.base/'placement.json']:bind(path)
        parent=json.loads((a.base/'receipt.json').read_text());assert parent['passed']and parent['stage']in('wire-cap-lower-bound-only','placement-preflight-only')
        assert parent['inputs'][str(a.manifest)]==sha(a.manifest)and parent['inputs'][str(a.graph)]==sha(a.graph)
        assert parent['outputs']['placement.json']==sha(a.base/'placement.json')
        base=json.loads((a.base/'placement.json').read_text());manifest=json.loads(a.manifest.read_text());graph=json.loads(a.graph.read_text())
        assert base['graph_sha256']==sha(a.graph)and base['graph']==str(a.graph)
        positions=base['placements_um'];assert set(positions)==set(graph['instances'])and len(positions)==345
        assert all(v==0 for v in base['orientations'].values())and 'macro_r'in positions
        sizes={n:manifest['leaves'][top]['die_um']for n,top in graph['instances'].items()}
        old=positions['macro_s'];w,h=sizes['macro_s'];W,H=base['width_um'],base['height_um'];pairs=[];pair_names=[]
        for bit,c in graph['connections'].items():
            ends=[c['driver'],*c['sinks']]
            if len(ends)!=2 or{e['instance']for e in ends}!={'macro_s','s_port'}:continue
            name='net_'+bit;coordinates=base['terminals'][name];i=next(i for i,e in enumerate(ends)if e['instance']=='macro_s');s=coordinates[i];t=coordinates[1-i]
            pairs.append((s[0]*4,s[1]*4,t[0]*4,t[1]*4));pair_names.append(name)
        assert len(pairs)>=256
        from system_upper import priority_outputs
        weak=priority_outputs(graph)
        for name in weak:
            c=graph['connections'][name[4:]];assert all(e['instance']!='macro_s'for e in[c['driver'],*c['sinks']]),'Move would alter a constrained output endpoint'
        for name in ['system_upper.py','r256_scene.py']:bind(Path(__file__).with_name(name))
        obstacles=[(*positions[n],*sizes[n])for n in positions if n!='macro_s']
        columns=list(range(128,4*math.floor((W-128-w)/4)+1,a.step_um));ys=list(range(128,4*math.floor((H-128-h)/4)+1,a.step_um));assert columns and ys
        state_path=a.queue_dir/'queue-state.json';bind(state_path);state=json.loads(state_path.read_text());assert str(state['job'])==os.environ['SLURM_JOB_ID'];forecast=4
        for name in state['active']:
            path=a.queue_dir/'pending'/(name+'.json');bind(path);forecast+=json.loads(path.read_text())['forecast_gib']
        memory={k:int(v.split()[0])*1024 for k,v in(line.split(':',1)for line in Path('/proc/meminfo').read_text().splitlines())};required=(forecast*1.2+16)*1024**3;assert memory['MemAvailable']>required
        receipt['memory_admission']=dict(sum_forecast_gib_including_new=forecast,new_forecast_gib=4,required_bytes=required,available_bytes=memory['MemAvailable'])
        jobs=[([x],ys,obstacles,[w,h],a.gap_um,old,pairs)for x in columns]
        with concurrent.futures.ProcessPoolExecutor(max_workers=16)as pool:results=list(pool.map(scan,jobs))
        candidates=sorted(row for r in results for row in r['best']);baseline=sum(abs(a-c)+abs(b-d)for a,b,c,d in pairs)
        report=dict(original_origin_um=old,instance='macro_s',peer='s_port',step_um=a.step_um,new_gap_um=a.gap_um,workers=16,independent_column_tasks=len(jobs),dynamic_column_refill=True,grid_positions=len(columns)*len(ys),feasible_grid_positions=sum(r['feasible']for r in results),pair_count=len(pairs),baseline_sum_pair_hpwl_um=baseline,best_candidates=candidates[:16],constrained_endpoint_nets_unchanged=len(weak),found_improving=bool(candidates and candidates[0][0]<baseline),whole_system_qualified=False)
        if report['found_improving']:
            best=candidates[0];x,y=best[-2:];assert x%4==y%4==0
            assert all(x+w+a.gap_um<=xx or xx+ww+a.gap_um<=x or y+h+a.gap_um<=yy or yy+hh+a.gap_um<=y for xx,yy,ww,hh in obstacles)
            lengths=[abs(a+x-old[0]-c)+abs(b+y-old[1]-d)for a,b,c,d in pairs];assert sum(lengths)==best[0]and max(lengths)==best[1]
            proposal=dict(schema='control162-s-only-placement-proposal/1',instance='macro_s',origin_um=[x,y],original_origin_um=old,base_placement=str(a.base/'placement.json'),base_placement_sha256=sha(a.base/'placement.json'),graph_sha256=sha(a.graph),sum_pair_hpwl_um=best[0],pair_count=len(pairs),new_gap_um=a.gap_um,unchanged_die_um=[W,H],candidate_only=True,whole_system_qualified=False)
            target=a.out/'proposal.json';target.write_text(json.dumps(proposal,indent=2)+'\n');receipt['outputs'][target.name]=sha(target)
        target=a.out/'local-move-search.json';target.write_text(json.dumps(report,indent=2)+'\n');receipt['outputs'][target.name]=sha(target)
        receipt.update(passed=True,found_improving=report['found_improving'],feasible_grid_positions=report['feasible_grid_positions'],scope='Software S-only placement search in allocated16CPU step,16independent coordinate partitions. Original graph, native macro size/orientation, all other origins, die and constrained-output endpoints preserved. Proposed translation independently rechecks all actual fixed rectangles plus gap and original actual terminal HPWL. No pin/layout reconstruction, native/electrical, geometry, PG, RC or300MHz qualification; proposal must enter fresh actual-pin reconstruction and all original final gates.',time=time.time())
    finally:(a.out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')


if __name__=='__main__':main()
