"""Decode actual benchmark DEF geometry into independent solver inputs.

Preserves DEF units, explicit endpoint extensions, and OpenDB NDR widths.
Does not assign guessed capacitances or call a model qualified.
"""
from collections import Counter
import hashlib
import json
from pathlib import Path
import re


def prepare(folder,metadata,out):
    rules=json.loads(metadata.read_text())
    native=(folder/'overlay/research12.tech.lef').read_text()
    layers={}
    for match in re.finditer(r'(?m)^LAYER\s+(metal\d+)\s*\n(.*?)^END\s+\1\s*$',native,re.S|re.M):
        name,body=match.groups()
        def value(pattern):
            found=re.search(pattern+r'\s+([0-9.]+)\s*;',body,re.M)
            assert found,name+' missing '+pattern
            return float(found.group(1))
        layers[name]=dict(width=value(r'^\s*WIDTH'),height=value(r'^\s*HEIGHT'),
                          thickness=value(r'^\s*THICKNESS'),rsheet=value(r'^\s*RESISTANCE RPERSQ'))
    assert set(layers)=={'metal%d'%i for i in range(1,13)}
    groups={};counts=Counter();families=Counter();declared=None;scale=None;name=None;ports=None
    active=False
    with (folder/'patterns.def').open()as stream:
        for line in stream:
            if not active:
                m=re.match(r'UNITS DISTANCE MICRONS (\d+)\s*;',line)
                if m:scale=int(m.group(1))
                m=re.match(r'NETS (\d+)\s*;',line)
                if m:declared=int(m.group(1));active=True
                continue
            if line.startswith('END NETS'):break
            m=re.match(r'\s*- (\S+)\s+\( PIN (\S+) \) \( PIN (\S+) \) \+ USE SIGNAL\s*$',line)
            if m:
                assert name is None,'unfinished net'
                name,first,second=m.groups();ports=[first,second];continue
            if not line.strip():continue
            assert name is not None,'unknown net line '+line
            m=re.fullmatch(r'\s*\+ ROUTED (metal\d+)(?: TAPERRULE (\S+))?\s+\(\s*([0-9*]+)\s+([0-9*]+)(?:\s+(\d+))?\s*\)\s+\(\s*([0-9*]+)\s+([0-9*]+)(?:\s+(\d+))?\s*\)\s*;\s*',line)
            assert m,'unsupported actual benchmark path '+line
            layer,rule,x0,y0,e0,x1,y1,e1=m.groups()
            assert '*'not in (x0,y0)
            x0,y0=int(x0)/scale,int(y0)/scale
            x1=x0 if x1=='*'else int(x1)/scale
            y1=y0 if y1=='*'else int(y1)/scale
            spec=layers[layer]
            width=spec['width']if rule is None else rules['rules'][rule][layer]['width_dbu']/rules['dbu_per_um']
            extension0=width/2 if e0 is None else int(e0)/scale
            extension1=width/2 if e1 is None else int(e1)/scale
            assert width>0 and ((x0==x1) != (y0==y1)),'non-orthogonal or zero benchmark segment'
            if y0==y1:
                assert x1>x0
                box=[x0-extension0,y0-width/2,spec['height'],x1+extension1,y0+width/2,spec['height']+spec['thickness']]
            else:
                assert y1>y0
                box=[x0-width/2,y0-extension0,spec['height'],x0+width/2,y1+extension1,spec['height']+spec['thickness']]
            match=re.fullmatch(r'(.+)_(\d+)',name)
            assert match,'unclassified benchmark group '+name
            group,index=match.groups()
            groups.setdefault(group,[]).append(dict(name=name,index=int(index),layer=layer,ports=ports,box_um=box,
                  resistance_ohm=spec['rsheet']*(abs(x1-x0)+abs(y1-y0))/width,width_um=width,ndr=rule))
            counts[layer]+=1;families[group.split('_',1)[0]]+=1;name=None
    assert name is None and sum(counts.values())==declared,'benchmark inventory incomplete'
    assert set(counts)==set(layers),'benchmark omitted actual routing layers'
    out.mkdir(exist_ok=False)
    cases=[]
    for index,(name,nets)in enumerate(sorted(groups.items())):
        assert len({n['name']for n in nets})==len(nets)
        # Numerical translation only; no stretching, net omission or geometry relabeling.
        ox=min(n['box_um'][0]for n in nets);oy=min(n['box_um'][1]for n in nets)
        scene='background 3.9\n'
        for n in nets:
            x0,y0,z0,x1,y1,z1=n['box_um']
            scene+='box %s %.12g %.12g %.12g %.12g %.12g %.12g\n'%(n['name'],x0-ox,y0-oy,z0,x1-ox,y1-oy,z1)
        path=out/('%06d.txt'%index);path.write_text(scene)
        cases.append(dict(id=index,name=name,nets=nets,scene=str(path),scene_sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    manifest=dict(schema='block-v1-reference-patterns/1',def_sha256=hashlib.sha256((folder/'patterns.def').read_bytes()).hexdigest(),
        source_folder=str(folder),ndr_metadata_sha256=hashlib.sha256(metadata.read_bytes()).hexdigest(),def_units_per_um=scale,
        layers=layers,net_count=declared,groups=len(groups),family_nets=dict(families),layer_nets=dict(counts),
        group_size_histogram=dict(Counter(len(nets)for nets in groups.values())),cases=cases,
        qualification='Geometry only; all actual twelve layers decoded; field solution/model qualification pending')
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({k:v for k,v in manifest.items()if k not in ('cases','layers')},indent=2))

