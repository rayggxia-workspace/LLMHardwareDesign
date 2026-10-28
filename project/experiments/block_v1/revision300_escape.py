"""Actual full-port upper DEF/ODB plus a joined, unchanged native GDS scene.

This is a finite interface demonstrator, never a hierarchical timing model or
process qualification. All source gates/geometry must already be accepted.
"""
import copy
import json
import re
from pathlib import Path


def union_equal(left,right):
    """Exact2D rectangular union, independent of partition and box ordering."""
    assert left and right
    xs=sorted({b[i]for b in left+right for i in (0,2)})
    ys=sorted({b[i]for b in left+right for i in (1,3)})
    assert (len(xs)-1)*(len(ys)-1)<100000
    for x0,x1 in zip(xs,xs[1:]):
        for y0,y1 in zip(ys,ys[1:]):
            inside=lambda boxes:any(b[0]<=x0<x1<=b[2]and b[1]<=y0<y1<=b[3]for b in boxes)
            assert inside(left)==inside(right),('Rectangle union differs',x0,y0,x1,y1)


def geometry(path,names):
    aliases={};shapes=[]
    for line in Path(path).read_text().splitlines():
        if line.startswith('# NET '):
            _,_,alias,encoded=line.split();aliases[alias]=bytes.fromhex(encoded).decode();continue
        if line.startswith('#'):continue
        alias,layer,kind,*box=line.split('\t');name=aliases[alias]
        if name not in names:continue
        assert layer in ('metal10','via10','metal11','via11','metal12'),(name,layer,kind)
        assert kind in ('wire','wire-via','block-port','instance-pin'),kind
        shapes.append(dict(net=name,layer=layer,box_dbu=list(map(int,box))))
    assert {s['net']for s in shapes}==names
    return shapes


def compare(actual,expected):
    keys={(s['net'],s['layer'])for s in expected}
    assert {(s['net'],s['layer'])for s in actual}==keys
    for net,layer in keys:
        subset=lambda rows:[s['box_dbu']for s in rows if (s['net'],s['layer'])==(net,layer)]
        union_equal(subset(actual),subset(expected))


def control(technology):
    from revision300_geometry import fixture,verify
    expected=fixture('horizontal16');compare(expected['shapes'],expected['shapes'])
    rejected=[]
    for label in ('missing_via','shift','wrong_net','extra_shape','old_landing','wrong_layer'):
        bad=copy.deepcopy(expected)
        if label=='missing_via':bad['shapes']=[s for s in bad['shapes']if not(s['net']=='data[0]'and s['layer']=='via10')]
        elif label=='shift':bad['shapes'][0]['box_dbu'][0]+=1
        elif label=='wrong_net':bad['shapes'][0]['net']='data[1]'
        elif label=='extra_shape':bad['shapes'].append(dict(net='data[0]',layer='metal11',box_dbu=[1,1,2,2]))
        elif label=='old_landing':bad['shapes'][0]['box_dbu'][2]-=2400
        else:bad['shapes'][0]['layer']='metal9'
        try:compare(bad['shapes'],expected['shapes'])
        except AssertionError:rejected.append(label)
        else:raise AssertionError('Accepted altered actual geometry: '+label)
    # Partitioned rectangles are a valid positive; missing/extra metal is not.
    split=copy.deepcopy(expected['shapes']);s=split.pop();a,b,c,d=s['box_dbu'];m=(a+c)//2
    split.extend([dict(s,box_dbu=[a,b,m,d]),dict(s,box_dbu=[m,b,c,d])]);compare(split,expected['shapes'])
    verify(expected,technology)
    return dict(passed=True,repartitioned_positive=True,rejected=rejected)


