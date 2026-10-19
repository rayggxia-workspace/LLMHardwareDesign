"""Read-only remote MXU analysis. Writes gzip JSON to stdout; no remote files changed.

Uses all physical endpoints and Liberty pin models. Inference means exclusive
downstream service, never recovered RTL ownership. Source labels always win.
"""
import collections, gzip, hashlib, json, re, sys, time
from pathlib import Path

R = Path('/public/home/yuzelu/project-circuit/llm_routing_analysis')
NETS = R/'stats/opentpu-small-v1/dedicated_v2/nets.jsonl.gz'
GEO = R/'stats/opentpu-small-v1/dedicated_v2/geometry.jsonl.gz'
LIB = R/'side_llaccel_html_20261019/receiver_cones_v1/liberty_models.json'
MODELS = json.loads(LIB.read_bytes())
U = 2000
EXCLUDE = {'CORE_SPACER', 'CORE_WELLTAP', 'CORE_ANTENNACELL'}
START = time.time()

def note(s):print(s, file=sys.stderr, flush=True)
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
    return h.hexdigest()
def records(p):
    with gzip.open(p,'rt') as f:
        for s in f:yield json.loads(s)
def model(e):return MODELS.get(e.get('master'),{})

# classify() and norm() are prepended from the reviewed local source classifier.
info={}; source={}; nodes=set(); graph=collections.defaultdict(set)
direct=collections.defaultdict(set); reasons=collections.defaultdict(set)
seen_outputs=collections.defaultdict(set)

def remember(e):
    if e['kind']!='ITERM':return
    n=norm(e['instance']);mod=e.get('module','UNKNOWN')
    if mod not in ('MXU','UNKNOWN'):return
    if n in info:
        assert info[n]==(e['master'],mod)
        return
    info[n]=(e['master'],mod)
    seed=classify(n) if mod=='MXU' else None
    if seed and seed[0]!='INTERNAL_UNCLASSIFIED':source[n]=seed[:2]
    elif model(e).get('kind')=='COMB':nodes.add(n);graph[n]

for r in records(NETS):
    if r.get('sig_type') in ('POWER','GROUND'):continue
    es=[e for e in r['endpoints'] if e.get('master_type') not in EXCLUDE]
    for e in es:remember(e)
    drivers=[e for e in es if e.get('role')=='driver']
    loads=[e for e in es if e.get('role')=='load']
    for e in drivers:
        if e['kind']!='ITERM':continue
        n=norm(e['instance'])
        if n not in nodes:continue
        seen_outputs[n].add(e['pin'])
        if len(drivers)!=1:reasons[n].add('AMBIGUOUS_DRIVER')
        if not loads:reasons[n].add('DANGLING_OUTPUT')
        if len(drivers)+len(loads)!=len(es):reasons[n].add('UNCLASSIFIED_ENDPOINT_ROLE')
        for t in loads:
            if t['kind']=='BTERM':reasons[n].add('TOP_OUTPUT');continue
            sn=norm(t['instance']);sm=model(t)
            if sn in source:
                if sm.get('kind')=='SEQ' and t['pin'] not in sm.get('data',[]):
                    reasons[n].add('SEQUENTIAL_NON_DATA_PIN')
                elif sm.get('kind')=='COMB' and t['pin'] in sm.get('inputs',[]):direct[n].add(source[sn])
                elif sm.get('kind')=='SEQ':direct[n].add(source[sn])
                elif t.get('master_type','').startswith('BLOCK') and t.get('io_type')=='INPUT':
                    if re.search(r'(^|[_.])(clk|clock|ck|reset|rst)($|[_.])',t['pin'],re.I):reasons[n].add('MACRO_CLOCK_RESET')
                    else:direct[n].add(source[sn])
                else:reasons[n].add('UNSUPPORTED_ANCHOR_PIN')
            elif sn in nodes:graph[n].add(sn)
            elif t.get('module','UNKNOWN') not in ('UNKNOWN','MXU'):reasons[n].add('EXTERNAL_MODULE_TERMINAL')
            elif sm.get('kind')=='SEQ':reasons[n].add('UNCLASSIFIED_SEQUENTIAL_TERMINAL')
            else:reasons[n].add('UNSUPPORTED_TERMINAL')

for n in nodes:
    expected=set(MODELS[info[n][0]]['outputs'])
    if seen_outputs[n]!=expected:reasons[n].add('MISSING_OR_UNSUPPORTED_OUTPUT')
pending={n:len(graph[n]) for n in nodes};reverse=collections.defaultdict(list)
for n,children in graph.items():
    for c in children:reverse[c].append(n)
