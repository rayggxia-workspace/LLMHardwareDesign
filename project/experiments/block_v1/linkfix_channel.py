"""Deterministic two-layer track router; independently received geometry/RC."""
import heapq
import json
from pathlib import Path
from interconnect_spef import sha


class Channels:
    """Preferred H/V trunks with penalised detours; retain all width/cut rules."""
    def __init__(self,nx,ny,endpoints,access=False,access_depth=0,orthogonal=False,seeded=()):
        self.nx,self.ny=nx,ny
        self.used={};self.cuts=set();self.history=[];self.access={};self.stems={};self.prefixes={};self.orthogonal=orthogonal
        for owner,points in endpoints.items():
            for x,y in points:
                assert (0,x,y)not in self.used,'Conflicting native terminals'
                self.used[0,x,y]=owner
        row_counts={}
        for points in endpoints.values():
            for x,y in points:row_counts[y]=row_counts.get(y,0)+1
        dense_rows=sorted(y for y,n in row_counts.items()if n>=8)
        row_directions={y:(-1 if i%2==0 else 1)for i,y in enumerate(dense_rows)}
        if access and orthogonal:
            for owner,points in endpoints.items():
                if owner in seeded:continue
                prefixes=[]
                for i,(x,y)in enumerate(points):
                    if y in row_directions:
                        d=row_directions[y];prefix=[(0,x,y+d*k)for k in range(3)]
                    else:
                        dx=1 if points[1-i][0]>=x else -1;chosen=None
                        for direction in (dx,-dx):
                            xx=x+direction
                            trial=[(0,x,y),(0,xx,y)]+[(1,xx+direction*k,y)for k in range(3)]
                            if all(self.used.get(node,owner)==owner for node in trial):chosen=trial;break
                        assert chosen is not None,('Orthogonal pad access conflict',owner,i)
                        prefix=chosen;cut=prefix[2][1:]
                        assert not any((cut[0]+a,cut[1]+b)in self.cuts for a,b in ((0,0),(-1,0),(1,0),(0,-1),(0,1)))
                        self.cuts.add(cut)
                    for node in prefix:
                        assert self.used.get(node,owner)==owner,('Orthogonal stem conflict',owner,node)
                        self.used[node]=owner
                    prefixes.append(prefix)
                self.prefixes[owner]=prefixes;self.access[owner]=points
            return
        if access:
            # Reserve each terminal's escape before routing any net. Otherwise
            # earlier short paths can surround an unrouted pad on both layers.
            # Alternate the4um horizontal escape every8um terminal row, so
            # dense vertical pin columns retain room for an8um via-to-via run.
            for owner,points in endpoints.items():
                escapes=[]
                for x,y in points:
                    xx=x+row_directions.get(y,1 if (y//2)%2==0 else -1)
                    for node in ((0,xx,y),(1,xx,y)):
                        assert self.used.get(node,owner)==owner,('Terminal escape conflict',owner,node)
                        self.used[node]=owner
                    assert not any((xx+dx,y+dy)in self.cuts for dx,dy in ((0,0),(-1,0),(1,0),(0,-1),(0,1))),('Terminal cut spacing',owner)
                    self.cuts.add((xx,y));escapes.append((xx,y))
                self.access[owner]=escapes
            if access_depth:
                assert access_depth==2
                for owner,points in endpoints.items():
                    stems=[]
                    for i,(x,y)in enumerate(self.access[owner]):
                        target_y=points[1-i][1];direction=1 if target_y>=y else -1
                        options=[direction,-direction]
                        chosen=None
                        for d in options:
                            nodes=[(1,x,y+d*k)for k in range(access_depth+1)]
                            if all(1<=xx<nx-1 and 1<=yy<ny-1 and self.used.get((l,xx,yy),owner)==owner for l,xx,yy in nodes):
                                chosen=nodes;break
                        assert chosen is not None,('Reserved terminal stem conflict',owner,i)
                        for node in chosen:self.used[node]=owner
                        stems.append(chosen)
                    self.stems[owner]=stems

    def seed_aligned(self,owner,start,end,offset):
        """Paired aligned horizontal pin rows use separate straight M12 tracks."""
        assert start[0]==end[0] and offset in (-1,0) and end[1]>start[1]
        x=start[0]+offset
        path=[(0,*start)]
        if offset:path.append((0,x,start[1]))
        path.append((1,x,start[1]))
        path += [(1,x,y)for y in range(start[1]+1,end[1]+1)]
        path.append((0,x,end[1]))
        if offset:path.append((0,*end))
        cuts=[(x,start[1]),(x,end[1])]
        for cut in cuts:
            assert not any((cut[0]+a,cut[1]+b)in self.cuts for a,b in ((0,0),(-1,0),(1,0),(0,-1),(0,1)))
        assert abs(cuts[0][1]-cuts[1][1])>=2
        for node in path:assert self.used.get(node,owner)==owner,('Seed conflicts with reserved native access',owner,node)
        self.cuts.update(cuts)
        for node in path:self.used[node]=owner
        self.history.append(dict(net=owner,expanded=0,steps=len(path),vias=2,aligned_channel=True))
        return path

    def route(self,owner,start,end,forbidden=None,attempt=0):
        # Track occupancy includes endpoints of every unrouted net, so a wire
        # cannot later be shorted by installing that other net's via10.
        forbidden=set()if forbidden is None else forbidden
        assert attempt<64,('Finite same-net cut repair exhausted',owner)
        original_start,original_end=start,end
        if owner in self.access:start,end=self.access[owner]
        if owner in self.stems:start,end=[p[-1][1:]for p in self.stems[owner]]
        target_layer=1 if owner in self.access else 0
        start_layer=target_layer
        if owner in self.prefixes:
            a,b=self.prefixes[owner];start_layer,*start=a[-1];target_layer,*end=b[-1]
        initial=(start_layer,*start,0 if owner in self.access and owner not in self.stems and owner not in self.prefixes else 2);heap=[(0,0,initial)];best={initial:0};parent={}
        target=None;expanded=0
        while heap:
            _,cost,state=heapq.heappop(heap)
            if best.get(state)!=cost:continue
            layer,x,y,run=state;expanded+=1
            if (layer,x,y)==(target_layer,*end):target=state;break
            assert expanded<3000000,('Finite channel search exhausted',owner)
            horizontal=(layer==1)if self.orthogonal else(layer==0)
            moves=[(layer,x+dx,y+dy,min(2,run+1),1)for dx,dy in (((-1,0),(1,0))if horizontal else((0,-1),(0,1)))]
            # Direction is preferred, not a metal-geometry prohibition.
            # Penalised wrong-way detours avoid closed walls of existing
            # wires/pad vias. Width/space/cut rules remain unchanged and are
            # independently checked on the resulting actual rectangles.
            if owner in self.access:
                moves += [(layer,x+dx,y+dy,min(2,run+1),10)for dx,dy in (((0,-1),(0,1))if horizontal else((-1,0),(1,0)))]
            # Same-cut-layer centres four microns apart on one axis violate
            # 2um cut +2.2um gap. Eight microns between successive vias avoids
            # that conflict; diagonal4/4 remains legal. Restrict additional
            # cuts to one8um lattice as well: every pair of new cuts then
            # meets spacing by construction, including nonconsecutive cuts.
            # All reserved native-access cuts still participate in checks.
            if run>=2 and (owner not in self.access or ((x+y)%2==0 if self.orthogonal else(x%2==1 and y%2==0))) and (x,y)not in forbidden and not any((x+dx,y+dy)in self.cuts for dx,dy in ((0,0),(-1,0),(1,0),(0,-1),(0,1))):
                moves.append((1-layer,x,y,0,3))
            for other,xx,yy,rr,step in moves:
                if not(1<=xx<self.nx-1 and 1<=yy<self.ny-1):continue
                occupied=self.used.get((other,xx,yy))
                if occupied is not None and occupied!=owner:continue
                nxt=(other,xx,yy,rr);g=cost+step
                if g>=best.get(nxt,10**12):continue
                best[nxt]=g;parent[nxt]=state
                h=abs(xx-end[0])+abs(yy-end[1])
                heapq.heappush(heap,(g+h,g,nxt))
        assert target is not None,('No complete route',owner)
        path=[target]
        while path[-1]!=initial:path.append(parent[path[-1]])
        path.reverse();points=[p[:3]for p in path]
        if owner in self.prefixes:
            a,b=self.prefixes[owner];points=a[:-1]+points+list(reversed(b[:-1]))
        elif owner in self.access:
            if owner in self.stems:
                sa,se=self.access[owner];a,b=self.stems[owner]
                points=[(0,*original_start),(0,*sa)]+a[:-1]+points+list(reversed(b[:-1]))+[(0,*se),(0,*original_end)]
            else:points=[(0,*original_start),(0,*start)]+points+[(0,*end),(0,*original_end)]
        cuts=[a[1:]for a,b in zip(points,points[1:])if a[0]!=b[0]]
        assert len(cuts)==len(set(cuts))
        for i,(x,y)in enumerate(cuts):
            for xx,yy in cuts[:i]:
                if abs(x-xx)+abs(y-yy)<=1:
                    victim=(x,y)if(x,y)not in self.cuts else(xx,yy)
                    assert victim not in self.cuts,'Reserved terminal cuts conflict'
                    return self.route(owner,original_start,original_end,forbidden|{victim},attempt+1)
        self.cuts.update(cuts)
        for point in points:
            assert self.used.get(point,owner)==owner
            self.used[point]=owner
        self.history.append(dict(net=owner,expanded=expanded,steps=len(points),vias=len(cuts)))
        return points


def route(root,out,cpus,run,key):
    from linkclose_route import definitions
    from overlay import generate
    assert cpus==16 and key in ('mf3','tf3','tf5','tf6','tf7','tf8','tf9')
    pair='mt'if key.startswith('m')else'ts'
    native,lefs,pins,size,placements,links=definitions(root,out.parents[2],pair)
    if pair=='mt':
        placements=dict(t=[200,200],bridge=[320,1260],m=[320,1440],booster=[1260,400],**{'return':[1260,1100]})
    else:
        placements['return']=[116,1160]
    for i,(a,p)in enumerate(placements.items()):
        for b,q in list(placements.items())[:i]:
            assert p[0]+size[a][0]<=q[0]or q[0]+size[b][0]<=p[0]or p[1]+size[a][1]<=q[1]or q[1]+size[b][1]<=p[1]
    upper=[max(p[i]+size[k][i]for k,p in placements.items())+200 for i in (0,1)]
    endpoints={}
    def track(xy):
        dbu=[round(v*2000)for v in xy];p=[round((dbu[i]-[190,140][i])/8000)for i in (0,1)]
        assert dbu==[8000*p[0]+190,8000*p[1]+140],('Off-track native pin',xy)
        return tuple(p)
    def point(p):return '( %d %d )'%(p[0]*8000+190,p[1]*8000+140)
    for l in links:
        for term,field in [('source','source_xy_um'),('sink','sink_xy_um')]:
            a,p=l[term];l[field]=[pins[a][p][i]+placements[a][i]for i in (0,1)]
        l['manhattan_lower_um']=sum(abs(l['source_xy_um'][i]-l['sink_xy_um'][i])for i in(0,1))
        endpoints[l['id']]=[track(l['source_xy_um']),track(l['sink_xy_um'])]
    def encode(path):
        start=path[0][1:];text='metal10 '+point(start)+' BV1_via10 NEW metal11 '+point(start)
        for i,(a,b)in enumerate(zip(path,path[1:])):
            if a[0]!=b[0]:text+=' BV1_via11 NEW metal%d '%(11+b[0])+point(b[1:])
            elif i==len(path)-2 or path[i+2][0]!=b[0] or (b[1]-a[1],b[2]-a[2])!=(path[i+2][1]-b[1],path[i+2][2]-b[2]):text+=' '+point(b[1:])
        return text+' NEW metal10 '+point(path[-1][1:])+' BV1_via10'
    aligned=[l for l in links if l['source'][0]=='t'and l['sink'][0]=='bank']if key=='tf9'else[]
    if aligned:assert len(aligned)==139 and all(endpoints[l['id']][0][0]==endpoints[l['id']][1][0]for l in aligned)
    seeded={l['id']for l in aligned}
    order=sorted([l for l in links if l['id']not in seeded],key=lambda l:int(l['id'][1:])%2==0)if key in ('tf6','tf8','tf9')else sorted(links,key=lambda l:-l['manhattan_lower_um'])
    attempts=[]
    for trial in range(16):
        channel=Channels(int(upper[0]/4),int(upper[1]/4),endpoints,access=True,access_depth=2,orthogonal=key in ('tf7','tf8','tf9'),seeded=seeded);routed={};failed=None
        for l in aligned:
            a,b=endpoints[l['id']];offset=-1 if a[1]==min(endpoints[z['id']][0][1]for z in aligned)else 0
            routed[l['id']]=encode(channel.seed_aligned(l['id'],a,b,offset))
        for count,l in enumerate(order):
            try:path=channel.route(l['id'],*endpoints[l['id']])
            except AssertionError as error:
                failed=l;attempts.append(dict(trial=trial,completed=count,failed=l['id'],error=str(error)))
                (out/'channel-attempts.json').write_text(json.dumps(attempts,indent=2)+'\n');break
            routed[l['id']]=encode(path)
            (out/'channel-progress.json').write_text(json.dumps(dict(trial=trial,completed=len(routed),total=len(links),last=channel.history[-1]))+'\n')
        if failed is None:break
        order=[failed]+[l for l in order if l is not failed]
    assert len(routed)==len(links),('Full bus routing exhausted',attempts)
    (out/'channel-attempts.json').write_text(json.dumps(attempts,indent=2)+'\n')
    spec=json.loads((root/'project/experiments/block_v1/technology-2um-v1.json').read_text())
    generate(Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/lef/NangateOpenCellLibrary.tech.lef'),spec,out/'technology')
    text='VERSION 5.8 ;\nDIVIDERCHAR "/" ;\nBUSBITCHARS "[]" ;\nDESIGN channel_'+key+' ;\nUNITS DISTANCE MICRONS 2000 ;\nDIEAREA ( 0 0 ) ( %d %d ) ;\n'%tuple(round(v*2000)for v in upper)
    text+='COMPONENTS %d ;\n'%len(native)
    for k,row in native.items():text+='- u_'+k+' '+row['top']+' + FIXED ( %d %d ) N ;\n'%tuple(round(v*2000)for v in placements[k])
    text+='END COMPONENTS\nNETS %d ;\n'%len(links)
    for l in links:
        terms=[l['source'],l['sink']]
        text+='- '+l['id']+' '+' '.join('( u_'+a+' '+p+' )'for a,p in terms)+' + USE SIGNAL + ROUTED '+routed[l['id']]+' ;\n'
    text+='END NETS\nEND DESIGN\n';(out/'input.def').write_text(text)
    request=dict(native=native,lefs={k:dict(path=str(v),sha256=sha(v))for k,v in lefs.items()},pins=pins,size=size,placements=placements,links=links,die_um=upper,representative_subset=False,original_full_bus_links=len(links))
    (out/'route-inputs.json').write_text(json.dumps(request,indent=2)+'\n')
    (out/'channel-search.json').write_text(json.dumps(channel.history,indent=2)+'\n')
    script='set_thread_count 16\nread_lef {'+str(out/'technology/research12.tech.lef')+'}\n'
    for i,lef in enumerate(dict.fromkeys(lefs.values())):
        p=out/('macro-%d.lef'%i);p.write_bytes(lef.read_bytes());assert sha(p)==sha(lef)
        script+='read_lef {'+str(p)+'}\n'
    script+='read_def {'+str(out/'input.def')+'}\nwrite_db routed.odb\nwrite_def routed.def\nsource {'+str(root/'project/experiments/block_v1/odb_geometry.tcl')+'}\nbvgeom::export geometry.tsv\n'
    (out/'route.tcl').write_text(script);run(['openroad','-no_init','-exit',out/'route.tcl'],'route.log')
    (out/'linkclose-route.json').write_text(json.dumps(dict(passed=True,pair=key,links=len(links),inputs_sha256=sha(out/'route-inputs.json'),odb_sha256=sha(out/'routed.odb'),def_sha256=sha(out/'routed.def'),geometry_sha256=sha(out/'geometry.tsv'),scope='Explicit full-bus track/channel routes, native pads unchanged, actual wire/via ODB. Independent KLayout checks and native-circuit RC/STA remain required; no automatic-router or manufacturing claim.'),indent=2)+'\n')


def geometry(root,out,cpus,run,key):
    from linkclose_measure import bound
    routed=out.parent/('linkclose-route-'+key)
    if key=='mf1':routed=out.parents[2]/'block-v1-20261029-925/tasks/linkclose-route-mf1'
    report,r=bound(routed,'linkclose-route.json')
    for name in ('route-inputs.json','geometry.tsv','routed.def','routed.odb'):
        assert sha(routed/name)==r['outputs'][name]
    run(['klayout','-b','-r',root/'project/experiments/block_v1/linkclose_geometry.rb',
        '-rd','request='+str(routed/'route-inputs.json'),'-rd','geometry='+str(routed/'geometry.tsv'),
        '-rd','spec='+str(root/'project/experiments/block_v1/technology-2um-v1.json'),'-rd','report='+str(out/'geometry.json')],'geometry.log')
    checked=json.loads((out/'geometry.json').read_text());assert checked['passed']
    assert checked['links']==report['links']==(275 if key.startswith('m')else 281)
    (out/'linkfix-geometry.json').write_text(json.dumps(dict(passed=True,source=str(routed),source_receipt_sha256=sha(routed/'receipt.json'),geometry=checked),indent=2)+'\n')
