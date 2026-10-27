"""Exact conductor-union binding, including real wire/via and terminal metal.

Coordinate compression is deliberately bounded to small qualification scenes.
It compares occupied volume, never just bbox, volume totals, or box ordering.
"""
import itertools
import math
import re


def integer(value):
    scaled=value*2000
    assert math.isfinite(scaled) and abs(scaled-round(scaled))<1e-6
    return int(round(scaled))


def compare(actual,expected):
    assert set(actual)==set(expected)
    summary={}
    for net in expected:
        a=[tuple(integer(v)for v in box)for box in actual[net]]
        b=[tuple(integer(v)for v in box)for box in expected[net]]
        assert a and b and all(all(x[k]<x[k+3]for k in range(3))for x in a+b)
        axes=[sorted({box[k]for box in a+b}|{box[k+3]for box in a+b})for k in range(3)]
        count=math.prod(len(axis)-1 for axis in axes);assert count<200000
        occupied=0
        for indices in itertools.product(*(range(len(axis)-1)for axis in axes)):
            point=[(axis[i]+axis[i+1])/2 for axis,i in zip(axes,indices)]
            inside=lambda boxes:any(all(box[k]<point[k]<box[k+3]for k in range(3))for box in boxes)
            observed,wanted=inside(a),inside(b)
            assert observed==wanted,('Conductor union mismatch',net,indices,point,observed,wanted)
            occupied+=wanted
        summary[net]=dict(actual_boxes=len(a),reference_boxes=len(b),compressed_cells=count,occupied_cells=occupied)
    return summary


def parse(text,technology):
    layers={}
    for name,body in re.findall(r'(?ms)^LAYER\s+(metal\d+)\s*\n(.*?)^END\s+\1\s*$',technology):
        value=lambda key:float(re.search(r'(?m)^\s*'+key+r'\s+([\d.]+)\s*;',body).group(1))
        layers[name]=(value('HEIGHT'),value('HEIGHT')+value('THICKNESS'))
    aliases={};boxes={};kinds={}
    assert text.splitlines()[0]=='# block-v1-odb-geometry/1 dbu_per_um=2000'
    for line in text.splitlines():
        if line.startswith('# NET '):
            _,_,alias,encoded=line.split();net=bytes.fromhex(encoded).decode('utf-8')
            assert alias not in aliases and net not in boxes
            aliases[alias]=net;boxes[net]=[];continue
        if line.startswith('#'):continue
        alias,layer,kind,*coordinates=line.split('\t');assert len(coordinates)==4
        net=aliases[alias];xy=[int(v)/2000-32 for v in coordinates]
        if layer in layers:z0,z1=layers[layer]
        else:
            assert re.fullmatch(r'via\d+',layer)
            number=int(layer[3:]);z0=layers['metal%d'%number][1];z1=layers['metal%d'%(number+1)][0]
        assert z1>z0
        boxes[net].append([xy[0],xy[1],z0,xy[2],xy[3],z1])
        kinds[kind]=kinds.get(kind,0)+1
    assert kinds.get('wire',0)>0 and kinds.get('instance-pin',0)>0
    return boxes,kinds


def controls(geometry,boxes):
    import copy
    expected={net:[box for name,box in boxes if name==net]for net in ['target','near']}
    # Positive uses a different rectangular partition of the same solid.
    actual=copy.deepcopy(expected);box=actual['near'].pop();middle=(box[0]+box[3])/2
    left=box[:];right=box[:];left[3]=middle;right[0]=middle
    actual['near'] += [left,right];compare(actual,expected)
    rejected=[]
    for name in ['shift','extra-metal','missing-metal','net-swap']+(['missing-via']if geometry=='via'else[]):
        bad=copy.deepcopy(actual)
        if name=='shift':bad['near'][0][0]+=.001
        elif name=='extra-metal':bad['target'].append([8,8,12.89,9,9,14.89])
        elif name=='missing-metal':bad['target'].pop()
        elif name=='net-swap':bad['target'],bad['near']=bad['near'],bad['target']
        else:bad['target']=[b for b in bad['target']if b[2]!=12.09]
        try:compare(bad,expected)
        except AssertionError:rejected.append(name)
        else:raise AssertionError('Accepted '+name)
    return dict(passed=True,repartitioned_positive=True,rejected=rejected)
