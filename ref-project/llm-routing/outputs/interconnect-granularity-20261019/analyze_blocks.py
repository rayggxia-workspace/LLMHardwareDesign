"""Fixed block cuts over routed nets. Strict origin and conservative service views.
Read-only remote analysis; JSON output is captured in the separate report folder.
"""
import collections,gzip,hashlib,json,re,sys,time,gc
from pathlib import Path
R=Path('/public/home/yuzelu/project-circuit/llm_routing_analysis')
CASES=[('gemmini_4x4','gemmini-4x4-v1',1000),('opentpu_small','opentpu-small-v1',2000),('opentallas_numeric_e1','opentallas-numeric-e1-v1',1000),('opentallas_numeric_e4','opentallas-numeric-e4-v1',1000),('opentallas_vadd8','opentallas-vadd8-v1',1000),('fable5_matvec','fable5-matvec-v1',2000),('llaccel_core','llaccel-html-20261019',2000)]
CONE={'gemmini_4x4':R/'tables/gemmini_4x4_receiver_cones_v1','opentallas_vadd8':R/'tables/opentallas_vadd8_receiver_cones_v2','llaccel_core':R/'side_llaccel_html_20261019/receiver_cones_v1'}
MODELS={};MODEL_HASH={}
for p in [R/'tables/opentallas_vadd8_receiver_cones_v2/liberty_models.json',R/'side_llaccel_html_20261019/receiver_cones_v1/liberty_models.json']:
    b=p.read_bytes();MODELS.update(json.loads(b));MODEL_HASH[str(p)]=hashlib.sha256(b).hexdigest()
def norm(x):return x.replace('\\[','[').replace('\\]',']')
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
    return h.hexdigest()
def recs(p):
    with gzip.open(p,'rt') as f:
        for line in f:yield json.loads(line)
def endpoints(r):return [e for e in r['endpoints'] if e.get('master_type') not in ('CORE_SPACER','CORE_WELLTAP','CORE_ANTENNACELL')]
def model(e):return MODELS.get(e.get('master'),{})
def family(name):return re.sub(r'\[\d+\]','[]',norm(name).split('$_')[0])
def anchor_group(case,name):
    f=family(name)
    if 'numeric' in case:
        return {'result[]':'DOT_RESULT','status[]':'STATUS_RAS','out_poison':'STATUS_RAS','out_valid':'VALID_STATE'}.get(f)
    groups={'ACTIVATION_STORE':['x_mem[][]'],'INPUT_LATCH':['beat_q[]','xline_q[]'],
      'PRODUCT_STAGE':['prod_q[]'],'SUM64_STAGE':['sum64_q[]'],'SUM16_STAGE':['sum16_q[]'],
      'SUM4_STAGE':['sum4_q[]'],'GROUP_SUM_STAGE':['acc_lo_q[]','acc_hi_q[]'],
      'GROUP_SUM_STORE':['acc_bank_lo[][]','acc_bank_hi[][]'],'SCALE_STORE':['scales_q[]'],
      'RETIRE_INPUT':['mac_lo_q[]','mac_hi_q[]','mac_m_q[]'],'SCALE_PRODUCTS':['pa_q[]','pb_q[]'],
      'PRODUCT_SUM':['ps_q[]'],'ROW_ACCUMULATE':['p_acc[]'],'ROUND_STAGE':['rr_mag[]','rr_neg'],
      'OUTPUT_FIFO':['ofifo[][]']}
    for g,names in groups.items():
        if f in names:return g
    # Only retained, named sequential cells enter the explicit remaining-state group.
    return None if re.fullmatch(r'_\d+_',f) else 'CONTROL_TAG_STATE'
def load_named_anchors(case,ident):
    base=R/'raw'/ident if 'numeric' in case else R/'raw/fable5-matvec-v1-final01/analysis'
    top='ot_numeric_dot' if 'numeric' in case else 'matvec_engine';sources={};kept=[]
    for fn in ['mapped.json','final.json']:
        p=base/fn;sources[str(p)]=sha(p);d=json.loads(p.read_bytes())
        cells=d['modules'][top]['cells']
        small={norm(n):c['type'] for n,c in cells.items() if MODELS.get(c['type'],{}).get('kind')=='SEQ' and anchor_group(case,n)}
        kept.append(small);del cells,d;gc.collect()
    return {n:(m,anchor_group(case,n)) for n,m in kept[1].items() if n in kept[0]},sources

