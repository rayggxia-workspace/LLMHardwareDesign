"""Simultaneous local multicommodity flow on closed real upper geometry.

SciPy/HiGHS feasibility preparation only. No physical pass is inferred from
solver success. All long stems, immutable via10 and original pins remain.
Native implementation/DRC is the next independent mandatory gate.
"""
from pathlib import Path
from collections import defaultdict
import argparse,csv,datetime,gzip,hashlib,json,os,subprocess,time
import numpy as np
from scipy.optimize import Bounds,LinearConstraint,milp
from scipy.sparse import coo_matrix
import scipy
from plan_upper_whole_nets import Index,is_retained_via10
from plan_upper_local_components import split_wire,inside,outside_anchor_groups
from plan_upper_local_bypass import rect,box_wire,STEP,HALF
from check_access import check_rows

def solve(branches,obstructions,diefile,out,seconds,blocker_proof=None):
    out=Path(out);out.mkdir(parents=True,exist_ok=False);inputs={str(p):hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in [branches,obstructions,diefile]}
    rec={'scope':'SIMULTANEOUS_GEOMETRIC_FLOW_PREPARATION_NOT_NATIVE_PHYSICAL_IMPLEMENTATION','full_qualification':False,'source_SHA':inputs,'scipy_version':scipy.__version__,'driver_commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'solver_time_limit_seconds':seconds,'native_DRC_RC_STA':'NOT_EXECUTED','rules_not_relaxed':True,'via11_cut_corner_semantics':'Native orthogonal FAIL1/diagonal PASS0, upper_cut_corner_probe/r03; proof must also be checked before physical application'}
    def save():
        rec['all_sources_unchanged']=all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==s for p,s in inputs.items());rec['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();rec['files']={p.name:{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in out.iterdir() if p.is_file() and p.name!='execution.json'};(out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n')
    with gzip.open(branches,'rt') as f:original=list(csv.DictReader(f,delimiter='\t'))
    obs=[]
    for line in Path(obstructions).read_text().splitlines():
        p=line.split()
        if p[0] in ['metal11','metal12']:obs.append(dict(zip(['layer','x0','y0','x1','y1'],p),net='__OBS__',kind='OBS',link=''))
    selected=['src[%d]'%i for i in [248,206,243,199,129,201,128]]
    if blocker_proof:
        proof=json.loads(Path(blocker_proof).read_text());additional=sorted(set(proof['actual_blocking_nets'])-set(selected))
        actual={(r['net'],r['kind'],r['layer'],rect(r)) for r in original}
        for net in additional:
            assert any((r['net'],r['kind'],r['layer'],rect(r)) in actual for point in proof['frontier'] for r in point['actual_blockers'] if r['net']==net)
        selected+=additional;inputs[str(blocker_proof)]=hashlib.sha256(Path(blocker_proof).read_bytes()).hexdigest();rec['additional_actual_endpoint_blocking_nets']=additional
    via_layers=defaultdict(set)
    for r in original:
        if r['kind']=='VIA':via_layers[r['net'],r['link']].add(r['layer'])
    center=(round((2450*2000-190)/STEP)*STEP+190,round((2645*2000-140)/STEP)*STEP+140);radius=38*STEP;region=(center[0]-radius,center[1]-radius,center[0]+radius,center[1]+radius)
    retained=[];anchors=defaultdict(set)
    for r in original:
        net=r['net']
        if net not in selected or r['kind']=='BTERM' or r['layer']=='metal10':retained.append(r);continue
        z=rect(r)
        if r['kind']=='VIA':
            p=((z[0]+z[2])//2,(z[1]+z[3])//2)
            if is_retained_via10(r,via_layers):
                retained.append(r)
                if r['layer']=='metal11' and inside(p,region):anchors[net].add((*p,11))
            else:
                assert 'via11' in via_layers[net,r['link']]
                if not inside(p,region):retained.append(r)
        elif r['kind']=='WIRE':
            keep,points=split_wire(r,region);retained+=keep;anchors[net].update(points)
        else:raise RuntimeError('Unsupported actual record '+r['kind'])
    groups={n:outside_anchor_groups(retained,anchors[n],n) for n in selected};rec['actual_retained_anchor_groups']=groups;rec['region_DBU']=region
    cost=[];integrality=[];lower=[];upper=[];ri=[];ci=[];av=[];lb=[];ub=[]
    def variable(c,integer,lo,hi):
        i=len(cost);cost.append(c);integrality.append(integer);lower.append(lo);upper.append(hi);return i
    def constraint(items,lo=-np.inf,hi=np.inf):
        row=len(lb);lb.append(lo);ub.append(hi)
        for col,value in items:
            if value:ri.append(row);ci.append(col);av.append(value)
    occupancy=defaultdict(list);viausage=defaultdict(list);flows=[];nodevars={};net_conservation={};virtualrows={};build_start=time.time()
    grid=[(x,y,ly) for x in range(region[0],region[2]+1,STEP) for y in range(region[1],region[3]+1,STEP) for ly in [11,12]]
    rec['per_net_independent_grid_reachability']={}
    for net in selected:
        demand=len(groups[net])-1;assert demand>=1
        metals=defaultdict(list);cuts=[];owncuts=[]
        for r in retained+obs:
            z=rect(r)
            if r['layer']=='via11' and r['kind']=='VIA':
                (owncuts if r['net']==net else cuts).append((z,1760))
            if r['net']!=net and r['layer'] in ['metal11','metal12'] and r['kind'] in ['WIRE','VIA','OBS']:metals[r['layer']].append((z,3000))
        indices={ly:Index(metals['metal'+str(ly)],metal_table=True) for ly in [11,12]};cutindex=Index(cuts,euclidean_cut=True)
        allowed={p for p in grid if indices[p[2]].clear(box_wire(p,p))};nv={p:variable(1,1,0,1) for p in allowed};nodevars[net]=nv;conservation={p:[] for p in allowed};net_conservation[net]=conservation
        for p,var in nv.items():occupancy[p].append(var)
        def edge(a,b,physical=True,via=False):
            ia,ib=nv[a],nv[b];v=variable(0,0,-demand,demand);conservation[a].append((v,1));conservation[b].append((v,-1))
            for n in [ia,ib]:constraint([(v,1),(n,-demand)],hi=0);constraint([(v,-1),(n,-demand)],hi=0)
            if via:
                h=variable(2,1,0,1);viausage[a[:2]].append(h);constraint([(v,1),(h,-demand)],hi=0);constraint([(v,-1),(h,-demand)],hi=0)
            flows.append((net,a,b,v))
        for p in sorted(allowed):
            x,y,ly=p
            for q in [(x+STEP,y,ly),(x,y+STEP,ly)]:
                if q in allowed and indices[ly].clear(box_wire(p,q)):edge(p,q)
            if ly==11 and (x,y,12) in allowed:
                box=box_wire(p,p);good=cutindex.clear(box)
                for z,_ in owncuts:
                    dx=max(box[0]-z[2],z[0]-box[2],0);dy=max(box[1]-z[3],z[1]-box[3],0)
                    if z!=box and dx*dx+dy*dy<1760**2:good=False;break
                if good:edge(p,(x,y,12),via=True)
        for gi,group in enumerate(groups[net]):
            terms=[]
            for p in group:
                p=tuple(p)
                if p not in allowed:continue
                v=variable(0,0,-demand,demand);terms.append((v,1));conservation[p].append((v,-1));z=nv[p]
                constraint([(v,1),(z,-demand)],hi=0);constraint([(v,-1),(z,-demand)],hi=0)
            assert terms,(net,'No actual group anchor is geometrically available',group)
            supply=demand if gi==0 else -1;constraint(terms,lo=supply,hi=supply)
        # Diagnose model connectivity independently of other selected flows.
        adjacency=defaultdict(set)
        for nn,a,b,var in flows:
            if nn==net:adjacency[a].add(b);adjacency[b].add(a)
        for group in groups[net]:
            usable=[tuple(p) for p in group if tuple(p) in allowed]
            for p in usable[1:]:adjacency[usable[0]].add(p);adjacency[p].add(usable[0])
        reached={tuple(p) for p in groups[net][0] if tuple(p) in allowed};todo=list(reached)
        while todo:
            for p in adjacency[todo.pop()]:
                if p not in reached:reached.add(p);todo.append(p)
        rec['per_net_independent_grid_reachability'][net]={'reachable_nodes':len(reached),'target_groups_reachable':[any(tuple(p) in reached for p in g) for g in groups[net][1:]]}
        for terms in conservation.values():constraint(terms,lo=0,hi=0)
    for cols in occupancy.values():constraint([(i,1) for i in cols],hi=1)
    for (x,y),cols in viausage.items():
        constraint([(i,1) for i in cols],hi=1)
        for p in [(x+STEP,y),(x,y+STEP)]:
            if p in viausage:constraint([(i,1) for i in cols+viausage[p]],hi=1)
    rec.update(variables=len(cost),constraints=len(lb),binary_variables=sum(integrality),physical_flow_edges=len(flows),build_seconds=time.time()-build_start)
    matrix=coo_matrix((np.asarray(av),(np.asarray(ri,dtype=np.int32),np.asarray(ci,dtype=np.int32))),shape=(len(lb),len(cost))).tocsc();del ri,ci,av
    options={'time_limit':seconds,'mip_rel_gap':0.05,'presolve':True,'threads':4};rec['actual_solver_options']=options
    result=milp(np.asarray(cost),integrality=np.asarray(integrality),bounds=Bounds(np.asarray(lower),np.asarray(upper)),constraints=LinearConstraint(matrix,np.asarray(lb),np.asarray(ub)),options=options)
    rec.update(solver_status=int(result.status),solver_message=result.message,solver_MIP_gap=getattr(result,'mip_gap',None),solver_node_count=getattr(result,'mip_node_count',None),geometry_optimal_length_claimed=False)
    if result.x is None:rec['status']='NO_FEASIBLE_SOLUTION_RETURNED_WITHIN_EXPLICIT_MODEL_AND_BUDGET_NOT_GLOBAL_PHYSICAL_INFEASIBILITY';save();print(json.dumps({k:v for k,v in rec.items() if k not in ['actual_retained_anchor_groups','source_SHA','files']},indent=2));return
    values=matrix@result.x;assert np.all(values>=np.asarray(lb)-1e-5) and np.all(values<=np.asarray(ub)+1e-5)
    mask=np.asarray(integrality,dtype=bool);assert np.max(np.abs(result.x[mask]-np.round(result.x[mask])))<1e-5
    rows=list(retained);solution=[];existing={(r['net'],rect(r)) for r in retained if r['kind']=='VIA' and r['layer']=='via11'}
    for serial,(net,a,b,var) in enumerate(flows):
        if abs(result.x[var])<1e-6:continue
        box=box_wire(a,b);solution.append({'net':net,'path_dbu':[a,b],'flow':float(result.x[var])})
        if a[2]!=b[2] and (net,box) in existing:continue
        layers=['metal'+str(a[2])] if a[2]==b[2] else ['metal11','metal12','via11'];kind='WIRE' if a[2]==b[2] else 'VIA'
        for layer in layers:rows.append(dict(zip(['x0','y0','x1','y1'],map(str,box)),net=net,layer=layer,kind=kind,link='simultaneous_proposed_'+str(serial)))
    graph=check_rows(sorted([dict(r) for r in rows],key=lambda r:r['net']),True);rec['proposed_per_net_geometry']=graph
    assert graph['pass'],'Do not promote solver flow with stray or disconnected actual geometry'
    proposal={'scope':'SIMULTANEOUS_LOCAL_FLOW_GEOMETRIC_REPAIR_NATIVE_IMPLEMENTATION_REQUIRED','selected_nets':selected,'retained_selected_material':[r for r in retained if r['net'] in selected and r['kind'] in ['WIRE','VIA']],'solution':solution,'source_SHA':inputs,'region_DBU':region,'full_qualification':False,'all_M1_M10_via10_and_pin_geometry_unchanged':True,'analysis_virtual_groups_represent_only_real_retained_connected_components':True}
    (out/'local_flow_proposal_NOT_IMPLEMENTED.json').write_text(json.dumps(proposal,indent=2)+'\n')
    with gzip.open(str(out/'proposed_branch_geometry_NOT_IMPLEMENTED.tsv.gz'),'wt') as f:
        w=csv.DictWriter(f,fieldnames=['net','layer','x0','y0','x1','y1','kind','link'],delimiter='\t');w.writeheader();w.writerows(rows)
    rec['status']='FEASIBLE_SIMULTANEOUS_GEOMETRY_NOT_NATIVE_IMPLEMENTED';rec['selected_physical_grid_edges']=len(solution);save();print(json.dumps({k:v for k,v in rec.items() if k not in ['actual_retained_anchor_groups','source_SHA','files','proposed_per_net_geometry']},indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--branches',required=True);p.add_argument('--obs',required=True);p.add_argument('--die',required=True);p.add_argument('--out',required=True);p.add_argument('--seconds',type=int,default=180);p.add_argument('--blocker-proof');a=p.parse_args();solve(a.branches,a.obs,a.die,a.out,a.seconds,a.blocker_proof)
