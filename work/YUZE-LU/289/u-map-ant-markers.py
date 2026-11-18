"""Read-only DEF/tech-via rectangle ownership for actual parent DRC markers."""
from pathlib import Path
import json,re,collections,hashlib
root=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117')
out=root/'u-physical'
loc=root/'u-physical/ant-spacing-localization.json'
import xml.etree.ElementTree as E
ms=[]
for item in E.parse(root/'audit/U-antenna/candidate-guard-ant-v1/upper-diagnostic.lyrdb').findall('.//items/item'):
    if item.findtext('cell')!='u_n32_controlled_dma_64':continue
    g=item.findtext('./values/value');v=list(map(float,re.findall(r'-?\d+(?:\.\d+)?',g)))
    ms.append(dict(category=item.findtext('category'),report_cell=item.findtext('cell'),bbox=[min(v[::2]),min(v[1::2]),max(v[::2]),max(v[1::2])],geometry=g))
loc.write_text(json.dumps({'markers':ms},indent=2))
markers=[]
for i,m in enumerate(json.loads(loc.read_text())['markers']):
    if 'ANTENNA' in m['category'] or m['report_cell']!='u_n32_controlled_dma_64':continue
    assert m['report_cell']=='u_n32_controlled_dma_64'
    layer=m['category'].strip("'").split('.')[0].lower()
    if layer=='via6':layer='via7' # The original deck mislabeled via7 spacing.
    markers.append(dict(id=i,layer=layer,box=[round(x*2000) for x in m['bbox']],geometry=m['geometry'],hits=[]))
assert len(markers)==7,len(markers)
grid=collections.defaultdict(set);pitch=20000
for i,m in enumerate(markers):
    x0,y0,x1,y1=m['box']
    for x in range((x0-2)//pitch,(x1+2)//pitch+1):
        for y in range((y0-2)//pitch,(y1+2)//pitch+1):grid[m['layer'],x,y].add(i)
def add(net,layer,box,kind):
    if layer not in {'metal9','metal10','via7','via9'}:return
    ids=set();x0,y0,x1,y1=box
    for x in range(x0//pitch,x1//pitch+1):
        for y in range(y0//pitch,y1//pitch+1):ids.update(grid.get((layer,x,y),()))
    for i in ids:
        a,b,c,d=markers[i]['box']
        if x0<=c+2 and x1>=a-2 and y0<=d+2 and y1>=b-2:
            hit=dict(net=net,kind=kind,layer=layer,box=box)
            if hit not in markers[i]['hits']:markers[i]['hits'].append(hit)
width={n:int(w) for n,w in (x.split('\t') for x in (out/'layers.tsv').read_text().splitlines())}
vias=collections.defaultdict(list)
for line in (out/'vias.tsv').read_text().splitlines():
    name,layer,*box=line.split('\t');vias[name].append((layer,list(map(int,box))))
for line in (out/'bpins.tsv').read_text().splitlines():
    port,net,layer,*box=line.split('\t');add(net,layer,list(map(int,box)),'BPin:'+port)
for line in (out/'pg.tsv').read_text().splitlines():
    net,kind,layer,*box=line.split('\t');add(net,layer,list(map(int,box)),kind)
path=root/'audit/U-antenna/candidate-guard-ant-v1/flow/results/nangate45/u-overlay-current/base/6_final.def'
s=path.read_text();s=s.split('\nNETS ',1)[1].split('\nEND NETS',1)[0]
entries=re.finditer(r'^\s*-\s+(\S+)\s+(.*?);\s*$',s,re.M|re.S)
unknown=set();routes=0
for entry in entries:
    net,body=entry.groups()
    if not any(k in body for k in ('metal7','metal8','metal9','metal10','via7','via9')):continue
    for route in re.finditer(r'(?:\+ ROUTED|\bNEW)\s+(\S+)\s+(.*?)(?=\bNEW|$)',body,re.S):
        layer,seq=route.groups();previous=None
        for token in re.finditer(r'\(\s*([*+-]?\d*|\*)\s+([*+-]?\d*|\*)(?:\s+(-?\d+))?\s*\)|(\S+)',seq):
            x,y,extension,name=token.groups()
            if x is not None:
                assert x and y,(net,seq)
                point=(previous[0] if x=='*' else int(x),previous[1] if y=='*' else int(y))
                if previous:
                    assert point[0]==previous[0] or point[1]==previous[1],(net,point,previous)
                    half=width[layer]//2
                    box=[min(point[0],previous[0])-half,min(point[1],previous[1])-half,max(point[0],previous[0])+half,max(point[1],previous[1])+half]
                    add(net,layer,box,'wire');routes+=1
                previous=point
            elif name in vias:
                assert previous
                for vl,box in vias[name]:add(net,vl,[v+previous[i%2] for i,v in enumerate(box)],'via:'+name)
            elif name not in {'+','USE','SIGNAL','CLOCK'} and not name.isdigit():
                unknown.add(name)
assert not unknown,sorted(unknown)
r=dict(scope='DEF route/BPin and actual technology-via rectangle overlap; not proof of shorts or antenna repair',def_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),markers=markers,scanned_segments=routes)
(out/'ant-marker-nets.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps({'markers':len(markers),'mapped':sum(bool(x['hits']) for x in markers),'nets':sorted({h['net'] for m in markers for h in m['hits']})},indent=2))
