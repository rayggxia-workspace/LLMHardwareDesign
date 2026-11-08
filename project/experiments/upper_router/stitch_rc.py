"""Join actual native RC networks with fresh distributed upper R/C.

Native resistor/capacitor records are retained. Only boundary-node identities
change when real nets are joined. No length-based pi capacitance is invented.
The field projection is a research model; its source/target node uncertainty
must also be exercised in timing, separately from the native Liberty limits.
"""
import argparse
from collections import defaultdict
from decimal import Decimal
import json
from pathlib import Path
import re
import struct
from heapq import heappop,heappush
from native_inventory import sha


def farthest_sink(graph,driver,sinks):
    """Largest shortest-path resistance, independent of endpoint name order."""
    adjacency=defaultdict(list)
    for e in graph['resistors']:
        assert e['ohm']>0
        adjacency[e['a']].append((e['b'],e['ohm']));adjacency[e['b']].append((e['a'],e['ohm']))
    root=graph['ports'][driver];distance={root:0.};queue=[(0.,root)]
    while queue:
        value,node=heappop(queue)
        if value!=distance[node]:continue
        for other,r in adjacency[node]:
            candidate=value+r
            if candidate<distance.get(other,float('inf')):
                distance[other]=candidate;heappush(queue,(candidate,other))
    assert sinks and all(graph['ports'][s] in distance for s in sinks)
    return max((graph['ports'][s] for s in sinks),key=lambda i:(distance[i],i))


def parse(raw):
    if not re.search(r'(?m)^\*C_UNIT\s+1\s+PF$',raw) or not re.search(r'(?m)^\*R_UNIT\s+1\s+OHM$',raw):
        raise ValueError('native SPEF units must be explicit PF/OHM')
    fields=re.split(r'(?m)^\*D_NET\s+',raw);header=fields[0];sections={};ports={}
    for body in fields[1:]:
        first,pins=body.split('\n*CONN\n',1);key,total=first.split()
        pins,rest=pins.split('\n*CAP\n',1);caps,res=rest.split('\n*RES\n',1)
        res,tail=res.split('\n*END',1)
        assert not tail.strip() and key not in sections
        sections[key]={'total':Decimal(total),'pins':pins.splitlines(),
                       'caps':[s.split()[1:] for s in caps.splitlines() if s.strip()],
                       'res':[s.split()[1:] for s in res.splitlines() if s.strip()]}
        for line in pins.splitlines():
            f=line.split()
            if f and f[0]=='*P':
                literal=f[1];name=re.sub(r'\\(.)',r'\1',literal)
                assert name not in ports
                ports[name]={'key':key,'literal':literal,'direction':f[2]}
    return header,sections,ports