def newbucket():return {'nets':0,'missing_length':0,'length_dbu':0,'layers':{},'functions':{},'examples':[]}
def add(tab,key,r):
    a=tab.setdefault(key,newbucket());a['nets']+=1;val=r.get('length_dbu');a['missing_length']+=val is None;a['length_dbu']+=val or 0
    f=r.get('category','UNKNOWN');f=f if f in ('CLOCK','RESET','CONTROL_HANDSHAKE') else 'OTHER';a['functions'][f]=a['functions'].get(f,0)+(val or 0)
    if len(a['examples'])<2:a['examples'].append({'id':r['id'],'name':r['name']})
    for l,v in r.get('layers',{}).items():
        z=a['layers'].setdefault(l,{'nets':0,'length_dbu':0,'min_dbu':v['length_dbu'],'max_dbu':v['length_dbu']});z['nets']+=1;z['length_dbu']+=v['length_dbu'];z['min_dbu']=min(z['min_dbu'],v['length_dbu']);z['max_dbu']=max(z['max_dbu'],v['length_dbu'])
def classify(es,assigned):
    items=[assigned.get(e.get('instance'),(None,'UNKNOWN')) if e['kind']!='BTERM' else ('TOP_IO','SOURCE') for e in es]
    gs={g for g,ev in items if g};bad=any(not g for g,ev in items);inf=any(ev=='INFERRED' for g,ev in items)
    if 'TOP_IO' in gs:key='TOP_INTERFACE'
    elif len(gs)>=2:key='CROSS_PARTIAL' if bad else ('CROSS_INFERRED' if inf else 'CROSS_SOURCE')
    elif bad:key='SHARED_SUPPORT' if any(ev=='SHARED' for g,ev in items) else 'UNRESOLVED'
    elif len(gs)==1 and len(es)>=2:key='INTERNAL_INFERRED' if inf else 'INTERNAL_SOURCE'
    else:key='UNRESOLVED'
    return key,gs,bad

