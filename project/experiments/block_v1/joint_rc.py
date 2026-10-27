"""Measured node-pair charge -> passive distributed RC -> SPEF.

This is an assembly/import contract. Independent field qualification, exact
geometry, native/new-layer ownership and complete block qualification are separate.
No capacitance is allocated by wire length or by multiplying marginal charges.
"""
import copy
import math
import re


def finite(value):
    assert type(value)in (float,int)and math.isfinite(value)
    return float(value)


def endpoint(net,node):return net+'/'+node


def assemble(nodes,edges,rows):
    names=list(nodes);assert len(names)>=2 and set(edges)==set(rows)==set(names)
    points={};labels={};ground={};self_charge={};sigma={};directional={}
    for net in names:
        assert re.fullmatch(r'[A-Za-z][A-Za-z0-9_]*',net)
        labels[net]=[n for n,p in nodes[net]]
        assert len(labels[net])>=2 and len(set(labels[net]))==len(labels[net])
        points[net]={}
        for node,p in nodes[net]:
            assert re.fullmatch(r'[A-Za-z][A-Za-z0-9_]*',node)and len(p)==3
            points[net][node]=tuple(finite(v)for v in p)
        assert len(set(points[net].values()))==len(points[net])
    for net in names:
        row=rows[net];assert row['master']==net and row['nodes']==labels[net]
        entries={e['net']:e for e in row['entries']}
        assert len(entries)==len(row['entries'])and set(entries)==set(names)|{'ground'}
        assert {e['net']for e in row['captures']}==set(names)|{'ground'}
        for other in names+['ground']:
            e=entries[other];assert len(e['partial'])==len(e['partial_sigma'])==len(labels[net])
            values=[finite(v)for v in e['partial']];uncertainty=[finite(v)for v in e['partial_sigma']]
            assert all(v>=0 for v in uncertainty)
            assert math.isclose(sum(values),finite(e['cap']),rel_tol=1e-10,abs_tol=1e-10)
            if other=='ground':
                for i,node in enumerate(labels[net]):
                    ground[endpoint(net,node)]=-values[i];sigma[endpoint(net,node)]=uncertainty[i]
                    assert ground[endpoint(net,node)]>0,'Nonpositive measured node ground charge'
            elif other==net:
                for i,node in enumerate(labels[net]):self_charge[endpoint(net,node)]=values[i]
            else:
                captures=[c for c in row['captures']if c['net']==other]
                assert [c['node']for c in captures]==labels[other]
                for j,c in enumerate(captures):
                    assert len(c['partial'])==len(c['partial_sigma'])==len(labels[net])
                    for i,node in enumerate(labels[net]):
                        v=finite(c['partial'][i]);s=finite(c['partial_sigma'][i]);assert v<0 and s>=0
                        directional[(endpoint(net,node),endpoint(other,labels[other][j]))]=(-v,s)
                for i in range(len(labels[net])):
                    assert math.isclose(sum(c['partial'][i]for c in captures),values[i],rel_tol=1e-10,abs_tol=1e-10)
    couplings=[];diagonal=dict(ground);uncertainty=dict(sigma)
    for (a,b),(forward,sa)in sorted(directional.items()):
        if a>b:continue
        reverse,sb=directional[(b,a)]
        # Arithmetic symmetrization is explicit and bounded; it must not replace
        # the source's independent local/FV/reciprocity scientific gates.
        cap=(forward+reverse)/2;s=(sa+sb)/2
        couplings.append(dict(a=a,b=b,ff=cap,sigma_ff=s,forward_ff=forward,reverse_ff=reverse))
        for node in [a,b]:diagonal[node]+=cap;uncertainty[node]+=s
    conservation={}
    for key in ground:
        net=key.split('/')[0];total=finite(next(e['cap']for e in rows[net]['entries']if e['net']==net))
        difference=abs(diagonal[key]-self_charge[key])
        allowed=.01*total+5*(uncertainty[key]+finite(next(e for e in rows[net]['entries']if e['net']==net)['partial_sigma'][labels[net].index(key.split('/')[1])]))
        conservation[key]=dict(measured_self_ff=self_charge[key],assembled_diagonal_ff=diagonal[key],difference_ff=difference,allowed_ff=allowed)
        assert difference<=allowed,'Symmetrization changed measured node self charge beyond locked offset-scale bound'
    resistors=[]
    for net in names:
        adjacent={node:set()for node in labels[net]};seen=set()
        for edge in edges[net]:
            a,b=edge['a'],edge['b'];value=finite(edge['ohm']);assert value>0 and a!=b and {a,b}<=set(labels[net])
            key=tuple(sorted((a,b)));assert key not in seen;seen.add(key)
            adjacent[a].add(b);adjacent[b].add(a)
            resistors.append(dict(a=endpoint(net,a),b=endpoint(net,b),ohm=value))
        visited=set();todo=[labels[net][0]]
        while todo:
            node=todo.pop()
            if node not in visited:visited.add(node);todo.extend(adjacent[node])
        assert visited==set(labels[net]),'Disconnected DC graph'
    return dict(schema='block-v1-measured-joint-rc/1',nets=names,nodes=points,ground_ff=ground,
        coupling=couplings,resistors=resistors,node_conservation=conservation,
        symmetrization='Arithmetic mean of independently measured directions after scientific acceptance; sigma uses arithmetic mean, without independence assumption',
        qualified_full_block=False,qualified_boundary_stitch=False)


