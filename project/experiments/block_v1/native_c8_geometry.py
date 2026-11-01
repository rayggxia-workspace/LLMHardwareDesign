"""Restricted upper-route rectangles and exact native-source shape accounting.

This is an obstacle preflight, never a replacement for actual ODB readback or
native full-rule DRC. Original rendered rectangles must be found one-for-one
in the actual source, retaining duplicated via8/via9 metal enclosures.
"""
import collections
from native_escape import parse

UPPER=('metal9','metal10','via9')


def render(paths):
    rows=[]
    for path in paths:
        layer=path['layer']
        if layer not in ('metal9','metal10'):continue
        if path['via']:
            assert layer=='metal9'and path['via']=='via9_0','Unsupported upper via definition'
            x,y,extension=path['points'][0];assert extension is None
            for name in UPPER:rows.append((name,'wire-via',(x-800,y-800,x+800,y+800)))
        else:
            (x1,y1,e1),(x2,y2,e2)=path['points']
            assert (x1==x2)!=(y1==y2)
            e1=800 if e1 is None else e1;e2=800 if e2 is None else e2
            assert e1 in (0,800)and e2 in (0,800),'Unsupported explicit extension'
            if x1==x2:
                if y1>y2:y1,y2,e1,e2=y2,y1,e2,e1
                box=(x1-800,y1-e1,x1+800,y2+e2)
            else:
                if x1>x2:x1,x2,e1,e2=x2,x1,e2,e1
                box=(x1-e1,y1-800,x2+e2,y1+800)
            rows.append((layer,'wire',box))
    return rows


def replace(actual,original,proposed):
    before=collections.Counter(actual);remove=collections.Counter(render(parse(original)[1]))
    assert not remove-before,'Restricted renderer disagrees with actual source rectangles'
    after=before-remove;after.update(render(parse(proposed)[1]))
    return list(after.elements())


class Obstacles:
    """Exact bounded queries; indexing changes candidate selection only."""
    def __init__(self,by_net,pitch=6400):
        assert type(pitch)is int and pitch>0
        self.pitch=pitch;self.buckets=collections.defaultdict(set);self.rows={};self.serial=0;self.by_net=collections.defaultdict(list)
        for name,rows in by_net.items():self.add(name,rows)

    def keys(self,layer,box):
        p=self.pitch
        for x in range(box[0]//p,box[2]//p+1):
            for y in range(box[1]//p,box[3]//p+1):yield layer,x,y

    def add(self,name,rows):
        for layer,kind,box in rows:
            if layer not in UPPER:continue
            i=self.serial;self.serial+=1;self.rows[i]=(name,layer,kind,box);self.by_net[name].append(i)
            for key in self.keys(layer,box):self.buckets[key].add(i)

    def remove(self,name):
        for i in self.by_net.pop(name,[]):
            _,layer,kind,box=self.rows.pop(i)
            for key in self.keys(layer,box):
                self.buckets[key].remove(i)
                if not self.buckets[key]:del self.buckets[key]

    def query(self,layer,box,margin=0):
        assert margin>=0
        area=(box[0]-margin,box[1]-margin,box[2]+margin,box[3]+margin);ids=set()
        for key in self.keys(layer,area):ids.update(self.buckets.get(key,()))
        for i in sorted(ids):
            row=self.rows[i];b=row[3]
            if b[0]<=area[2]and b[2]>=area[0]and b[1]<=area[3]and b[3]>=area[1]:yield row

    def violations(self,name,rows):
        violations=[]
        for layer,kind,a in rows:
            if layer not in UPPER:continue
            spacing=1760 if layer=='via9'else 1600
            for other,_,other_kind,b in self.query(layer,a,spacing):
                if other==name:continue
                dx=max(0,a[0]-b[2],b[0]-a[2]);dy=max(0,a[1]-b[3],b[1]-a[3])
                if dx*dx+dy*dy<spacing*spacing:
                    violations.append(dict(net=name,other=other,layer=layer,box=a,other_box=b,distance_squared=dx*dx+dy*dy,required_spacing_dbu=spacing))
        return violations
