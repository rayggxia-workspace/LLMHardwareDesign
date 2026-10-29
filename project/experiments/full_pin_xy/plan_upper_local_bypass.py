"""Actual-geometry two-layer local bypass search; native validation mandatory.

Original lower hooks/via10 are immutable. Only the M11 segment responsible
for each remaining Short may be replaced with M11/M12 wire and via11.
Research-model metal spacing 0.8um (1.5um against wide shapes), cut11 0.88um.
Conservative rectangular clearance, not a complete DRC or electrical proof.
"""
from pathlib import Path
from collections import defaultdict
import csv,gzip,hashlib,heapq,io,itertools,json,math

STEP=3200;HALF=800;METAL_SPACE=1600;CUT_SPACE=1760


def read_rows(path):
    with gzip.open(path,'rt') as f:return list(csv.DictReader(f,delimiter='\t'))


def rect(r):return tuple(int(r[k]) for k in ['x0','y0','x1','y1'])


def contains(a,b):return a[0]<=b[0] and a[1]<=b[1] and a[2]>=b[2] and a[3]>=b[3]


def gap(a,b):return max(max(a[0]-b[2],b[0]-a[2],0),max(a[1]-b[3],b[1]-a[3],0))


def box_wire(a,b):return (min(a[0],b[0])-HALF,min(a[1],b[1])-HALF,max(a[0],b[0])+HALF,max(a[1],b[1])+HALF)


def search(rows,obs,net,old,margin_um,start_layer=11):
    a,b=(old[0]+HALF,old[1]+HALF),(old[2]-HALF,old[3]-HALF)
    assert min(old[2]-old[0],old[3]-old[1])==1600 and a!=b and (a[0]==b[0] or a[1]==b[1])
    assert all((p[0]-190)%STEP==0 and (p[1]-140)%STEP==0 for p in [a,b])
    margin=round(margin_um*2000);region=(min(a[0],b[0])-margin,min(a[1],b[1])-margin,max(a[0],b[0])+margin,max(a[1],b[1])+margin)
    obstacles=defaultdict(list);cut=[];own_cut=set()
    for r in rows+obs:
        z=rect(r)
        if z[0]>region[2]+3000 or z[2]<region[0]-3000 or z[1]>region[3]+3000 or z[3]<region[1]-3000:continue
        if r['layer']=='via11' and r['kind']=='VIA':
            cut.append(z)
            if r['net']==net:own_cut.add(z)
        if r['net']!=net and r['layer'] in ['metal11','metal12'] and r['kind'] in ['WIRE','VIA','OBS']:
            width=min(z[2]-z[0],z[3]-z[1]);spacing=3000 if width>=1800 else METAL_SPACE
            obstacles[r['layer']].append((z,spacing))
    cache={}
    def clear(layer,x,y,xx,yy):
        key=(layer,x,y,xx,yy)
        if key in cache:return cache[key]
        z=box_wire((x,y),(xx,yy));value=all(gap(z,p)>=s for p,s in obstacles[layer]);cache[key]=value;return value
    def via(x,y):
        if not clear('metal11',x,y,x,y) or not clear('metal12',x,y,x,y):return False
        z=box_wire((x,y),(x,y))
        return all((p==z and p in own_cut) or gap(z,p)>=CUT_SPACE for p in cut)
    start=(a[0],a[1],start_layer);target=(b[0],b[1],start_layer)
    score={start:0};parent={};queue=[(abs(a[0]-b[0])+abs(a[1]-b[1]),0,start)];expanded=0
    while queue:
        _,g,node=heapq.heappop(queue)
        if g!=score[node]:continue
        expanded+=1
        if node==target:
            path=[node]
            while node in parent:node=parent[node];path.append(node)
            return {'path_dbu':list(reversed(path)),'expanded_nodes':expanded,'margin_um':margin_um,'cost':g,'foreign_metal_shapes_considered':sum(map(len,obstacles.values())),'existing_cut11_shapes_considered':len(cut)}
        x,y,layer=node;next_nodes=[]
        for dx,dy in [(STEP,0),(-STEP,0),(0,STEP),(0,-STEP)]:
            xx,yy=x+dx,y+dy
            if not (region[0]<=xx<=region[2] and region[1]<=yy<=region[3]):continue
            if clear('metal'+str(layer),x,y,xx,yy):
                wrong=(layer==11 and dy!=0) or (layer==12 and dx!=0)
                next_nodes.append(((xx,yy,layer),STEP*(4 if wrong else 1)))
        if via(x,y):next_nodes.append(((x,y,23-layer),STEP*3))
        for nxt,cost in next_nodes:
            ng=g+cost
            if ng>=score.get(nxt,10**30):continue
            score[nxt]=ng;parent[nxt]=node
            h=abs(nxt[0]-b[0])+abs(nxt[1]-b[1])
            heapq.heappush(queue,(ng+h,ng,nxt))
    return {'path_dbu':None,'expanded_nodes':expanded,'margin_um':margin_um,'foreign_metal_shapes_considered':sum(map(len,obstacles.values()))}


def add_proposal(rows,net,path):
    for i,(a,b) in enumerate(zip(path,path[1:])):
        z=box_wire(a,b)
        if a[2]==b[2]:layers=['metal'+str(a[2])];kind='WIRE'
        else:layers=['metal11','metal12','via11'];kind='VIA'
        for layer in layers:rows.append(dict(zip(['x0','y0','x1','y1'],map(str,z)),net=net,kind=kind,layer=layer,link='proposed_'+str(i)))


