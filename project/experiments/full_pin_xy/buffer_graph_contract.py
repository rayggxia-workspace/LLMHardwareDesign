"""Pure mapped endpoint proof; no filesystem or physical-flow globals."""
from pathlib import Path
from collections import defaultdict,deque
from cell_semantics import check_pair,contract


class DSU:
    def __init__(self):self.p={}
    def find(self,x):
        if x not in self.p:self.p[x]=x
        root=x
        while self.p[root]!=root:root=self.p[root]
        while x!=root:
            parent=self.p[x];self.p[x]=root;x=parent
        return root
    def union(self,a,b):self.p[self.find(a)]=self.find(b)


def identity_buffer(text,name):
    q=contract(text,name);assert not q['state'],('New stateful cell',name)
    ins=[pin for pin,fields in q['pins'] if ('direction','input') in fields]
    outs=[(pin,dict(fields).get('function')) for pin,fields in q['pins'] if ('direction','output') in fields]
    assert len(q['pins'])==2 and len(ins)==len(outs)==1,(name,'Not a two-pin buffer')
    assert outs[0][1]=='"'+ins[0]+'"',(name,'New cell is not an exact identity buffer')
    return ins[0],outs[0][0],q


def compare(a,at,ap,b,bt,bp,libtext,libpath):
    missing=set(a)-set(b);assert not missing,('Original nonfiller cells removed',len(missing),sorted(missing)[:10])
    added=set(b)-set(a);assert set(ap)==set(bp),'Original port set changed'
    original_terms={k:v for k,v in bt.items() if k[0] in a}
    assert set(at)==set(original_terms),'Original endpoint set changed'
    contracts=[];pair_cache={}
    for n in sorted(a):
        assert a[n][1]==b[n][1],('Original master class changed',n)
        if a[n][0]!=b[n][0]:
            pair=(a[n][0],b[n][0])
            if pair not in pair_cache:pair_cache[pair]=check_pair([Path(libpath)],pair[0],pair[1],lambda p:libtext)
            contracts.append(dict(instance=n,proof=pair_cache[pair]))
    per_new=defaultdict(dict)
    for (inst,pin),value in bt.items():
        if inst in added:per_new[inst][pin]=value
    models={};edges=[];dsu=DSU();adj=defaultdict(list);indegree=defaultdict(int)
    for n in sorted(added):
        master=b[n][0]
        if master not in models:models[master]=identity_buffer(libtext,master)
        ip,op,model=models[master];terms=per_new[n]
        assert set(terms)=={ip,op},(n,'New buffer terminals missing/extra')
        assert terms[ip][0]=='INPUT' and terms[op][0]=='OUTPUT'
        src,dst=terms[ip][1],terms[op][1];assert src!='NULL' and dst!='NULL' and src!=dst,(n,'Undriven or self-loop buffer')
        edges.append((src,dst,n));dsu.union(src,dst);adj[src].append(dst);indegree[dst]+=1;indegree.setdefault(src,0)
    queue=deque(n for n,k in indegree.items() if k==0);visited=0
    while queue:
        n=queue.popleft();visited+=1
        for nxt in adj[n]:
            indegree[nxt]-=1
            if indegree[nxt]==0:queue.append(nxt)
    assert visited==len(indegree),'Added identity-buffer graph contains a cycle'
    # Endpoint keys retain terminal identity. NULL is checked per endpoint,
    # never treated as one shared electrical net.
    ref={('I',)+k:v for k,v in at.items()};cur={('I',)+k:v for k,v in original_terms.items()}
    ref.update({('P',n):v for n,v in ap.items()});cur.update({('P',n):v for n,v in bp.items()})
    groups=defaultdict(list);old_to_new=defaultdict(set);new_to_old=defaultdict(set);nulls=0
    for key,(direction,net) in ref.items():
        got_direction,got_net=cur[key];assert direction==got_direction,(key,'Direction changed')
        assert direction in ['INPUT','OUTPUT'],('Unsupported bidirectional signal endpoint',key,direction)
        if net=='NULL':assert got_net=='NULL',(key,'Originally unconnected pin changed');nulls+=1;continue
        assert got_net!='NULL',(key,'Original connected endpoint became unconnected')
        root=dsu.find(got_net);old_to_new[net].add(root);new_to_old[root].add(net);groups[net].append((key,direction,got_net))
    assert all(len(v)==1 for v in old_to_new.values()),'An original logical net split after buffer elimination'
    assert all(len(v)==1 for v in new_to_old.values()),'Different original nets were merged by new buffers'
    def driver(key,d):return (key[0]=='I' and d=='OUTPUT') or (key[0]=='P' and d=='INPUT')
    edge_groups=defaultdict(list)
    for src,dst,n in edges:edge_groups[dsu.find(src)].append((src,dst,n))
    buffer_roots=set(edge_groups);source_checked=0;driverless=0;single_driver_groups=0
    for net,terms in groups.items():
        sources={n for key,d,n in terms if driver(key,d)};root=next(iter(old_to_new[net]))
        if not sources:
            assert root not in buffer_roots,('New buffers on an originally driverless component',net)
            driverless+=1;continue
        reachable=set(sources);work=deque(sources)
        while work:
            for nxt in adj[work.popleft()]:
                if nxt not in reachable:reachable.add(nxt);work.append(nxt)
        assert all(n in reachable for key,d,n in terms),(net,'Identity buffers connected in the wrong direction')
        if len([1 for key,d,n in terms if driver(key,d)])==1:
            drivers=defaultdict(int)
            for n in sources:drivers[n]+=1
            for src,dst,name in edge_groups[root]:drivers[dst]+=1
            assert all(k==1 for k in drivers.values()),(net,'New multiple-driver wire')
            single_driver_groups+=1
        source_checked+=1
    assert buffer_roots<=set(new_to_old),'Added buffer island has no original endpoint contract'
    return {'all_original_instances_retained':True,'all_original_terminal_sets_directions_preserved':True,
      'original_net_partition_equal_after_buffer_elimination':True,'directed_original_driver_reachability':True,
      'added_buffer_graph_acyclic':True,'null_terminals_checked_individually':nulls,
      'original_nonfiller_instances':len(a),'actual_nonfiller_instances':len(b),'added_identity_buffers':len(added),
      'resized_original_instances':len(contracts),'original_signal_terminals':len(at),'top_ports':len(ap),
      'original_net_components':len(groups),'original_driven_components_checked':source_checked,
      'original_driverless_components_unchanged':driverless,'single_driver_components_checked':single_driver_groups,
      'changed_original_master_contracts':contracts,'new_buffer_master_contracts':{n:q[2] for n,q in models.items()}}