def emit_spef(model,variant='actual'):
    model=copy.deepcopy(model);assert variant in ('actual','wrong-unit','missing-coupling','permuted-ground','permuted-resistance','rewired-coupling')
    names=model['nets'];nodes=[endpoint(n,k)for n in names for k in model['nodes'][n]]
    ids={n:i+1 for i,n in enumerate(names)}
    instances={node:'E%d'%i for i,node in enumerate(nodes)}
    mapping={node:len(names)+i+1 for i,node in enumerate(nodes)}
    native={node:node.split('/')[0]+'/I:'+instances[node]+'/p'for node in nodes}
    if variant=='missing-coupling':model['coupling'].pop()
    elif variant=='permuted-ground':
        group=[n for n in nodes if n.split('/')[0]==names[0]]
        a=min(group,key=model['ground_ff'].get);b=max(group,key=model['ground_ff'].get)
        assert abs(model['ground_ff'][a]-model['ground_ff'][b])>1e-6
        model['ground_ff'][a],model['ground_ff'][b]=model['ground_ff'][b],model['ground_ff'][a]
    elif variant=='permuted-resistance':
        a=min(model['resistors'],key=lambda e:e['ohm']);b=max(model['resistors'],key=lambda e:e['ohm'])
        assert abs(a['ohm']-b['ohm'])>1e-6;a['ohm'],b['ohm']=b['ohm'],a['ohm']
    elif variant=='rewired-coupling':
        pair=names[:2];left=[endpoint(pair[0],n)for n in list(model['nodes'][pair[0]])[:2]]
        right=[endpoint(pair[1],n)for n in list(model['nodes'][pair[1]])[:2]]
        lookup={tuple(sorted((c['a'],c['b']))):c for c in model['coupling']}
        cells=[lookup[tuple(sorted((a,b)))]for a in left for b in right]
        delta=.8*min(cells[0]['ff'],cells[3]['ff'])
        for c,sign in zip(cells,[-1,1,1,-1]):c['ff']+=sign*delta;assert c['ff']>0
    text='*SPEF "IEEE 1481-1998"\n*DESIGN "joint_rc_probe"\n*DATE "2026-10-27"\n*VENDOR "LLMHardwareDesign"\n*PROGRAM "measured-joint-rc"\n*VERSION "1"\n*DIVIDER /\n*DELIMITER :\n*BUS_DELIMITER [ ]\n*T_UNIT 1 NS\n*C_UNIT 1 '+('PF'if variant=='wrong-unit'else'FF')+'\n*R_UNIT 1 OHM\n*L_UNIT 1 UH\n*NAME_MAP\n'
    text+=''.join('*%d %s\n'%(ids[n],n)for n in names)
    text+=''.join('*%d %s\n'%(mapping[n],instances[n])for n in nodes)
    label=lambda node:'*%d:p'%mapping[node]
    for net in names:
        owned=[n for n in nodes if n.split('/')[0]==net]
        coupling=[c for c in model['coupling']if c['a']in owned or c['b']in owned]
        total=sum(model['ground_ff'][n]for n in owned)+sum(c['ff']for c in coupling)
        text+='\n*D_NET *%d %.17g\n*CONN\n'%(ids[net],total)
        text+=''.join('*I %s B\n'%label(n)for n in owned)+'*CAP\n';index=1
        for n in owned:text+='%d %s %.17g\n'%(index,label(n),model['ground_ff'][n]);index+=1
        for c in coupling:text+='%d %s %s %.17g\n'%(index,label(c['a']),label(c['b']),c['ff']);index+=1
        text+='*RES\n';index=1
        for r in model['resistors']:
            if r['a']in owned:text+='%d %s %s %.17g\n'%(index,label(r['a']),label(r['b']),r['ohm']);index+=1
        text+='*END\n'
    return text,instances,native


def receive(folder,model,native):
    def table(name,count):
        rows=[line.split('\t')for line in(folder/name).read_text().splitlines()];assert all(len(r)==count for r in rows)
        values={tuple(r[:-1]):finite(float(r[-1]))for r in rows};assert len(values)==len(rows)
        return values
    ground={k[0]:v for k,v in table('nodes.tsv',2).items()}
    resistance=table('resistors.tsv',3);coupling=table('coupling.tsv',3)
    expected_g={native[k]:v for k,v in model['ground_ff'].items()}
    expected_r={tuple(sorted((native[r['a']],native[r['b']]))):r['ohm']for r in model['resistors']}
    expected_c={tuple(sorted((native[c['a']],native[c['b']]))):c['ff']for c in model['coupling']}
    def equal(actual,expected):
        return set(actual)==set(expected)and all(math.isfinite(actual[k])and abs(actual[k]-v)<=1e-8+2e-6*abs(v)for k,v in expected.items())
    checks=dict(exact_node_ground=equal(ground,expected_g),exact_edge_resistance=equal(resistance,expected_r),
        exact_node_pair_coupling=equal(coupling,expected_c),positive_ground=all(v>0 for v in ground.values()),
        positive_coupling=all(v>0 for v in coupling.values()))
    return dict(passed=all(checks.values()),checks=checks,ground_ff=ground,
        resistor_ohm=[dict(a=a,b=b,value=v)for (a,b),v in resistance.items()],
        coupling_ff=[dict(a=a,b=b,value=v)for (a,b),v in coupling.items()])