OUTPUT={'schema':1,'model_hashes':MODEL_HASH,'cases':{},'method':'Whole physical net length at explicit fixed cuts. Strict retained source anchors versus source plus exclusive downstream-service assignments. Shared-support cells are never made an artificial single block. Pair sets count each complete two-block net once, with no pair expansion of multi-block nets.'}
for case,ident,u in CASES:
    t=time.time();p=R/'stats'/ident/'dedicated_v2/nets.jsonl.gz';sources={};strict={};enhanced={};cm={};expected_master={};anchors={};cone_counts={}
    custom=case in ('opentallas_numeric_e1','opentallas_numeric_e4','fable5_matvec')
    if custom:anchors,ss=load_named_anchors(case,ident);sources.update(ss)
    if case=='opentallas_vadd8':
        cert=R/'stats/opentallas-vadd8-v1/named_mapping_verification_v2.json';sources[str(cert)]=sha(cert)
        manifest=json.loads((CONE[case]/'manifest.json').read_text());assert sources[str(cert)]==manifest['certification_sha256']
        anchors={norm(x['logical_instance']):(x['final_master'],x['module']) for x in json.loads(cert.read_text())['certified_instances']}
    if case in CONE:
        cp=CONE[case]/'cell_cones.jsonl.gz';sources[str(cp)]=sha(cp)
        for x in recs(cp):
            n=norm(x['cell']);assert n not in cm;expected_master[n]=x['master']
            if x['status']=='EXCLUSIVE':assert len(x['groups'])==1;cm[n]=(x['groups'][0],'INFERRED')
            elif x['status']=='SHARED':cm[n]=(None,'SHARED')
    if case=='opentpu_small':
        bp=R/'unknown-analysis-20261018-v2/resolved_components.jsonl.gz';sources[str(bp)]=sha(bp)
        for x in recs(bp):
            one=len(x['modules'])==1 and not any(e['kind']=='BTERM' for e in x['terminals'])
            for e in x['edges']:
                n=norm(e['instance']);val=(x['modules'][0],'INFERRED') if one else (None,'SHARED')
                assert n not in cm or cm[n]==val;cm[n]=val;expected_master[n]=e['master']
    # For sole-block cases build a conservative ODB graph to retained register families.
    forward=collections.defaultdict(set);bad_nodes=set();direct=collections.defaultdict(set);seen_out=collections.defaultdict(set);comb_masters={};known_cells={};allids=set()
    for r in recs(p):
        if r.get('sig_type') in ('POWER','GROUND'):continue
        assert r['id'] not in allids;allids.add(r['id'])
        es=endpoints(r)
        for e in es:
            if e['kind']=='BTERM':continue
            name=e['instance'];n=norm(name);master=e['master'];m=e.get('module','UNKNOWN')
            if name in known_cells:assert known_cells[name]==master
            known_cells[name]=master
            if custom or case=='opentallas_vadd8':
                if n in anchors:assert anchors[n][0]==master;strict[name]=(anchors[n][1],'SOURCE')
            elif m and m!='UNKNOWN':strict[name]=(m,'SOURCE')
            if n in cm:
                assert expected_master[n]==master
                enhanced[name]=cm[n]
            if custom and model(e).get('kind')=='COMB':comb_masters[name]=master;forward[name]
        if not custom:continue
        ds=[e for e in es if e.get('role')=='driver'];ls=[e for e in es if e.get('role')=='load']
        drivers=[e for e in ds if e['kind']=='ITERM' and model(e).get('kind')=='COMB']
        for e in drivers:
            n=e['instance'];seen_out[n].add(e['pin'])
            if len(ds)!=1 or not ls or len(ds)+len(ls)!=len(es):bad_nodes.add(n)
            for sink in ls:
                if sink['kind']=='BTERM':bad_nodes.add(n);continue
                sm=model(sink);sn=sink['instance'];kind=sm.get('kind')
                if kind=='COMB':forward[n].add(sn)
                elif kind=='SEQ' and sink['pin'] in sm.get('data',[]) and norm(sn) in anchors:
                    assert anchors[norm(sn)][0]==sink['master'];direct[n].add(anchors[norm(sn)][1])
                else:bad_nodes.add(n)
        if len(ds)!=1:
            for sink in ls:
                if sink['kind']=='ITERM' and model(sink).get('kind')=='COMB':bad_nodes.add(sink['instance'])
    if custom:
        for n,m in comb_masters.items():
            if set(MODELS[m].get('outputs',[]))!=seen_out[n]:bad_nodes.add(n)
        reverse=collections.defaultdict(list);pending={n:len(v) for n,v in forward.items()}
        for n,children in forward.items():
            for ch in children:reverse[ch].append(n)
        queue=collections.deque(n for n,v in pending.items() if not v);groups={n:set(direct[n]) for n in forward};bad={n:n in bad_nodes for n in forward};processed=set()
        while queue:
            n=queue.popleft();processed.add(n)
            for parent in reverse[n]:
                groups[parent].update(groups[n]);bad[parent]|=bad[n];pending[parent]-=1
                if pending[parent]==0:queue.append(parent)
        cnt=collections.Counter()
        for n in forward:
            if n not in processed or bad[n] or not groups[n]:cnt['UNKNOWN']+=1
            elif len(groups[n])==1:enhanced[n]=(next(iter(groups[n])),'INFERRED');cnt['EXCLUSIVE']+=1
            else:enhanced[n]=(None,'SHARED');cnt['SHARED']+=1
        cone_counts=dict(cnt)
        # Independent forward traversals for a deterministic sample, including blocked and shared cases.
        samples=[]
        for status in ('EXCLUSIVE','SHARED','UNKNOWN'):
            names=[n for n in sorted(forward) if ('EXCLUSIVE' if enhanced.get(n,(None,''))[1]=='INFERRED' else 'SHARED' if enhanced.get(n,(None,''))[1]=='SHARED' else 'UNKNOWN')==status]
            for n in names[:3]:
                todo=[n];seen=set();term=set();blocked=False
                while todo:
                    v=todo.pop()
                    if v in seen:continue
                    seen.add(v);term.update(direct[v]);blocked|=v in bad_nodes or v not in processed;todo.extend(forward[v])
                result='UNKNOWN' if blocked or not term else 'EXCLUSIVE' if len(term)==1 else 'SHARED'
                assert result==status,(case,n,status,result)
                samples.append({'cell':n,'status':status,'groups':sorted(term),'visited_cells':len(seen),'match':True})
        del forward,reverse,pending,groups,direct,seen_out,comb_masters;gc.collect()
    else:samples=[]
    enhanced.update(strict) # Source evidence has priority; shared/receiver never overrides it.
    views={v:{'classes':{},'pairs':{},'hyperedges':{},'blocks':{}} for v in ('strict','service')}
    allstats={};coverage={v:collections.Counter() for v in views};blockcells={v:collections.Counter() for v in views}
    for v,assignment in [('strict',strict),('service',enhanced)]:
        for n in known_cells:
            g,ev=assignment.get(n,(None,'UNKNOWN'));coverage[v][ev]+=1
            if g:blockcells[v][g]+=1
    for r in recs(p):
        if r.get('sig_type') in ('POWER','GROUND'):continue
        assert sum(v['length_dbu'] for v in r.get('layers',{}).values())==(r.get('length_dbu') or 0)
        add(allstats,'ALL',r);es=endpoints(r)
        for v,assignment in [('strict',strict),('service',enhanced)]:
            cls,gs,unknown=classify(es,assignment);vv=views[v];add(vv['classes'],cls,r)
            for block in gs-{'TOP_IO'}:
                b=vv['blocks'].setdefault(block,{'internal':{},'incident_cross':{},'incident_unresolved':{},'top_interface':{}})
                target='top_interface' if 'TOP_IO' in gs else 'incident_cross' if len(gs)>=2 else 'incident_unresolved' if unknown else 'internal'
                add(b[target],'ALL',r)
            if not unknown and len(gs)==2:
                key=' <-> '.join(sorted(gs));add(vv['pairs'],key,r)
            elif len(gs)>=3:
                key=' + '.join(sorted(gs))+(' + UNKNOWN' if unknown else '');add(vv['hyperedges'],key,r)
    actualhash=sha(p);sources[str(p)]=actualhash
    if case in CONE:assert actualhash==json.loads((CONE[case]/'manifest.json').read_text())['nets_sha256']
    for v in views.values():
        assert sum(x['nets'] for x in v['classes'].values())==allstats['ALL']['nets']
        assert sum(x['length_dbu'] for x in v['classes'].values())==allstats['ALL']['length_dbu']
        for l,z in allstats['ALL']['layers'].items():assert sum(x['layers'].get(l,{}).get('length_dbu',0) for x in v['classes'].values())==z['length_dbu']
    OUTPUT['cases'][case]={'units':u,'source_sha256':actualhash,'all':allstats['ALL'],'views':views,'connected_cell_coverage':{k:dict(v) for k,v in coverage.items()},'block_cells':{k:dict(v) for k,v in blockcells.items()},'input_hashes':sources,'new_odb_cone_status':cone_counts,'independent_forward_samples':samples,'new_cone_limit':'ODB topology plus exact named mapped/final sequential anchors; not a full independent final-netlist connectivity check. All outputs followed; top output, control pins, ambiguous drivers, unsupported and cyclic paths block assignment.' if custom else None,'elapsed_seconds':round(time.time()-t,2)}
    print(case,allstats['ALL']['nets'],dict(coverage['service']),round(time.time()-t,1),file=sys.stderr,flush=True)
    del known_cells,strict,enhanced,cm,expected_master,anchors;gc.collect()
print(json.dumps(OUTPUT,ensure_ascii=False))