def field_capacitance(binding,scene,rows,graph):
    names=scene['names'];upper=set(binding['nets']);byname={r['net']:r for r in rows}
    assert set(byname)==upper
    local=defaultdict(float);local_sigma=defaultdict(float);directional=defaultdict(list)
    for name,row in byname.items():
        expected=len(graph['nets'][binding['nets'][name]['logical_net']]['nodes'])
        assert len(row['node_self'])==expected
        for target,origin,capture,value,sigma in row['bins']:
            assert 0<=origin<expected and sigma>=0
            assert value<=5*sigma+1e-4*row['total_ff'],'positive off-diagonal charge outside numerical uncertainty'
            cap=max(0.,-value)
            if target<len(names) and names[target] in upper:
                directional[(name,names[target])].append((origin,capture,cap,sigma))
            else:
                signal=target<len(names) and target not in scene['grounded_indices']
                local[(name,origin,signal)]+=cap;local_sigma[(name,origin,signal)]+=sigma
    coupling=[]
    pairs={tuple(sorted((a,b))) for a,b in directional if a!=b}
    for a,b in sorted(pairs):
        forward=directional[(a,b)];reverse=directional.get((b,a),[])
        # Upper-origin charges can end on the other net's *native* metal.
        # Averaging the two directional upper-only rows therefore changes the
        # measured driver load. Keep the reciprocal common part as explicit
        # coupling and retain each directional residual as signal-ground C.
        # Quiet load is conserved per node. Both terms receive the same Miller
        # factor in the 0/1/2 timing envelope, including native aggressors.
        qa=defaultdict(float);qb=defaultdict(float)
        for i,j,c,s in forward:qa[i,j]+=c
        for j,i,c,s in reverse:qb[i,j]+=c
        for i,j in sorted(set(qa)|set(qb)):
            common=min(qa[i,j],qb[i,j])
            if common>0:coupling.append({'a':[a,i],'b':[b,j],'ff':common})
            local[a,i,True]+=qa[i,j]-common
            local[b,j,True]+=qb[i,j]-common
    diagnostics=[]
    for name,row in byname.items():
        projected=sum(c for (n,i,signal),c in local.items() if n==name)+sum(c['ff'] for c in coupling if name in (c['a'][0],c['b'][0]))
        original=sum(v[0] for v in row['node_self']);bound=sum(v[1] for v in row['node_self'])
        diagnostics.append({'net':name,'field_upper_ff':original,'projected_ff':projected,
                            'field_sigma_bound_ff':bound,'projection_delta_ff':projected-original})
        assert original>0 and projected>0
        assert abs(projected-original)<=5*bound+.03*original,'node projection changes load beyond its numerical/model gate'
    return {'ground':[{'net':n,'node':i,'ff':c,'miller':signal} for (n,i,signal),c in sorted(local.items()) if c>0],
            'coupling':coupling,'projection_diagnostics':diagnostics,
            'projection':'reciprocal common C plus directional native residual; preserves quiet field load; all signal terms swept with Miller 0/1/2',
            'scope':'upper-origin field charge in full native context; native internal RC remains its accepted extracted view'}


