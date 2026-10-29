"""Repair only actual upper route components near the two remaining Shorts.

Retain long external route stems, via10 and all M10/lower material. Allow
local via11 relocation; no whole-net reroute across the chip is needed.
"""
from pathlib import Path
from collections import defaultdict
import csv,gzip,json
from plan_upper_whole_nets import astar,is_retained_via10
from plan_upper_local_bypass import rect,box_wire,add_proposal,STEP,HALF
from check_access import check_rows

def inside(p,z):return z[0]<=p[0]<=z[2] and z[1]<=p[1]<=z[3]

def split_wire(r,z):
    box=rect(r);assert min(box[2]-box[0],box[3]-box[1])==1600
    a=(box[0]+HALF,box[1]+HALF);b=(box[2]-HALF,box[3]-HALF);ly=int(r['layer'][5:])
    if a==b:return ([],[]) if inside(a,z) else ([r],[])
    assert a[0]==b[0] or a[1]==b[1]
    axis=1 if a[0]==b[0] else 0;other=1-axis
    if not z[other]<=a[other]<=z[other+2]:return [r],[]
    lo=max(a[axis],z[axis]);hi=min(b[axis],z[axis+2])
    if hi<=lo:return [r],[]
    p=list(a);p[axis]=lo;q=list(b);q[axis]=hi;p=tuple(p);q=tuple(q)
    retained=[];anchors=[]
    for start,end,anchor in [(a,p,p),(q,b,q)]:
        if start!=end:
            row=dict(r);row.update(dict(zip(['x0','y0','x1','y1'],map(str,box_wire(start,end)))));row['link']='retained_clip_'+r['link']+'_'+str(len(retained));retained.append(row);anchors.append((*anchor,ly))
    return retained,anchors

def outside_anchor_groups(retained,points,net):
    rows=[dict(r) for r in retained if r['net']==net]
    numbered={str(i):p for i,p in enumerate(sorted(points))}
    for i,p in numbered.items():
        # Membership labels sit entirely on retained real conductor caps.
        # Analysis-only terminals, never written to any physical database.
        rows.append(dict(zip(['x0','y0','x1','y1'],map(str,box_wire(p,p))),net=net,layer='metal'+str(p[2]),kind='BTERM',link='B:ANALYSIS_MEMBERSHIP_'+i))
    q=check_rows(rows)['nets'][net];groups=[]
    for terms in q['terminal_groups']:
        ids=[name.split('B:ANALYSIS_MEMBERSHIP_',1)[1] for name in terms if name.startswith('B:ANALYSIS_MEMBERSHIP_')]
        if ids:groups.append(sorted(numbered[i] for i in ids))
    assert sum(map(len,groups))==len(points)
    return groups

