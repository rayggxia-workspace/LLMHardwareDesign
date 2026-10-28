"""Finite 16-bit full-strip and turning fixtures for the 2um demo rules.

Integer DBU geometry, explicit independent net identities and graph checks.
An independent KLayout process writes/reads real GDS and checks its regions.
This is P1 only, never a complete macro escape or native-leaf acceptance.
"""
import copy
import json
import math
from pathlib import Path

DBU=2000
LAYERS={'metal10':(29,0),'via10':(210,0),'metal11':(211,0),'via11':(212,0),'metal12':(213,0)}


def u(value):
    from decimal import Decimal
    v=Decimal(str(value))*DBU
    assert v==v.to_integral_value()
    return int(v)


def box(x,y,w=2):return [x-u(w)/2,y-u(w)/2,x+u(w)/2,y+u(w)/2]


def fixture(kind):
    assert kind in ('horizontal16','vertical16','turn-reverse16')
    shapes=[];ports=[]
    def add(layer,rectangle,net):
        assert all(float(v).is_integer()for v in rectangle)
        shapes.append(dict(layer=layer,box_dbu=list(map(int,rectangle)),net=net))
    def wire(layer,a,b,net):
        assert a[0]==b[0]or a[1]==b[1]
        add(layer,[min(a[0],b[0])-u(1),min(a[1],b[1])-u(1),max(a[0],b[0])+u(1),max(a[1],b[1])+u(1)],net)
    for bit in range(16):
        net='data[%d]'%bit
        x=u(160.095)+(u(8)*bit if kind=='vertical16'else 0);y=u(160.07)+(0 if kind=='vertical16'else u(8)*bit)
        add('metal10',box(x,y),net);add('via10',box(x,y),net)
        if kind=='horizontal16':
            end=[u(64.095),y];wire('metal11',[x,y],end,net)
        elif kind=='vertical16':
            end=[x,u(512.07)];add('metal11',box(x,y),net);add('via11',box(x,y),net);wire('metal12',[x,y],end,net)
        else:
            tx=u(352.095)-u(8)*bit;end=[tx,u(512.07)]
            wire('metal11',[x,y],[tx,y],net);add('via11',box(tx,y),net);wire('metal12',[tx,y],end,net)
        ports.append(dict(net=net,source_m10_dbu=[x,y],external_endpoint_dbu=end,
                          endpoint_layer='metal11'if kind=='horizontal16'else'metal12'))
    return dict(schema='coarse-interface-fixture/1',name=kind,dbu_per_um=DBU,macro_box_dbu=[u(128),u(128),u(384),u(384)],
                test_boundary_dbu=[u(32),u(32),u(544),u(544)],ports=ports,shapes=shapes)


def distance(a,b):
    dx=max(0,a[0]-b[2],b[0]-a[2]);dy=max(0,a[1]-b[3],b[1]-a[3])
    return math.hypot(dx,dy)


def contains(outer,inner):return outer[0]<=inner[0]and outer[1]<=inner[1]and outer[2]>=inner[2]and outer[3]>=inner[3]


def verify(data,technology):
    assert technology['rule_id']=='nangate45-custom12-demo-2um-v1'
    g=technology['geometry_um'];assert (g['width'],g['spacing'],g['cut_width'],g['cut_spacing'],g['enclosure'])==(2.,2.,2.,2.2,0.)
    shapes=data['shapes'];assert data['dbu_per_um']==DBU
    names={p['net']for p in data['ports']};assert len(names)==16 and len(data['ports'])==16
    assert all(s['layer']in LAYERS and s['net']in names for s in shapes)
    links=[set()for s in shapes]
    for i,a in enumerate(shapes):
        rect=a['box_dbu'];assert len(rect)==4 and all(type(v)is int for v in rect)and rect[0]<rect[2]and rect[1]<rect[3]
        width=u(.8 if a['layer']=='metal10'else 2)
        assert min(rect[2]-rect[0],rect[3]-rect[1])>=width
        if a['layer'].startswith('via'):
            assert rect[2]-rect[0]==u(2)and rect[3]-rect[1]==u(2)
            assert (rect[0]+u(1)-u(g['track_offset_x']))%u(g['pitch'])==0
            assert (rect[1]+u(1)-u(g['track_offset_y']))%u(g['pitch'])==0
        for j,b in enumerate(shapes[:i]):
            if a['layer']!=b['layer']:continue
            gap=distance(rect,b['box_dbu'])
            if a['net']!=b['net']:
                required=u(2.2 if a['layer'].startswith('via')else .8 if a['layer']=='metal10'else 2)
                assert gap>=required,(a,b,gap,required)
            elif gap==0:links[i].add(j);links[j].add(i)
    for i,s in enumerate(shapes):
        if not s['layer'].startswith('via'):continue
        lower,upper=(('metal10','metal11')if s['layer']=='via10'else('metal11','metal12'))
        for layer in (lower,upper):
            hits=[j for j,t in enumerate(shapes)if t['layer']==layer and t['net']==s['net']and contains(t['box_dbu'],s['box_dbu'])]
            assert hits,('unenclosed via',s,layer)
            for j in hits:links[i].add(j);links[j].add(i)
    for port in data['ports']:
        indices={i for i,s in enumerate(shapes)if s['net']==port['net']};assert indices
        p=port['source_m10_dbu'];q=port['external_endpoint_dbu'];x0,y0,x1,y1=data['macro_box_dbu']
        assert x0<p[0]<x1 and y0<p[1]<y1
        assert not(x0<=q[0]<=x1 and y0<=q[1]<=y1),'Endpoint must really exit macro'
        assert any(shapes[i]['layer']=='metal10'and contains(shapes[i]['box_dbu'],[*p,*p])for i in indices)
        assert any(shapes[i]['layer']==port['endpoint_layer']and contains(shapes[i]['box_dbu'],[*q,*q])for i in indices)
        seen=set();todo=[next(iter(indices))]
        while todo:
            i=todo.pop()
            if i in seen:continue
            seen.add(i);todo.extend(links[i]-seen)
        assert seen==indices,('Open or wrong-net graph',port['net'])
    return dict(passed=True,total_signal_bits=16,connected_bits=16,shorts=0,opens=0,geometry_violations=0,
                via10_count=sum(s['layer']=='via10'for s in shapes),via11_count=sum(s['layer']=='via11'for s in shapes))


