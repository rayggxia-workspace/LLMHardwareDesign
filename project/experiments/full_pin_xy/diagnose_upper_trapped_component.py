"""Explain actual source-net small reachable component without more routing."""
from pathlib import Path
from collections import defaultdict,deque,Counter
import csv,gzip,io,json,math,sys
from plan_upper_whole_nets import actual_table_spacing,is_retained_via10
from plan_upper_local_bypass import rect,box_wire,gap,STEP

def diagnose(capture,out):
    capture=Path(capture)
    raw=gzip.decompress((capture/'branch_access.tsv.gz.gz').read_bytes())
    rows=list(csv.DictReader(io.StringIO(gzip.decompress(raw).decode()),delimiter='\t'))
    obs=[]
    for line in gzip.decompress((capture/'after_branch.OBS.tsv.gz').read_bytes()).decode().splitlines():
        p=line.split()
        if p[0] in ['metal11','metal12']:obs.append(dict(zip(['layer','x0','y0','x1','y1'],p),net='__OBS__',kind='OBS',link=''))
    layers=defaultdict(set)
    for r in rows:
        if r['kind']=='VIA':layers[r['net'],r['link']].add(r['layer'])
    selected=['src[%d]'%i for i in [248,206,243,199,129,201,128]];net='src[128]'
    retained=[r for r in rows if r['net'] not in selected or r['kind']=='BTERM' or is_retained_via10(r,layers) or r['layer']=='metal10']
    cuts={rect(r) for r in rows if r['net']==net and r['layer']=='via10' and r['kind']=='VIA'};a=sorted(((r[0]+r[2])//2,(r[1]+r[3])//2) for r in cuts)[0]
    foreign=[r for r in retained+obs if r['net']!=net and r['layer'] in ['metal11','metal12','via11'] and r['kind'] in ['VIA','WIRE','OBS']]
    def blockers(layer,p,q):
        box=box_wire(p,q);result=[]
        for r in foreign:
            if r['layer']!=layer:continue
            z=rect(r);needed=1760 if layer=='via11' else actual_table_spacing(box,z)
            if gap(box,z)<needed:
                dx=max(box[0]-z[2],z[0]-box[2],0);dy=max(box[1]-z[3],z[1]-box[3],0)
                result.append(dict(r,needed_DBU=needed,square_distance_DBU=gap(box,z),Euclidean_distance_DBU=math.hypot(dx,dy),corner_only_conservative_rejection=math.hypot(dx,dy)>=needed))
        return result
    start=(*a,11);todo=deque([start]);seen={start};frontier=[]
    while todo and len(seen)<100:
        p=todo.popleft();x,y,ly=p
        options=[((x+dx,y+dy,ly),'metal'+str(ly)) for dx,dy in [(STEP,0),(-STEP,0),(0,STEP),(0,-STEP)]]
        for q,layer in options:
            blocked=blockers(layer,p,q)
            if blocked:frontier.append({'from':p,'to':q,'reason':'foreign_metal','actual_blockers':blocked})
            elif q not in seen:seen.add(q);todo.append(q)
        blocked=blockers('metal11',p,p)+blockers('metal12',p,p)+blockers('via11',p,p);q=(x,y,23-ly)
        if blocked:frontier.append({'from':p,'to':q,'reason':'via11_landing_or_cut','actual_blockers':blocked})
        elif q not in seen:seen.add(q);todo.append(q)
    result={'scope':'EXACT_ACTUAL_TRAPPED_COMPONENT_OBSTACLE_DIAGNOSIS_NOT_PHYSICAL_INFEASIBILITY','net':net,'start':start,'reachable_nodes':sorted(seen),'complete_component':not todo,'frontier':frontier,'actual_blocking_nets':dict(Counter(r['net'] for x in frontier for r in x['actual_blockers'])),'corner_only_conservative_rejections':sum(r['corner_only_conservative_rejection'] for x in frontier for r in x['actual_blockers']),'full_qualification':False}
    Path(out).write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k not in ['frontier','reachable_nodes']},indent=2));return result
if __name__=='__main__':diagnose(*sys.argv[1:])