def stitch(raw,binding,graph,caps,*,coupling_scale=1,node_projection='distributed'):
    header,sections,ports=parse(raw)
    aliases={};members={};canonical={};upper_nodes={};graph_names={}
    for name,net in binding['nets'].items():
        ends=[net['driver']]+net['sinks'];keys=[]
        for i,p in enumerate(ends):
            assert p in ports and ports[p]['direction']==('O' if i==0 else 'I'),('native port mismatch',p)
            key=ports[p]['key'];assert key not in canonical,'shared native component needs explicit fanout canonicalization'
            if key not in keys:keys.append(key)
        root=keys[0];members[root]=keys
        for key in keys:canonical[key]=root
        g=graph['nets'][net['logical_net']];graph_names[name]=g
        maximum=max([int(tok.split(':')[1]) for key in keys for tag in ('caps','res')
                     for row in sections[key][tag] for tok in row[:-1]
                     if re.fullmatch(re.escape(key)+r':\d+',tok)]+[0])+1
        for i,key in enumerate(keys):
            sections[key]['node_offset']=i*maximum
        base=(len(keys)+1)*maximum
        for node in g['nodes']:upper_nodes[(name,node['id'])]=root+':'+str(base+node['id'])
        for p in ends:aliases[ports[p]['literal']]=upper_nodes[(name,g['ports'][p])]
    def node(token):
        if token in aliases:return aliases[token]
        key,sep,suffix=token.partition(':')
        if sep and key in canonical and suffix.isdigit():
            return canonical[key]+':'+str(int(suffix)+sections[key]['node_offset'])
        return token
    for section in sections.values():
        section['caps']=[[*(node(t) for t in row[:-1]),row[-1]] for row in section['caps']]
        section['res']=[[*(node(t) for t in row[:-1]),row[-1]] for row in section['res']]
        section['pins']=[p for p in section['pins'] if not(p.startswith('*P ') and p.split()[1] in aliases)]
    for root,keys in members.items():
        for key in keys[1:]:
            other=sections.pop(key)
            for field in ('pins','caps','res'):sections[root][field]+=other[field]
            sections[root]['total']+=other['total']
    # Remove only joined native boundary ports from the SPEF port declaration.
    before,marker,port_header=header.partition('*PORTS\n')
    if marker:header=before+marker+''.join(s for s in port_header.splitlines(keepends=True) if not(s.split() and s.split()[0] in aliases))
    far_nodes={name:farthest_sink(g,binding['nets'][name]['driver'],binding['nets'][name]['sinks'])
               for name,g in graph_names.items()} if node_projection=='farthest_sink' else {}
    def project(name,index):
        g=graph_names[name]
        if node_projection=='driver':index=g['ports'][binding['nets'][name]['driver']]
        elif node_projection=='farthest_sink':index=far_nodes[name]
        else:assert node_projection=='distributed'
        return upper_nodes[(name,index)]
    for name,g in graph_names.items():
        root=canonical[ports[binding['nets'][name]['driver']]['key']]
        for e in g['resistors']:
            sections[root]['res'].append([upper_nodes[name,e['a']],upper_nodes[name,e['b']],str(e['ohm'])])
    for c in caps['ground']:
        name=c['net'];root=canonical[ports[binding['nets'][name]['driver']]['key']]
        value=Decimal(str(c['ff']))*Decimal(str(coupling_scale if c.get('miller') else 1))/1000
        sections[root]['caps'].append([project(name,c['node']),str(value)]);sections[root]['total']+=value
    for c in caps['coupling']:
        a,ia=c['a'];b,ib=c['b'];value=Decimal(str(c['ff']))*Decimal(str(coupling_scale))/1000
        ar=canonical[ports[binding['nets'][a]['driver']]['key']];br=canonical[ports[binding['nets'][b]['driver']]['key']]
        sections[ar]['caps'].append([project(a,ia),project(b,ib),str(value)])
        sections[ar]['total']+=value;sections[br]['total']+=value
    output=[header]
    for key,s in sections.items():
        output.append('*D_NET '+key+' '+str(s['total'])+'\n*CONN\n'+'\n'.join(s['pins'])+'\n*CAP\n')
        for i,row in enumerate(s['caps'],1):output.append(str(i)+' '+' '.join(row)+'\n')
        output.append('*RES\n')
        for i,row in enumerate(s['res'],1):output.append(str(i)+' '+' '.join(row)+'\n')
        output.append('*END\n\n')
    return ''.join(output)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('native_spef','binding','graph','scene','rows','output'):p.add_argument(n,type=Path)
    p.add_argument('--coupling-scale',type=float,default=1)
    p.add_argument('--node-projection',choices=['distributed','driver','farthest_sink'],default='distributed')
    a=p.parse_args();read=lambda p:json.loads(p.read_text())
    binding,graph=read(a.binding),read(a.graph);scene=read(a.scene)
    receipt=read(a.rows.with_name('solve.json'))
    assert receipt['passed'] and receipt['rows_sha256']==sha(a.rows)
    assert receipt['scene_sha256']==scene['scene_sha256']==sha(a.scene.with_name('scene.bin'))
    assert scene['graph_sha256']==sha(a.graph)
    assert graph['spec_sha256']==binding['spec_sha256'] and graph['routes_sha256']==binding['route_sha256']
    # Read grounded roles from the physical binary header, including old
    # prepared scenes whose JSON did not yet duplicate these role fields.
    grounded=[]
    with a.scene.with_name('scene.bin').open('rb') as f:
        magic,count,boxes,eps,native_bin=struct.unpack('<8sIQdI',f.read(32));assert magic==b'UPPERR23'
        for i in range(count):
            size=struct.unpack('<I',f.read(4))[0];assert f.read(size).decode()==scene['names'][i]
            is_ground,nodes=struct.unpack('<BI',f.read(5));f.read(nodes*24)
            if is_ground:grounded.append(i)
    scene['grounded_indices']=grounded
    caps=field_capacitance(binding,scene,[json.loads(s) for s in a.rows.read_text().splitlines()],graph)
    out=stitch(a.native_spef.read_text(),binding,graph,caps,coupling_scale=a.coupling_scale,node_projection=a.node_projection)
    with a.output.open('x') as f:f.write(out)
    a.output.with_suffix('.projection.json').write_text(json.dumps(caps,indent=2)+'\n')
