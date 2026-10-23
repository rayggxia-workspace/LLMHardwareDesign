"""Conservative semantic DEF audit: reject any frozen primitive difference."""
import collections
import hashlib
import json
from pathlib import Path
import re

def section(text,name):
    m=re.search(r'^'+name+r' (\d+) ;\n(.*?)^END '+name,text,re.M|re.S)
    assert m,name
    rows=re.findall(r'^\s*- (.*?);',m[2],re.M|re.S)
    assert len(rows)==int(m[1]),name
    return rows

def snapshot(path,bottom):
    text=Path(path).read_text()
    components={}
    for row in section(text,'COMPONENTS'):
        words=row.split()
        components[words[0]]=' '.join(words[1:])
    pg=sorted(' '.join(row.split()) for row in section(text,'SPECIALNETS'))
    pins=sorted(' '.join(row.split()) for row in section(text,'PINS'))
    fixed=collections.Counter()
    custom=collections.Counter()
    connectivity={}
    for row in section(text,'NETS'):
        parts=re.split(r'\+ (?:ROUTED|FIXED) |\n\s*NEW ',row)
        header=parts[0].strip()
        name=header.split()[0]
        connectivity[name]=' '.join(header.split())
        clock='+ USE CLOCK' in header
        for path in parts[1:]:
            layer=re.match(r'metal(\d+)\s',path)
            assert layer,path[:100]
            layer=int(layer[1])
            points=re.findall(r'\(\s*(-?\d+|\*)\s+(-?\d+|\*)(?:\s+(-?\d+))?\s*\)',path)
            rest=re.sub(r'\([^)]*\)','',path).split()
            assert len(rest) in (1,2),rest
            assert points and '*' not in points[0][:2]
            x,y=map(int,points[0][:2]);extension=points[0][2]
            if len(rest)==2:
                via=rest[1]
                m=re.fullmatch(r'via(\d+)(?:_\d+)?',via)
                assert m and len(points)==1,(rest,points)
                upper=int(m[1])+1
                frozen=clock or upper<=bottom
                key=(name,'via',via,x,y)
                (fixed if frozen else custom)[key]+=1
            else:
                for px,py,end in points[1:]:
                    nx=x if px=='*' else int(px);ny=y if py=='*' else int(py)
                    assert x==nx or y==ny
                    endpoints=sorted([(x,y,extension),(nx,ny,end)])
                    key=(name,'wire',layer,*endpoints[0],*endpoints[1])
                    (fixed if clock or layer<bottom else custom)[key]+=1
                    x,y,extension=nx,ny,end
    return dict(components=components,pg=pg,pins=pins,connectivity=connectivity,fixed=fixed,custom=custom)

def audit(before,after,bottom,output,require_custom=False):
    a,b=snapshot(before,bottom),snapshot(after,bottom)
    checks={k:a[k]==b[k] for k in ['components','pg','pins','connectivity','fixed']}
    checks['custom_geometry_present']=bool(b['custom']) if require_custom else True
    missing=list((a['fixed']-b['fixed']).items())
    added=list((b['fixed']-a['fixed']).items())
    result=dict(passed=all(checks.values()),checks=checks,bottom_custom_metal=bottom,
        fixed_primitive_count=sum(a['fixed'].values()),final_custom_primitive_count=sum(b['custom'].values()),
        missing_frozen_count=sum(v for k,v in missing),added_frozen_count=sum(v for k,v in added),
        missing_first20=missing[:20],added_first20=added[:20],
        before_sha256=hashlib.sha256(Path(before).read_bytes()).hexdigest(),
        after_sha256=hashlib.sha256(Path(after).read_bytes()).hexdigest(),
        scope='Exact master/placement/status/connections/PG/pins and conservative ordinary wire/via primitive multiset. Fixed V7 access landings are included. Equivalent resegmentation may be rejected; no geometric change is silently accepted.')
    Path(output).write_text(json.dumps(result,indent=2)+'\n')
    assert result['passed'],'Frozen geometry/resources changed; inspect retained evidence'
    return result