def write_def(top,fixture,pins,pg):
    side=fixture['test_boundary_dbu'][2];ports={p['net']:p for p in fixture['ports']}
    assert fixture['test_boundary_dbu'][:2]==[0,0]
    rows=['VERSION 5.8 ;','DIVIDERCHAR "/" ;','BUSBITCHARS "[]" ;','DESIGN escape_'+top+' ;',
          'UNITS DISTANCE MICRONS 2000 ;','DIEAREA ( 0 0 ) ( %d %d ) ;'%(side,side),
          'COMPONENTS 1 ;','- LEAF '+top+' + FIXED ( 80000 80000 ) N ;','END COMPONENTS',
          'PINS %d ;'%len(pins)]
    for pin in pins:
        n=pin['pin'];assert re.fullmatch(r'[A-Za-z_][A-Za-z0-9_\[\]]*',n)
        p=ports[n];x,y=p['external_endpoint_dbu'];use='CLOCK'if n=='clk'else'SIGNAL'
        rows+=['- %s + NET %s + DIRECTION %s + USE %s'%(n,n,pin['direction'].upper(),use),
               ' + LAYER %s ( -2000 -2000 ) ( 2000 2000 ) + FIXED ( %d %d ) N ;'%(p['endpoint_layer'],x,y)]
    rows+=['END PINS','NETS %d ;'%len(pins)]
    for pin in pins:
        n=pin['pin'];p=ports[n];x,y=p['source_m10_dbu'];ex,ey=p['external_endpoint_dbu']
        rows+=['- %s ( PIN %s ) ( LEAF %s ) + ROUTED metal10 ( %d %d ) BV1_via10'%(n,n,n,x,y)]
        if p['endpoint_layer']=='metal12':rows+=[' NEW metal11 ( %d %d ) BV1_via11'% (x,y)]
        rows+=[' NEW %s ( %d %d ) ( %d %d ) ;'%(p['endpoint_layer'],x,y,ex,ey)]
    rows+=['END NETS','SPECIALNETS %d ;'%len(pg)]
    for name,sigtype in sorted(pg.items()):rows+=['- %s ( LEAF %s ) + USE %s ;'%(name,name,sigtype)]
    rows+=['END SPECIALNETS','END DESIGN']
    return '\n'.join(rows)+'\n'