def plan(branches,obstructions,diefile,out):
    with gzip.open(branches,'rt') as f:original=list(csv.DictReader(f,delimiter='\t'))
    obs=[]
    for line in Path(obstructions).read_text().splitlines():
        p=line.split()
        if p[0] in ['metal11','metal12']:obs.append(dict(zip(['layer','x0','y0','x1','y1'],p),net='__OBS__',kind='OBS',link=''))
    selected=['src[%d]'%i for i in [248,206,243,199,129,201,128]];via_layers=defaultdict(set)
    for r in original:
        if r['kind']=='VIA':via_layers[r['net'],r['link']].add(r['layer'])
    # Same source-derived two-Short neighborhood; grid-aligned ~120x120um.
    center=(round((2450*2000-190)/STEP)*STEP+190,round((2645*2000-140)/STEP)*STEP+140)
    radius=38*STEP;region=(center[0]-radius,center[1]-radius,center[0]+radius,center[1]+radius)
    retained=[];anchors=defaultdict(set)
    for r in original:
        net=r['net']
        if net not in selected or r['kind']=='BTERM' or r['layer']=='metal10':retained.append(r);continue
        if r['kind']=='VIA':
            if is_retained_via10(r,via_layers):
                retained.append(r)
                if r['layer']=='metal11':
                    z=rect(r);p=((z[0]+z[2])//2,(z[1]+z[3])//2,11)
                    if inside(p,region):anchors[net].add(p)
            else:
                assert 'via11' in via_layers[net,r['link']]
                z=rect(r);p=((z[0]+z[2])//2,(z[1]+z[3])//2)
                if not inside(p,region):retained.append(r)
        elif r['kind']=='WIRE':
            keep,new=split_wire(r,region);retained+=keep;anchors[net].update(new)
        else:raise RuntimeError('Unsupported original native record '+r['kind'])
    assert all(len(anchors[n])>=2 for n in selected),{n:len(anchors[n]) for n in selected}
    anchor_groups={net:outside_anchor_groups(retained,anchors[net],net) for net in selected}
    die=list(map(int,Path(diefile).read_text().split()));trials=[];solution=None;answer_rows=None
    # Rank the measured narrow src128 endpoint before long local crossings.
    # Closed r01 shows src129 loses its 15-node exit component after src128
    # connects three boundary stems. Reserve that measured exit first; two
    # targeted priority alternatives, not an unbounded permutation search.
    orders=[['src[%d]'%i for i in order] for order in [[129,206,128,248,201,243,199],[129,128,206,201,248,199,243]]]
    for order in orders:
        rows=list(retained);edits=[];failed=None
        for net in order:
            groups=sorted(anchor_groups[net],key=lambda g:(not any(p[2]==11 and inside(p,region) for p in g),g));root=sorted(groups[0],key=lambda p:(p[2]!=11,p))[0]
            for group in groups[1:]:
                alternatives=[]
                for target in sorted(group,key=lambda p:abs(p[0]-root[0])+abs(p[1]-root[1])):
                    q=astar(rows,obs,net,root[:2],target[:2],die,start_layer=root[2],target_layer=target[2],region_override=region)
                    alternatives.append(dict(target=target,**q))
                    if q['path_dbu']:break
                good=next((x for x in alternatives if x['path_dbu']),None)
                if good is None:failed=dict(net=net,root=root,alternatives=alternatives);break
                edits.append(dict(net=net,root=root,**good));add_proposal(rows,net,good['path_dbu'])
            if failed:break
        trials.append({'order':order,'connected_local_subpaths':len(edits),'failure':failed})
        if not failed:solution=edits;answer_rows=rows;break
    result={'scope':'LOCAL_ACTUAL_UPPER_COMPONENT_REPAIR_WITH_ORIGINAL_LONG_STEMS_RETAINED_NOT_NATIVE_IMPLEMENTATION','status':'PROPOSED_LOCAL_COMPONENTS_NATIVE_IMPLEMENTATION_REQUIRED' if solution else 'FAILED_LOCAL_COMPONENT_SEARCH','selected_nets':selected,'region_centerline_DBU':region,'changed_upper_material_confined_to_region_plus_800DBU_caps':True,'anchors':{n:sorted(anchors[n]) for n in selected},'actual_retained_conductor_anchor_groups':anchor_groups,'analysis_membership_labels_not_real_hardware':True,'fixed_M10_via10_and_all_original_pin_geometry_unchanged':True,'full_qualification':False,'solution':solution,'trials':trials}
    if solution:
        result['proposed_per_net_geometry']=check_rows(sorted([dict(r) for r in answer_rows],key=lambda r:r['net']),True)
        assert result['proposed_per_net_geometry']['pass']
        result['retained_selected_material']=[r for r in retained if r['net'] in selected and r['kind'] in ['WIRE','VIA']]
        p=Path(out).with_name('proposed_branch_geometry_NOT_IMPLEMENTED.tsv.gz')
        with gzip.open(str(p),'wt') as f:
            w=csv.DictWriter(f,fieldnames=['net','layer','x0','y0','x1','y1','kind','link'],delimiter='\t');w.writeheader();w.writerows(answer_rows)
    Path(out).write_text(json.dumps(result,indent=2)+'\n');return result