queue=collections.deque(n for n,p in pending.items() if not p)
targets={n:set(direct[n]) for n in nodes};blocked={n:set(reasons[n]) for n in nodes};processed=set()
while queue:
    n=queue.popleft();processed.add(n)
    if not targets[n] and not blocked[n]:blocked[n].add('NO_TERMINAL')
    for parent in reverse[n]:
        targets[parent].update(targets[n]);blocked[parent].update(blocked[n]);pending[parent]-=1
        if not pending[parent]:queue.append(parent)
for n in nodes-processed:blocked[n].add('REACHES_COMBINATIONAL_CYCLE')

enhanced=dict(source); evidence={n:'SOURCE' for n in source}; leaf_evidence=dict(evidence)
status={}; status_counts=collections.Counter(); source_unknown_status=collections.Counter()
for n in nodes:
    gs={g for g,l in targets[n]};ls={l for g,l in targets[n]}
    if blocked[n] or not gs:s='BLOCKED'
    elif len(gs)>1:s='SHARED_GROUPS'
    elif len(ls)>1:s='EXCLUSIVE_GROUP_SHARED_LEAVES'
    else:s='EXCLUSIVE_LEAF'
    status[n]=s;status_counts[s]+=1
    if info[n][1]=='MXU':source_unknown_status[s]+=1
    if s in ('EXCLUSIVE_LEAF','EXCLUSIVE_GROUP_SHARED_LEAVES'):
        enhanced[n]=(next(iter(gs)),next(iter(ls)) if len(ls)==1 else None)
        evidence[n]='EXCLUSIVE_SERVICE';leaf_evidence[n]='EXCLUSIVE_SERVICE' if len(ls)==1 else 'SHARED_LEAVES'

# Independent walks on the same ODB graph check the dynamic-programming result.
samples=[]
for s in sorted(set(status.values())):
    pool=sorted(n for n in nodes if status[n]==s and info[n][1]=='MXU')
    for n in pool[:4]:
        todo=[n];seen=set();terms=set();rs=set()
        while todo:
            v=todo.pop()
            if v in seen:continue
            seen.add(v);terms.update(direct[v]);rs.update(reasons[v]);todo.extend(graph[v])
            if v not in processed:rs.add('REACHES_COMBINATIONAL_CYCLE')
        gs={g for g,l in terms};ls={l for g,l in terms}
        test='BLOCKED' if rs or not gs else 'SHARED_GROUPS' if len(gs)>1 else 'EXCLUSIVE_GROUP_SHARED_LEAVES' if len(ls)>1 else 'EXCLUSIVE_LEAF'
        assert test==s,(n,s,test)
        if n in processed:assert terms==targets[n],n
        samples.append({'cell':n,'status':s,'terminals':sorted(terms),'reasons':sorted(rs),'visited':len(seen),'match':True})
note('Graph complete: '+str(dict(source_unknown_status))+' elapsed '+str(round(time.time()-START)))

ROLE={
 'PE':'INTEGER_CORE','COLUMN_END':'INTEGER_CORE','COLUMN_ALIGN':'INTEGER_CORE','RESULT_PACK':'INTEGER_CORE',
 'INPUT_PREP':'INPUT_SUPPORT','INPUT_ALIGN':'INPUT_SUPPORT','WEIGHT_FIFO':'INPUT_SUPPORT','WEIGHT_FIFO_CONTROL':'INPUT_SUPPORT',
 'SCALE_FIFO':'INPUT_SUPPORT','SCALE_FIFO_CONTROL':'INPUT_SUPPORT','SCALE_RESPONSE':'INPUT_SUPPORT',
 'RESULT_FIFO':'RESULT_BUFFER','FP_EPILOGUE':'FP_EPILOGUE','ACC_RMW':'ACC_RMW',
 'POSTPROCESS_STATE':'POSTPROCESS_STATE','DRAIN':'DRAIN','CONTROL_SHARED':'CONTROL_SHARED'}

def bucket():return {'nets':0,'length_dbu':0,'layers':{},'examples':[]}
def add(tab,key,r,es=None):
    z=tab.setdefault(key,bucket());z['nets']+=1;z['length_dbu']+=r.get('length_dbu') or 0
    for l,v in r.get('layers',{}).items():
        q=z['layers'].setdefault(l,{'length_dbu':0,'nets':0,'min_dbu':v['length_dbu'],'max_dbu':v['length_dbu']})
        q['length_dbu']+=v['length_dbu'];q['nets']+=1;q['min_dbu']=min(q['min_dbu'],v['length_dbu']);q['max_dbu']=max(q['max_dbu'],v['length_dbu'])
    if len(z['examples'])<2:
        a={'id':r['id'],'name':r['name'],'category':r.get('category'),'sig_type':r.get('sig_type')}
        if es is not None:a['endpoints']=[{'instance':e.get('instance','TOP_IO'),'pin':e.get('pin'),'role':e.get('role'),'module':e.get('module')} for e in es[:20]]
        z['examples'].append(a)