def negotiate(rows,obs,primary):
    """Free actual crossing-segment endpoint blockers, not lower pins/vias."""
    z=rect(primary);points=[(z[0]+HALF,z[1]+HALF),(z[2]-HALF,z[3]-HALF)]
    other='metal12' if primary['layer']=='metal11' else 'metal11'
    blockers=[]
    for r in rows:
        if r['net']==primary['net'] or r['layer']!=other or r['kind']!='WIRE':continue
        if any(gap(box_wire(p,p),rect(r))<METAL_SPACE for p in points):
            b=rect(r);a,c=(b[0]+HALF,b[1]+HALF),(b[2]-HALF,b[3]-HALF)
            if min(b[2]-b[0],b[3]-b[1])!=1600 or a==c:continue
            if not all((p[0]-190)%STEP==0 and (p[1]-140)%STEP==0 for p in [a,c]):continue
            blockers.append(r)
    chosen=[primary]+blockers
    assert len({(r['net'],r['layer'],rect(r)) for r in chosen})==len(chosen)
    if len(chosen)>5:return None,{'status':'TOO_MANY_ENDPOINT_BLOCKING_SEGMENTS','count':len(chosen)}
    trials=[]
    for order in itertools.permutations(range(len(chosen))):
        # Primary-first orders try the needed bypass before reclaiming tracks.
        if order[0]!=0:continue
        for margin in [12,24,48]:
            current=[r for r in rows if all(r is not q for q in chosen)];edits=[];expanded=0
            for index in order:
                r=chosen[index];answer=search(current,obs,r['net'],rect(r),margin,int(r['layer'][5:]))
                expanded+=answer['expanded_nodes']
                if not answer['path_dbu']:break
                edits.append({'net':r['net'],'removed_layer':r['layer'],'removed_wire_box_dbu':list(rect(r)),'source_wire_link':r['link'],'proposed':True,**answer})
                add_proposal(current,r['net'],answer['path_dbu'])
            trials.append({'order':list(order),'margin_um':margin,'routed_segments':len(edits),'expanded_nodes':expanded})
            if len(edits)==len(chosen):return (current,edits),{'status':'COUPLED_SEGMENT_GEOMETRIC_PATHS_FOUND','trials':trials,'actual_endpoint_blockers':[{k:r[k] for k in ['net','layer','x0','y0','x1','y1','link']} for r in blockers]}
    return None,{'status':'NO_COUPLED_PATH_FOUND','trials':trials,'actual_endpoint_blockers':[{k:r[k] for k in ['net','layer','x0','y0','x1','y1','link']} for r in blockers]}


def plan(branches,obstructions,out):
    rows=read_rows(branches);obs=[]
    for line in Path(obstructions).read_text().splitlines():
        p=line.split();assert len(p)==5
        if p[0] in ['metal11','metal12']:obs.append(dict(zip(['layer','x0','y0','x1','y1'],p),net='__OBS__',kind='OBS',link=''))
    # Exact native Short boxes from closed r02; do not infer endpoints/targets.
    specifications=[('src[248]',(4876190,5285740,4877790,5287340)),('src[206]',(4930590,5276140,4932190,5277740))]
    edits=[]
    for net,marker in specifications:
        hits=[r for r in rows if r['net']==net and r['kind']=='WIRE' and r['layer']=='metal11' and contains(rect(r),marker)]
        assert len(hits)==1,(net,'Ambiguous actual crossing WIRE',hits)
        old=hits[0];old_box=rect(old);attempts=[]
        for margin in [12,24,48,96]:
            result=search(rows,obs,net,old_box,margin);attempts.append(result)
            if result['path_dbu']:break
        if not result['path_dbu']:
            solution,negotiation=negotiate(rows,obs,old)
            if solution:
                rows,additional=solution
                edits+=additional
                continue
            failure={'status':'NO_LOCAL_GEOMETRIC_BYPASS_FOUND','full_qualification':False,'failed_net':net,'attempts':attempts,'negotiation':negotiation,'previous_edits':edits}
            Path(out).write_text(json.dumps(failure,indent=2)+'\n');return failure
        edit={'net':net,'removed_wire_box_dbu':list(old_box),'source_wire_link':old['link'],'native_short_box_dbu':list(marker),'proposed':True,**result};edits.append(edit)
        rows=[r for r in rows if r is not old]
        add_proposal(rows,net,result['path_dbu'])
    result={'status':'PROPOSED_LOCAL_BYPASSES_NATIVE_IMPLEMENTATION_REQUIRED','full_qualification':False,
      'DBU_per_um':2000,'grid_pitch_dbu':STEP,'wire_width_dbu':1600,'minimum_metal_spacing_dbu':METAL_SPACE,'minimum_cut11_spacing_dbu':CUT_SPACE,
      'geometry_source_sha256':hashlib.sha256(Path(branches).read_bytes()).hexdigest(),'obstruction_source_sha256':hashlib.sha256(Path(obstructions).read_bytes()).hexdigest(),
      'same_M10_hooks_via10_all_original_pin_rectangles_and_lower_material':True,
      'screen_scope':'Actual other-net M11/M12 rectangles, existing cut11 and actual upper OBS. Conservative square-distance clearance; not full DRC, original lower freeze, function or RC/STA.',
      'edits':edits}
    Path(out).write_text(json.dumps(result,indent=2)+'\n');return result
