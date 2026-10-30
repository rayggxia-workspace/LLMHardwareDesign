"""Reroute complete related upper nets, allowing via11 relocation.

Unlike the closed segment search, preserves only actual via10 landings and
M10/lower material. Geometric output requires native implementation and DRC.
"""
from collections import defaultdict
import csv,gzip,heapq,json,math
from pathlib import Path
from plan_upper_local_bypass import STEP,HALF,METAL_SPACE,CUT_SPACE,rect,gap,box_wire,add_proposal

def actual_table_spacing(a,b):
    """Exact copied M9/M10 PRL table for rectangular screening only."""
    dx=max(a[0]-b[2],b[0]-a[2],0);dy=max(a[1]-b[3],b[1]-a[3],0)
    prl=max(0,min(a[3],b[3])-max(a[1],b[1])) if dx and not dy else max(0,min(a[2],b[2])-max(a[0],b[0])) if dy and not dx else 0
    width=max(min(a[2]-a[0],a[3]-a[1]),min(b[2]-b[0],b[3]-b[1]))
    if width>=3000 and prl>=8000:return 3000
    if width>=1800 and prl>=5400:return 1800
    return 1600

class Index:
    def __init__(self,records,metal_table=False,euclidean_cut=False):
        self.bins=defaultdict(list);self.size=64000;self.metal_table=metal_table;self.euclidean_cut=euclidean_cut
        for i,(z,space) in enumerate(records):
            pad=space+HALF
            for x in range((z[0]-pad)//self.size,(z[2]+pad)//self.size+1):
                for y in range((z[1]-pad)//self.size,(z[3]+pad)//self.size+1):self.bins[x,y].append((i,z,space))
    def clear(self,z):
        seen=set()
        for x in range(z[0]//self.size,z[2]//self.size+1):
            for y in range(z[1]//self.size,z[3]//self.size+1):
                for i,p,s in self.bins.get((x,y),[]):
                    if i not in seen:
                        seen.add(i)
                        required=actual_table_spacing(z,p) if self.metal_table else s
                        if self.euclidean_cut:
                            dx=max(z[0]-p[2],p[0]-z[2],0);dy=max(z[1]-p[3],p[1]-z[3],0)
                            if dx*dx+dy*dy<required*required:return False
                        elif gap(z,p)<required:return False
        return True

def is_retained_via10(r,via_layers):
    return r['kind']=='VIA' and 'via10' in via_layers[r['net'],r['link']]

def astar(rows,obs,net,a,b,die,max_nodes=80000,start_layer=11,target_layer=11,region_override=None,include_own_cuts=False):
    assert all((p[0]-190)%STEP==0 and (p[1]-140)%STEP==0 for p in [a,b]),(net,a,b)
    metals=defaultdict(list);cuts=[];own_cuts=[]
    for r in rows+obs:
        if r['net']==net:
            if include_own_cuts and r['layer']=='via11' and r['kind']=='VIA':own_cuts.append(rect(r))
            continue
        z=rect(r)
        if r['layer'] in ['metal11','metal12'] and r['kind'] in ['WIRE','VIA','OBS']:
            metals[r['layer']].append((z,3000))
        if r['layer']=='via11' and r['kind']=='VIA':cuts.append((z,CUT_SPACE))
    indices={k:Index(metals[k],metal_table=True) for k in ['metal11','metal12']};cutindex=Index(cuts,euclidean_cut=True)
    start=(*a,start_layer);target=(*b,target_layer)
    endpoint_clear={name:indices['metal'+str(layer)].clear(box_wire(p,p)) for name,p,layer in [('a',a,start_layer),('b',b,target_layer)]}
    if not all(endpoint_clear.values()):return {'path_dbu':None,'reason':'ACTUAL_RETAINED_M11_VIA10_LANDING_BLOCKED','endpoint_clear':endpoint_clear,'expanded_nodes':0}
    margin=192000
    region=(max(die[0]+HALF,min(a[0],b[0])-margin),max(die[1]+HALF,min(a[1],b[1])-margin),min(die[2]-HALF,max(a[0],b[0])+margin),min(die[3]-HALF,max(a[1],b[1])+margin))
    if region_override is not None:region=region_override
    cache={}
    def clear(layer,x,y,xx,yy):
        key=(layer,x,y,xx,yy)
        if key not in cache:cache[key]=indices['metal'+str(layer)].clear(box_wire((x,y),(xx,yy)))
        return cache[key]
    scores={start:0};parent={};queue=[(abs(a[0]-b[0])+abs(a[1]-b[1]),0,start)];expanded=0
    while queue and expanded<max_nodes:
        _,g,node=heapq.heappop(queue)
        if g!=scores[node]:continue
        expanded+=1
        if node==target:
            path=[node]
            while node in parent:node=parent[node];path.append(node)
            return {'path_dbu':list(reversed(path)),'expanded_nodes':expanded,'cost':g,'via11_count':sum(x[2]!=y[2] for x,y in zip(path,path[1:]))}
        x,y,layer=node;nexts=[]
        for dx,dy in [(STEP,0),(-STEP,0),(0,STEP),(0,-STEP)]:
            xx,yy=x+dx,y+dy
            if region[0]<=xx<=region[2] and region[1]<=yy<=region[3] and clear(layer,x,y,xx,yy):
                wrong=(layer==11 and dy!=0) or (layer==12 and dx!=0);nexts.append(((xx,yy,layer),STEP*(4 if wrong else 1)))
        cut=box_wire((x,y),(x,y))
        own_clear=all(p==cut or max(cut[0]-p[2],p[0]-cut[2],0)**2+max(cut[1]-p[3],p[1]-cut[3],0)**2>=CUT_SPACE**2 for p in own_cuts)
        if clear(11,x,y,x,y) and clear(12,x,y,x,y) and cutindex.clear(cut) and own_clear:nexts.append(((x,y,23-layer),STEP*3))
        for nxt,cost in nexts:
            ng=g+cost
            if ng>=scores.get(nxt,10**30):continue
            scores[nxt]=ng;parent[nxt]=node;h=abs(nxt[0]-b[0])+abs(nxt[1]-b[1]);heapq.heappush(queue,(ng+1.75*h,ng,nxt))
    return {'path_dbu':None,'reason':'NODE_BUDGET_EXHAUSTED' if queue else 'NO_PATH_WITHIN_EXPLICIT_REGION','expanded_nodes':expanded,'region_dbu':region,'global_infeasibility_proven':False}

def plan(branches,obstructions,diefile,out):
    with gzip.open(branches,'rt') as f:original=list(csv.DictReader(f,delimiter='\t'))
    obs=[]
    for line in Path(obstructions).read_text().splitlines():
        p=line.split();assert len(p)==5
        if p[0] in ['metal11','metal12']:obs.append(dict(zip(['layer','x0','y0','x1','y1'],p),net='__OBS__',kind='OBS',link=''))
    via_layers=defaultdict(set)
    for r in original:
        if r['kind']=='VIA':via_layers[r['net'],r['link']].add(r['layer'])
    selected=['src[%d]'%i for i in [248,206,243,199,129,201,128]]
    endpoints={}
    for net in selected:
        cuts={rect(r) for r in original if r['net']==net and r['kind']=='VIA' and r['layer']=='via10'}
        assert len(cuts)==2,(net,len(cuts))
        endpoints[net]=sorted(((z[0]+z[2])//2,(z[1]+z[3])//2) for z in cuts)
    retained=[r for r in original if r['net'] not in selected or r['kind']=='BTERM' or is_retained_via10(r,via_layers) or r['layer']=='metal10']
    assert all(r['kind'] in ['WIRE','VIA','BTERM'] for r in original)
    die=list(map(int,Path(diefile).read_text().split()));assert len(die)==4
    trials=[];solution=None
    orders=[selected,selected[:2]+list(reversed(selected[2:])),list(reversed(selected)),selected[2:]+selected[:2]]
    for order in orders:
        rows=list(retained);edits=[]
        for net in order:
            a,b=endpoints[net];answer=astar(rows,obs,net,a,b,die)
            edits.append(dict(net=net,retained_actual_via10_centers_dbu=[a,b],**answer))
            if not answer['path_dbu']:break
            add_proposal(rows,net,answer['path_dbu'])
        trials.append({'order':order,'results':edits})
        if len(edits)==len(order) and all(r['path_dbu'] for r in edits):solution=edits;break
        if edits[-1].get('reason')=='ACTUAL_RETAINED_M11_VIA10_LANDING_BLOCKED':break
    result={'scope':'COMPLETE_RELATED_UPPER_NET_SEARCH_ALLOWING_VIA11_RELOCATION_NOT_NATIVE_IMPLEMENTATION','status':'PROPOSED_WHOLE_NET_PATHS_NATIVE_IMPLEMENTATION_REQUIRED' if solution else 'FAILED_BOUNDED_WHOLE_NET_SEARCH_NOT_GLOBAL_INFEASIBILITY','full_qualification':False,'selected_nets':selected,'retained_actual_via10_centers_dbu':endpoints,'original_lower_M10_via10_and_hooks_unchanged':True,'wire_width_DBU':1600,'metal_spacing_policy':'Actual existing research PRL/width table; all native technology rules unchanged','weighted_Astar':1.75,'optimal_length_claimed':False,'cut11_space_DBU':1760,'trials':trials,'solution':solution}
    Path(out).write_text(json.dumps(result,indent=2)+'\n');return result
