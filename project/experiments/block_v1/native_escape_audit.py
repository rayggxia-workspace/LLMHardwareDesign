"""Actual rectangle connectivity/short checks for bounded native escape edits."""
import collections
import hashlib
import math
import re
from native_escape import records,parse,signature


def geometry(path):
    bynet=collections.defaultdict(list)
    for line in path.read_text().splitlines():
        net,layer,kind,*coords=line.split('\t');coords=tuple(map(int,coords))
        assert len(coords)==4 and coords[0]<coords[2]and coords[1]<coords[3]
        assert re.fullmatch(r'(metal(?:[1-9]|10)|via[1-9])',layer)
        bynet[bytes.fromhex(net).decode()].append((layer,kind,coords))
    return bynet


def connected_layers(a,b):
    if a==b:return True
    return any((a=='via'+str(i)and b in ('metal'+str(i),'metal'+str(i+1)))or
               (b=='via'+str(i)and a in ('metal'+str(i),'metal'+str(i+1)))for i in range(1,10))


def overlap(a,b):return min(a[2],b[2])>max(a[0],b[0])and min(a[3],b[3])>max(a[1],b[1])


def touching(a,b):return min(a[2],b[2])>=max(a[0],b[0])and min(a[3],b[3])>=max(a[1],b[1])


def connectivity(rows):
    parent=list(range(len(rows)))
    def find(i):
        while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
        return i
    def join(i,j):parent[find(i)]=find(j)
    terms=collections.defaultdict(list)
    for i,(layer,kind,box)in enumerate(rows):
        if kind.startswith(('I-','P-')):terms[kind].append(i)
        for j,(other,other_kind,other_box)in enumerate(rows[:i]):
            if connected_layers(layer,other)and overlap(box,other_box):join(i,j)
    # Shapes of one actual library terminal represent one electrode. This
    # does not bridge distinct pins, cells or nets and does not replace LVS.
    for indices in terms.values():
        for j in indices[1:]:join(indices[0],j)
    wires=[i for i,r in enumerate(rows)if r[1].startswith('wire')]
    assert wires and terms
    roots={find(i)for i in wires}
    missing=[name for name,indices in terms.items()if not any(find(i)in roots for i in indices)]
    return dict(passed=len(roots)==1 and not missing,wire_components=len(roots),terminal_count=len(terms),
                port_count=sum(k.startswith('P-')for k in terms),unconnected_terminals=missing)


def physical(by_net,names):
    nets={name:connectivity(by_net[name])for name in names}
    shorts=[];spacing=[]
    for name in names:
        selected=[r for r in by_net[name]if r[0]in ('metal9','metal10','via9')]
        # All other wire/PG/port/master conductors on these layers were
        # scanned. A geometry merge cannot hide an inter-net short here.
        for other,rows in by_net.items():
            if other==name:continue
            for layer,kind,box in rows:
                if layer not in ('metal9','metal10','via9'):continue
                for own,own_kind,a in selected:
                    if connected_layers(own,layer)and touching(a,box):
                        shorts.append(dict(net=name,other=other,layer=own,other_layer=layer,box=a,other_box=box))
                    if own==layer and own in ('metal9','metal10'):
                        dx=max(0,a[0]-box[2],box[0]-a[2]);dy=max(0,a[1]-box[3],box[1]-a[3])
                        distance=math.hypot(dx,dy)
                        if 0<distance<1600-1e-8:spacing.append(dict(net=name,other=other,layer=own,distance_dbu=distance))
    return dict(passed=all(v['passed']for v in nets.values())and not shorts and not spacing,
                nets=nets,cross_net_shorts=shorts,base_spacing_under_800nm=spacing,
                scope='Selected-net actual wire/terminal rectangle connectivity and complete upper-layer cross-net overlap/base spacing; full native deck, manufacturing connectivity and RC/STA remain separate')


def def_inventory(path):
    nets={}
    for text in records(path):
        name=text.lstrip().split()[1];assert name not in nets
        nets[name]=hashlib.sha256(text.encode()).hexdigest()
    outside=hashlib.sha256();inside=False
    with path.open('rb')as stream:
        for line in stream:
            if re.fullmatch(rb'NETS \d+ ;\s*',line.lstrip()):inside=True;outside.update(line);continue
            if line.lstrip().startswith(b'END NETS'):inside=False
            if not inside:outside.update(line)
    assert nets
    return nets,outside.hexdigest()


def header_identity(header):
    # OpenDB reconnects listed existing terminals and can reorder their DEF
    # serialization. Preserve the exact endpoint multiset, net and USE type;
    # no other header grammar or attribute is silently discarded.
    match=re.fullmatch(r'\s*-\s+(\S+)\s+((?:\(\s*\S+\s+\S+\s*\)\s*)+)\+\s+USE\s+(SIGNAL|CLOCK)\s*',header)
    assert match,'Unsupported connection header'
    terms=re.findall(r'\(\s*(\S+)\s+(\S+)\s*\)',match[2])
    assert terms and len(terms)==len(set(terms)),'Duplicate terminal'
    return match[1],sorted(terms),match[3]


def readback(before,after,plans):
    a,ah=def_inventory(before);b,bh=def_inventory(after)
    assert set(a)==set(b)and ah==bh,'Native cells/pins/PG/definitions or net set changed'
    changed={name for name in a if a[name]!=b[name]}
    assert changed==set(plans),'Unexpected route mutation or expected edit missing'
    observed={text.lstrip().split()[1]:text for text in records(after)if text.lstrip().split()[1]in plans}
    for name,text in observed.items():
        header,paths=parse(text);plan=plans[name]
        assert header_identity(header)==header_identity(plan['header']),'Logical connection identity changed'
        assert signature(paths)==signature(plan['final_paths']),'Actual OpenDB route differs from plan'
    return dict(passed=True,total_nets=len(a),changed_nets=sorted(changed),outside_nets_sha256=ah,
                unchanged_net_count=len(a)-len(changed))