def fine_family(gs):
    ps=[re.fullmatch(r'PE\[(\d+),(\d+)\]',x) for x in gs]
    if all(ps) and len(ps)==2:
        a,b=[tuple(map(int,m.groups())) for m in ps]
        if a[0]!=b[0]:return 'PE–PE: different columns'
        return 'PE–PE: same chain' if a[1]//4==b[1]//4 else 'PE–PE: different chains, same column'
    def simple(s):
        if s.startswith('PE['):return 'PE'
        if s.startswith('COLUMN_END['):return 'COLUMN_END'
        if s.startswith('ACT_SKEW['):return 'ACT_SKEW'
        if s.startswith('WEIGHT_SKEW['):return 'WEIGHT_SKEW'
        if s.startswith('COL_ALIGN['):return 'COLUMN_ALIGN'
        if s.startswith('RESULT_FIFO_COPY['):return 'RESULT_FIFO'
        if s.startswith('WEIGHT_FIFO['):return 'WEIGHT_FIFO'
        if s.startswith('SCALE_FIFO['):return 'SCALE_FIFO'
        if s.startswith('FP_EPILOGUE['):return 'FP_EPILOGUE'
        if s.startswith('ACC_RMW['):return 'ACC_RMW'
        return s
    return ' + '.join(sorted({simple(s) for s in gs}))

views={v:{g:{k:{} for k in ['classes','internal_groups','complete_pairs','complete_multi','partial_pairs','partial_multi','connection_families']} for g in ['group','leaf','role']} for v in ['strict','service']}
allnets={};scope={};scope_ids=set();boundary={};no_wire=collections.Counter()
selected={n for n,(m,mod) in info.items() if mod=='MXU'}|set(enhanced)

def labels(es,assignment,gran):
    gs=set();bad=False;external=set();inf=False
    for e in es:
        if e['kind']=='BTERM':external.add('TOP_IO');continue
        n=norm(e['instance']);mod=e.get('module','UNKNOWN')
        if n in assignment:
            group,leaf=assignment[n]
            label=ROLE[group] if gran=='role' else group if gran=='group' else leaf
            if label is None:bad=True
            else:gs.add(label)
            inf|=n not in source
        elif assignment is enhanced and gran=='role' and status.get(n)=='SHARED_GROUPS' and len({ROLE[g] for g,l in targets[n]})==1:
            gs.add(next(iter({ROLE[g] for g,l in targets[n]})));inf=True
        elif mod not in ('MXU','UNKNOWN'):external.add(mod)
        else:bad=True
    return gs,bad,external,inf

for r in records(NETS):
    if r.get('sig_type') in ('POWER','GROUND'):continue
    es=[e for e in r['endpoints'] if e.get('master_type') not in EXCLUDE]
    assert sum(v['length_dbu'] for v in r.get('layers',{}).values())==(r.get('length_dbu') or 0)
    add(allnets,'ALL',r)
    if not any(e['kind']=='ITERM' and norm(e['instance']) in selected for e in es):continue
    assert r['id'] not in scope_ids;scope_ids.add(r['id']);add(scope,'ALL',r)
    if not r.get('dbwire_present'):no_wire['nets']+=1
    dedicated=r.get('sig_type')=='CLOCK' or r.get('category') in ('CLOCK','RESET')
    for v,assignment in [('strict',source),('service',enhanced)]:
        for gran in ['group','leaf','role']:
            t=views[v][gran];gs,bad,ext,inf=labels(es,assignment,gran)
            if dedicated:kind='CLOCK_RESET'
            elif ext:kind='BOUNDARY_PARTIAL' if bad else 'BOUNDARY_COMPLETE'
            elif bad:kind='PARTIAL_CROSS' if len(gs)>=2 else 'UNRESOLVED_SUPPORT'
            elif len(gs)>=2:kind='CROSS_INFERRED' if inf else 'CROSS_SOURCE'
            elif len(gs)==1:kind='INTERNAL_INFERRED' if inf else 'INTERNAL_SOURCE'
            else:kind='UNRESOLVED_SUPPORT'
            add(t['classes'],kind,r)
            if dedicated or ext:continue
            if not bad and len(gs)==1:add(t['internal_groups'],next(iter(gs)),r,es)
            if len(gs)>=2:
                key=' + '.join(sorted(gs));which=('partial_' if bad else 'complete_')+('pairs' if len(gs)==2 else 'multi')
                add(t[which],key,r,es)
                if gran=='leaf' and not bad and len(gs)==2:add(t['connection_families'],fine_family(gs),r,es)
    gs,bad,ext,inf=labels(es,enhanced,'group')
    if ext and not dedicated:add(boundary,' + '.join(sorted(ext))+(' + UNRESOLVED' if bad else ''),r,es)

