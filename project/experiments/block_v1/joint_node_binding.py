"""Read actual transformed pin positions; reject electrically invisible moves.

An unchanged conductor union and exact SPEF readback are necessary but do not
prove that a labelled sampling node still occupies its scientific position.
"""
import concurrent.futures
import json
from pathlib import Path
import sys
from joint_rc import emit_spef,receive
from joint_rc_native import READBACK
from joint_routed_geometry import integer,parse,compare


POSITIONS=r'''
set physical [open physical-nodes.tsv w]
foreach net [[ord::get_db_block] getNets] {
  foreach term [$net getITerms] {
    set inst [$term getInst]
    set transform [$inst getTransform]
    set count 0
    foreach mpin [[$term getMTerm] getMPins] {
      foreach box [$mpin getGeometry] {
        if {[$box isVia]} {error "Fixture node pin must be a routing rectangle"}
        set a [odb::new_Point [$box xMin] [$box yMin]]
        set b [odb::new_Point [$box xMax] [$box yMax]]
        $transform apply $a
        $transform apply $b
        puts $physical "[$net getName]/I:[$inst getName]/[[$term getMTerm] getName]\t[[$box getTechLayer] getName]\t[expr {[$a getX]+[$b getX]}]\t[expr {[$a getY]+[$b getY]}]"
        odb::delete_Point $a
        odb::delete_Point $b
        incr count
      }
    }
    if {$count != 1} {error "Fixture node needs exactly one physical pin rectangle"}
  }
}
close $physical
'''


def receive_positions(path,model,native):
    expected={};centers={10:11.09,11:13.89,12:16.69}
    for net,points in model['nodes'].items():
        for node,p in points.items():
            layer=min(centers,key=lambda k:abs(centers[k]-p[2]));assert abs(centers[layer]-p[2])<1e-8
            expected[native[net+'/'+node]]=['metal%d'%layer,2*integer(p[0]+32),2*integer(p[1]+32)]
    actual={}
    for line in path.read_text().splitlines():
        key,layer,x,y=line.split('\t');assert key not in actual
        actual[key]=[layer,int(x),int(y)]
    mismatch={key:dict(expected=value,actual=actual.get(key))for key,value in expected.items()if actual.get(key)!=value}
    return dict(passed=actual==expected,missing_or_moved=mismatch,unexpected=sorted(set(actual)-set(expected)),
        actual=actual,coordinate_unit='twice database unit, 2000dbu/um; pin center uses actual instance transform')


def verify(root,out,cpus,run,geometry):
    from io_slots import file_sha
    from capture_field_verify import fixture
    base=out.parents[2];source=base/'block-v1-20261027-182/tasks'/('joint-routed-'+geometry)
    receipt=json.loads((source/'receipt.json').read_text());assert receipt['passed']is True
    inputs={str(source/'receipt.json'):file_sha(source/'receipt.json')}
    for name in ['joint-routed.json','routed.odb','geometry.tsv','actual/candidate.spef']:
        assert file_sha(source/name)==receipt['outputs'][name];inputs[str(source/name)]=file_sha(source/name)
    prior=json.loads((source/'joint-routed.json').read_text());assert prior['passed']is True
    for name in ['joint_rc.py','joint_rc_native.py','joint_routed.py','joint_routed_geometry.py','capture_field_verify.py']:
        relative='project/experiments/block_v1/'+name;assert file_sha(root/relative)==receipt['inputs'][relative]
    measured=base/'block-v1-20261027-180/tasks'/('joint-rc-native-'+geometry)/'measured-joint-rc.json'
    assert file_sha(measured)==prior['inputs'][str(measured)];inputs[str(measured)]=file_sha(measured)
    model=json.loads(measured.read_text());_,instances,native=emit_spef(model)
    first=instances['target/left'];last=instances['target/right'];assert first!=last
    variants=dict(actual='',shift='''set inst [[ord::get_db_block] findInst %s]
set status [$inst getPlacementStatus]
$inst setPlacementStatus PLACED
lassign [$inst getLocation] x y
$inst setLocation [expr {$x+2}] $y
$inst setPlacementStatus $status
'''%first,swap='''set a [[ord::get_db_block] findInst %s]
set b [[ord::get_db_block] findInst %s]
set ast [$a getPlacementStatus]
set bst [$b getPlacementStatus]
$a setPlacementStatus PLACED
$b setPlacementStatus PLACED
lassign [$a getLocation] ax ay
lassign [$b getLocation] bx by
$a setLocation $bx $by
$b setLocation $ax $ay
$a setPlacementStatus $ast
$b setPlacementStatus $bst
'''%(first,last))
    tech=Path(next(p for p in prior['inputs']if p.endswith('/research12.tech.lef')))
    assert file_sha(tech)==prior['inputs'][str(tech)];inputs[str(tech)]=file_sha(tech)
    expected={net:[b for n,b in fixture(geometry)[0]if n==net]for net in model['nets']}
    child='import os,sys;os.chdir(sys.argv[1]);os.execvp("openroad",["openroad","-no_init","-exit","audit.tcl"])'
    exporter=root/'project/experiments/block_v1/odb_geometry.tcl'
    def execute(name):
        folder=out/name;folder.mkdir()
        script='set_thread_count 1\nread_db {'+str(source/'routed.odb')+'}\n'+variants[name]
        script+='bench_read_spef {'+str(source/'actual/candidate.spef')+'}\n'+READBACK+POSITIONS
        script+='source {'+str(exporter)+'}\nbvgeom::export geometry.tsv\nwrite_db observed.odb\n'
        (folder/'audit.tcl').write_text(script);run([sys.executable,'-c',child,str(folder)],name+'.log')
        physical=receive_positions(folder/'physical-nodes.tsv',model,native)
        electrical=receive(folder,model,native);assert electrical['passed']is True
        observed,kinds=parse((folder/'geometry.tsv').read_text(),tech.read_text())
        union=compare(observed,expected)
        assert physical['passed']==(name=='actual'),(name,physical)
        assert name=='actual'or len(physical['missing_or_moved'])==(1 if name=='shift'else 2)
        return name,dict(physical=physical,electrical=electrical,unchanged_conductor_union=union,
            observed_odb_sha256=file_sha(folder/'observed.odb'),physical_nodes_sha256=file_sha(folder/'physical-nodes.tsv'))
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(cpus,len(variants)))as pool:observed=dict(pool.map(execute,variants))
    assert all(file_sha(Path(p))==h for p,h in inputs.items())
    (out/'joint-node-binding.json').write_text(json.dumps(dict(schema='block-v1-joint-node-binding/1',passed=True,
        geometry=geometry,inputs=inputs,observations=observed,node_positions_and_identities_directly_received=True,
        qualified_full_block=False,qualified_production_via=False,qualified_boundary_stitch=False,
        scope='Direct transformed physical-node ID/position binding on sealed182 routed scientific fixtures; native shift/swap preserve conductor volume and all imported electrical values but must fail physical node binding'),indent=2)+'\n')