def negative_controls(tech):
    cases={}
    d=fixture('horizontal16');next(s for s in d['shapes']if s['layer']=='metal10')['box_dbu']=list(map(int,box(u(160.095),u(160.07),.8)));cases['old_08_landing']=d
    d=fixture('vertical16');d['shapes']=[s for s in d['shapes']if not(s['layer']=='via11'and s['net']=='data[0]')];cases['missing_via']=d
    d=fixture('horizontal16');d['shapes'][0]['layer']='metal9';cases['wrong_layer']=d
    d=fixture('horizontal16');d['ports'][0]['external_endpoint_dbu']=[u(150),u(160.07)];cases['endpoint_inside_macro']=d
    d=fixture('horizontal16');d['shapes'][0]['box_dbu'][0]+=.5;cases['fractional_dbu']=d
    d=fixture('horizontal16');d['shapes'].append(dict(layer='metal11',box_dbu=d['shapes'][2]['box_dbu'][:],net='data[1]'));cases['different_net_short']=d
    # Two cuts may fit metal spacing while violating the stricter cut rule.
    d=fixture('vertical16')
    for s in d['shapes']:
        if s['net']=='data[1]':s['box_dbu'][0]-=u(4);s['box_dbu'][2]-=u(4)
    d['ports'][1]['source_m10_dbu'][0]-=u(4);d['ports'][1]['external_endpoint_dbu'][0]-=u(4);cases['four_um_via_pitch']=d
    d=fixture('horizontal16')
    for s in d['shapes']:s['box_dbu'][0]+=u(.705);s['box_dbu'][2]+=u(.705)
    for p in d['ports']:p['source_m10_dbu'][0]+=u(.705);p['external_endpoint_dbu'][0]+=u(.705)
    cases['old_track_phase']=d
    result={}
    for name,data in cases.items():
        rejected=False
        try:verify(data,tech)
        except (AssertionError,ValueError):rejected=True
        assert rejected,name
        result[name]=True
    bad=copy.deepcopy(tech);bad['rule_id']='nangate45-research-12m-v1'
    try:verify(fixture('horizontal16'),bad)
    except AssertionError:result['wrong_rule_version']=True
    assert result.get('wrong_rule_version')
    return result


def suite(root,out,cpus,run):
    from io_slots import file_sha
    from overlay import generate
    from klayout_overlay import generate as layer_map
    assert cpus in (1,16)
    folder=root/'project/experiments/block_v1';technology=json.loads((folder/'technology-2um-v1.json').read_text())
    platform=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45')
    generate(platform/'lef/NangateOpenCellLibrary.tech.lef',technology,out/'technology')
    layer_map(platform,technology,out/'klayout-technology')
    fixtures=[]
    for kind in ('horizontal16','vertical16','turn-reverse16'):
        d=fixture(kind);proof=verify(d,technology);name=kind+'.json';(out/name).write_text(json.dumps(d,indent=2)+'\n')
        fixtures.append(dict(name=kind,json_path=str(out/name),gds_path=str(out/(kind+'.gds')),proof=proof))
    (out/'fixtures.json').write_text(json.dumps(fixtures,indent=2)+'\n')
    script=(folder/'revision300_klayout.py').read_text().replace('FIXTURE_MANIFEST_PLACEHOLDER',str(out/'fixtures.json'))
    (out/'klayout_check.py').write_text(script)
    run(['klayout','-b','-r',out/'klayout_check.py'],'klayout-check.log')
    independent=json.loads((out/'klayout-results.json').read_text());assert independent['passed']
    result=dict(passed=True,stage='P1',technology_rule_id=technology['rule_id'],technology_sha256=file_sha(folder/'technology-2um-v1.json'),
                fixtures=fixtures,independent_gds_checks=independent,negative_controls=negative_controls(technology),
                full_macro_escape_qualified=False,revised_300mhz_leaf_qualified=False,
                scope='Three simultaneous16-net finite strip/turn fixtures, real GDS readback and independent KLayout geometry. No old/new complete macro, P&R or arbitrary connection qualification.')
    (out/'revision300-stripes.json').write_text(json.dumps(result,indent=2)+'\n')


if __name__=='__main__':
    here=Path(__file__).parent;tech=json.loads((here/'technology-2um-v1.json').read_text())
    print(json.dumps(dict(fixtures={k:verify(fixture(k),tech)for k in ('horizontal16','vertical16','turn-reverse16')},negative_controls=negative_controls(tech)),indent=2))