def implement(root,out,cpus,run,kind):
    from io_slots import file_sha
    from revision300_delivery import accepted,config
    from revision300_receive import source
    from revision300_ports import generate
    from revision300_geometry import verify,u
    from overlay import generate as technology_overlay
    assert cpus==16 and kind in 'mvrst'
    index,odb,provenance,count,die=accepted(root,out,kind)
    folder,_,flow,_=source(root,out,kind);base=out.parents[2]
    geom=base/config(root)['geometry'][kind]
    assert base in geom.resolve().parents and geom.name=='revision300-geometry-'+kind
    receipt=json.loads((geom/'receipt.json').read_text());assert receipt['passed'] and receipt['mode']==geom.name
    p=geom/'five-macro-geometry.json';assert file_sha(p)==receipt['outputs'][p.name]
    proof=json.loads(p.read_text());assert proof['passed'] and proof['original_odb_unchanged'] and proof['native_def_rect_complete']
    assert proof['source_odb_sha256']==index['final_files']['6_final.odb']['sha256']
    for name in ('candidate.lef','m10-access.json','native-pins.tsv','source-occupancy.tsv'):
        assert file_sha(geom/name)==receipt['outputs'][name]==proof['files'][name]['sha256']
    tools=root/'project/experiments/block_v1'
    technology=json.loads((tools/'technology-2um-v1.json').read_text());assert proof['files']['m10-access.json']
    assert json.loads((geom/'m10-access.json').read_text())['technology_sha256']==file_sha(tools/'technology-2um-v1.json')
    plan=json.loads((folder/'pins.json').read_text());ports={}
    for pin in plan['pins']:
        p=ports.setdefault(pin['port'],dict(bits=0,direction=pin['direction']))
        assert p['direction']==pin['direction'];p['bits']=max(p['bits'],pin['index']+1)
    rebuilt,fixture,_=generate(ports,die[0],technology)
    assert rebuilt==plan and die[0]==die[1] and len(plan['pins'])==count
    actual={p['pin']:p for p in json.loads((geom/'m10-access.json').read_text())['pins']}
    assert set(actual)=={p['net']for p in fixture['ports']}
    for p in fixture['ports']:assert actual[p['net']]['center_dbu']==p['source_m10_dbu']
    # Translation by40um preserves both native and custom track phases. The
    # complete test footprint/halo is charged, not cropped to pin windows.
    offset=u(40)
    for key in ('macro_box_dbu','test_boundary_dbu'):fixture[key]=[x+offset for x in fixture[key]]
    for s in fixture['shapes']:s['box_dbu']=[x+offset for x in s['box_dbu']]
    for p in fixture['ports']:
        for key in ('source_m10_dbu','external_endpoint_dbu'):p[key]=[x+offset for x in p[key]]
    verify(fixture,technology)
    pg={}
    for line in (geom/'native-pins.tsv').read_text().splitlines():
        name,direction,sigtype,*_=line.split('\t')
        if sigtype in ('POWER','GROUND'):pg[name]=sigtype
    assert set(pg.values())=={'POWER','GROUND'}
    platform=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45')
    technology_overlay(platform/'lef/NangateOpenCellLibrary.tech.lef',technology,out/'technology')
    (out/'upper.def').write_text(write_def(flow['top'],fixture,plan['pins'],pg))
    helper=tools/'odb_geometry.tcl'
    inventory='''set f [open INVENTORY w]
set block [ord::get_db_block]
if {[llength [$block getInsts]] != 1} {error "Expected one frozen macro"}
foreach term [$block getBTerms] {
 set name [$term getName];set net [$term getNet]
 if {[$net getName] ne $name || [llength [$net getITerms]] != 1 || [llength [$net getBTerms]] != 1} {error "Port identity/count mismatch"}
 set inner [lindex [$net getITerms] 0]
 if {[[$inner getInst] getName] ne "LEAF" || [[$inner getMTerm] getName] ne $name} {error "Wrong macro bit"}
 puts $f "$name\\t[$term getIoType]\\t[$term getSigType]"
}
close $f
'''
    header='read_lef {'+str(out/'technology/research12.tech.lef')+'}\nread_lef {'+str(geom/'candidate.lef')+'}\n'
    for label,read in [('initial',header+'read_def {'+str(out/'upper.def')+'}\n'),
                       ('odb-reload','read_db {'+str(out/'upper.odb')+'}\n'),
                       ('def-reload',header+'read_def {'+str(out/'upper-roundtrip.def')+'}\n')]:
        script='set_thread_count 16\n'+read+'source {'+str(helper)+'}\n'
        script+=inventory.replace('INVENTORY',str(out/(label+'-ports.tsv')))
        script+='bvgeom::export {'+str(out/(label+'-geometry.tsv'))+'}\n'
        if label=='initial':script+='write_db {'+str(out/'upper.odb')+'}\nwrite_def {'+str(out/'upper-roundtrip.def')+'}\n'
        (out/(label+'.tcl')).write_text(script);run(['openroad','-no_init','-exit',out/(label+'.tcl')],label+'.log')
    expected_names=set(actual)
    received=[]
    for label in ('initial','odb-reload','def-reload'):
        names={line.split('\t')[0]for line in(out/(label+'-ports.tsv')).read_text().splitlines()}
        assert names==expected_names
        shapes=geometry(out/(label+'-geometry.tsv'),names);compare(shapes,fixture['shapes'])
        checked=dict(fixture,shapes=shapes);verify(checked,technology);received.append(checked)
    # Whole native M10 conductors, PG, terminals and OBS are inspected under
    # their actual net IDs, never treating an obstruction as a conductor.
    intersections=0;obstructions=0
    for line in(geom/'source-occupancy.tsv').open():
        if line.startswith('#'):continue
        net,layer,typ,*box=line.rstrip('\n').split('\t')
        if layer!='metal10':continue
        box=list(map(int,box))
        for pin in actual.values():
            cut=pin['via10_cut_dbu'];overlap=max(box[0],cut[0])<min(box[2],cut[2])and max(box[1],cut[1])<min(box[3],cut[3])
            if not overlap:continue
            if 'obstruction'in typ:obstructions+=1;raise AssertionError('Native M10 obstruction overlaps new via: '+pin['pin'])
            assert net==pin['net'],('New via meets other native net',pin['pin'],net,pin['net'])
            intersections+=1
    assert intersections>=count
    (out/'actual-escape.json').write_text(json.dumps(received[-1],indent=2)+'\n')
    (out/'gds-inputs.json').write_text(json.dumps(dict(native_gds=index['final_files']['6_final.gds']['path'],
        fixture=str(out/'actual-escape.json'),offset_um=40,output=str(out/'joined.gds')),indent=2)+'\n')
    script=(tools/'revision300_escape_gds.py').read_text().replace('INPUT_MANIFEST_PLACEHOLDER',str(out/'gds-inputs.json'))
    (out/'gds-readback.py').write_text(script);run(['klayout','-b','-r',out/'gds-readback.py'],'gds-readback.log')
    readback=json.loads((out/'joined-readback.json').read_text());assert readback['passed']
    # Early RC is explicit and cannot masquerade as calibrated extraction or
    # as proof that the existing50fF leaf boundary includes the whole escape.
    rc=json.loads((out/'technology/early-rc-estimates.json').read_text());costs=[]
    for p in fixture['ports']:
        a,b=p['source_m10_dbu'],p['external_endpoint_dbu'];length=(abs(a[0]-b[0])+abs(a[1]-b[1]))/2000
        vias=1 if p['endpoint_layer']=='metal11' else 2
        costs.append(dict(net=p['net'],length_um=length,vias=vias,base_wire_cap_ff=length*rc['variants']['base']['capacitance'],
                          high_wire_cap_ff=length*rc['variants']['high']['capacitance'],
                          base_series_r_ohm=length*rc['variants']['base']['resistance']+vias*rc['variants']['base']['via_resistance']))
    native_odb_sha=file_sha(odb);assert native_odb_sha==proof['source_odb_sha256']
    assert file_sha(Path(index['final_files']['6_final.gds']['path']))==index['final_files']['6_final.gds']['sha256']
    result=dict(passed=True,stage='P2-geometry',macro=kind.upper(),all_signal_bits=count,simultaneous_connected_bits=count,
        source_delivery=provenance,source_geometry_receipt_sha256=file_sha(geom/'receipt.json'),source_odb_sha256=native_odb_sha,
        technology_sha256=file_sha(tools/'technology-2um-v1.json'),native_original_files_unchanged=True,
        three_actual_odb_def_geometry_readbacks=True,independent_joined_gds=readback,negative_controls=control(technology),
        native_m10_same_net_intersections=intersections,native_m10_obstruction_intersections=obstructions,
        native_die_um=die,test_footprint_um=[d+80 for d in die],charged_halo_um=40,
        wire_length_um=sum(p['length_um']for p in costs),via10_count=count,via11_count=sum(p['vias']==2 for p in costs),
        early_rc_costs=costs,over_48ff_base_wire_budget=[p['net']for p in costs if p['base_wire_cap_ff']>48],
        early_rc_qualified=False,combined_300mhz_interface_timing_qualified=False,m11_m12_system_qualified=False,
        scope='Every real bit connected in standalone upper DEF/ODB and joined unchanged native GDS, exact geometry/net identities/readbacks and new-layer rules. Full external footprint charged. RC uncalibrated; extra wire load requires separate same-source interface timing. No array/arbitrary permutation/manufacturing qualification.')
    (out/'revision300-escape.json').write_text(json.dumps(result,indent=2)+'\n')