for v in views.values():
    for t in v.values():
        assert sum(z['nets'] for z in t['classes'].values())==scope['ALL']['nets']
        assert sum(z['length_dbu'] for z in t['classes'].values())==scope['ALL']['length_dbu']
        for l,a in scope['ALL']['layers'].items():assert sum(z['layers'].get(l,{}).get('length_dbu',0) for z in t['classes'].values())==a['length_dbu']
        cross=sum(t['classes'].get(k,{}).get('length_dbu',0) for k in ['CROSS_SOURCE','CROSS_INFERRED','PARTIAL_CROSS'])
        assert cross==sum(z['length_dbu'] for k in ['complete_pairs','complete_multi','partial_pairs','partial_multi'] for z in t[k].values())
note('Routing complete, scoped nets '+str(scope['ALL']['nets'])+' elapsed '+str(round(time.time()-START)))

rows=[];found=set();cellcounts=collections.Counter();groupcounts=collections.Counter();areacounts=collections.Counter()
for r in records(GEO):
    if r['type']!='instance':break
    n=norm(r['name'])
    if n not in selected:continue
    assert n not in found;found.add(n)
    assert info[n][0]==r['master'],(n,info[n],r['master'])
    sg,sl=source.get(n,(None,None));eg,el=enhanced.get(n,(None,None))
    ev='SOURCE' if sg else 'EXCLUSIVE_SERVICE' if eg else status.get(n,'UNSUPPORTED_STATE')
    cellcounts[ev]+=1;groupcounts[eg or 'UNRESOLVED_SHARED']+=1
    b=r['box_dbu'];area=(b[2]-b[0])*(b[3]-b[1])/U**2;areacounts[eg or 'UNRESOLVED_SHARED']+=area
    rows.append([n,r['master'],b,info[n][1],sg,sl,eg,el,ev])
assert found==selected,('geometry mismatch',len(selected-found),list(selected-found)[:10])
assert sum(mod=='MXU' for m,mod in info.values())==147068
assert len(source)==63445

audit=[]
for n in sorted(selected):
    if n in source:continue
    audit.append({'cell':n,'master':info[n][0],'original_module':info[n][1],
                  'status':status.get(n,'UNSUPPORTED_STATE'),'groups':sorted({g for g,l in targets.get(n,set())}),
                  'terminals':sorted(targets.get(n,set())),'reasons':sorted(blocked.get(n,set()))})
out={'schema':1,'units':U,'all_case':allnets['ALL'],'scope':scope['ALL'],'views':views,'boundary':boundary,
     'source_mxu_cells':147068,'source_seed_cells':len(source),'cell_evidence_counts':dict(cellcounts),
     'cell_group_counts':dict(groupcounts),'cell_group_area_um2':dict(areacounts),
     'role_only_service_cells':{n:next(iter({ROLE[g] for g,l in targets[n]})) for n in nodes if status[n]=='SHARED_GROUPS' and len({ROLE[g] for g,l in targets[n]})==1},'original_unclassified_cones':dict(source_unknown_status),'graph_status':dict(status_counts),'independent_samples':samples,
     'geometry_rows':rows,'receiver_audit':audit,'no_dbwire':dict(no_wire),'roles':ROLE,
     'sha256':{'nets':sha(NETS),'geometry':sha(GEO),'liberty_models':sha(LIB)},
     'elapsed_seconds':round(time.time()-START,2),
     'method':'Whole physical nets touching source-MXU or exclusively MXU-service endpoints; source-first anchors, conservative all-output ODB cones, all unclassified branches block exclusivity. No register bypass, no all-pairs hyperedge expansion, no branch-exclusive length claim.'}
note('Done '+str(out['elapsed_seconds'])+' seconds')
sys.stdout.buffer.write(gzip.compress(json.dumps(out,ensure_ascii=False,separators=(',',':')).encode(),compresslevel=3))
