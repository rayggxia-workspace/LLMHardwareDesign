"""Bind sealed scientific node charges to exact real OpenDB conductors.

These are explicitly encoded qualification routes, not automatic router output
or production via/DRC/full-block extraction qualification.
"""
import concurrent.futures
import json
from pathlib import Path
import re
import sys
from joint_rc import emit_spef,receive
from joint_rc_native import anchor_files,READBACK,VARIANTS
from joint_routed_geometry import parse,compare,controls


def routes(geometry):
    p=lambda x,y,e:'( %d %d %d )'%(round((x+32)*2000),round((y+32)*2000),round(e*2000))
    horizontal=lambda layer,x0,x1:'%s %s %s'%(layer,p(x0,0,0),p(x1,0,0))
    if geometry=='branch':
        target=horizontal('metal11',-3.2,3.2)+' NEW metal11 '+p(0,0,0)+' '+p(0,3.2,0)
    else:
        assert geometry=='via'
        target=horizontal('metal10',-3.2,3.2)+' NEW metal10 '+p(1.6,0,0)+' CAPTURE_via10 NEW metal11 '+p(1.6,0,.4)+' '+p(1.6,3.2,0)
    return dict(target=target,near=horizontal('metal12',-1.6,4.8))


def verify(root,out,cpus,run,geometry):
    from io_slots import file_sha
    from capture_field_verify import fixture
    assert cpus>=1 and geometry in ('branch','via');base=out.parents[2]
    source=base/'block-v1-20261027-180/tasks'/('joint-rc-native-'+geometry)
    bound=json.loads((source/'receipt.json').read_text());assert bound['passed']is True
    inputs={str(source/'receipt.json'):file_sha(source/'receipt.json')}
    for name in ['joint-rc-native.json','measured-joint-rc.json']:
        assert file_sha(source/name)==bound['outputs'][name];inputs[str(source/name)]=file_sha(source/name)
    prior=json.loads((source/'joint-rc-native.json').read_text());assert prior['passed']is True
    assert prior['geometry']==geometry and prior['qualified_full_block']is False
    for name in ['capture_field_verify.py','graph_field_verify.py','partial_field_verify.py','joint_rc.py','joint_rc_native.py']:
        relative='project/experiments/block_v1/'+name
        assert file_sha(root/relative)==bound['inputs'][relative],name
    model=json.loads((source/'measured-joint-rc.json').read_text())
    boxes,nodes=fixture(geometry)
    assert {n:dict(p)for n,p in nodes.items()}=={n:{k:list(v)for k,v in p.items()}for n,p in model['nodes'].items()}
    expected={net:[b for n,b in boxes if n==net]for net in model['nets']}
    geometry_controls=controls(geometry,boxes)
    _,instances,native=emit_spef(model);anchor_files(out,model,instances)
    text=(out/'anchors.def').read_text()
    for net,path in routes(geometry).items():
        pattern=r'(?m)^- '+net+r' (.*?)\+ USE SIGNAL ;$'
        text,count=re.subn(pattern,lambda m:'- '+net+' '+m.group(1)+'+ USE SIGNAL + ROUTED '+path+' ;',text)
        assert count==1
    (out/'routed-input.def').write_text(text)
    # The sealed science fixture has a 0.8um square cut without production
    # enclosure. Keep it named and scoped as a fixture, never BV1_via10.
    (out/'fixture-via.lef').write_text('VERSION 5.6 ;\nVIA CAPTURE_via10\n RESISTANCE 0.5 ;\n LAYER metal10 ; RECT -0.4 -0.4 0.4 0.4 ;\n LAYER via10 ; RECT -0.4 -0.4 0.4 0.4 ;\n LAYER metal11 ; RECT -0.4 -0.4 0.4 0.4 ;\nEND CAPTURE_via10\nEND LIBRARY\n')
    original=base/'block-v1-20261027-009/tasks/route-probe'
    receipt=json.loads((original/'receipt.json').read_text());assert receipt['passed']is True
    tech=original/'overlay/research12.tech.lef';assert file_sha(tech)==receipt['outputs']['overlay/research12.tech.lef']
    inputs[str(tech)]=file_sha(tech)
    exporter=root/'project/experiments/block_v1/odb_geometry.tcl'
    script='set_thread_count 1\nread_lef {'+str(tech)+'}\nread_lef anchors.lef\nread_lef fixture-via.lef\nread_def routed-input.def\nwrite_db routed.odb\nwrite_def routed.def\nsource {'+str(exporter)+'}\nbvgeom::export geometry.tsv\n'
    (out/'create-routed.tcl').write_text(script);run(['openroad','-no_init','-exit',str(out/'create-routed.tcl')],'create-routed.log')
    actual,kinds=parse((out/'geometry.tsv').read_text(),tech.read_text())
    union=compare(actual,expected)
    assert (kinds.get('wire-via',0)>0)==(geometry=='via')
    odb=out/'routed.odb';odb_sha=file_sha(odb);geometry_sha=file_sha(out/'geometry.tsv')
    child='import os,sys;os.chdir(sys.argv[1]);os.execvp("openroad",["openroad","-no_init","-exit","receive.tcl"])'
    def execute(variant):
        folder=out/variant;folder.mkdir()
        spef,current_instances,current_native=emit_spef(model,variant);assert current_instances==instances and current_native==native
        (folder/'candidate.spef').write_text(spef)
        script='set_thread_count 1\nread_db {'+str(odb)+'}\nbench_read_spef candidate.spef\n'+READBACK
        script+='source {'+str(exporter)+'}\nbvgeom::export geometry-after.tsv\nwrite_db received.odb\n'
        (folder/'receive.tcl').write_text(script);run([sys.executable,'-c',child,str(folder)],variant+'.log')
        result=receive(folder,model,native);assert result['passed']==(variant=='actual'),(variant,result)
        assert file_sha(folder/'geometry-after.tsv')==geometry_sha,'Parasitic import changed conductor geometry'
        return variant,dict(result=result,received_odb_sha256=file_sha(folder/'received.odb'),spef_sha256=file_sha(folder/'candidate.spef'))
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(cpus,len(VARIANTS)))as pool:observed=dict(pool.map(execute,VARIANTS))
    assert file_sha(odb)==odb_sha and all(file_sha(Path(p))==h for p,h in inputs.items())
    result=dict(schema='block-v1-joint-routed/1',passed=True,geometry=geometry,
        source_scientific_binding=prior,source_receipt_sha256=file_sha(source/'receipt.json'),inputs=inputs,
        routed_odb_sha256=odb_sha,routed_def_sha256=file_sha(out/'routed.def'),geometry_sha256=geometry_sha,
        exact_conductor_union=union,actual_geometry_kinds=kinds,geometry_controls=geometry_controls,readback=observed,
        node_positions_and_identities_bound=True,capacitance_from_identical_sealed_scientific_volume=True,
        qualified_production_via=False,qualified_full_drc=False,qualified_full_block=False,qualified_boundary_stitch=False,
        scope='Two explicitly routed OpenDB scientific fixtures, all conductor union/physical node coordinates and native measured pair-C readback; no automatic router, production via, general RC solver, native/new-layer stitching or full-block qualification')
    (out/'joint-routed.json').write_text(json.dumps(result,indent=2)+'\n')
