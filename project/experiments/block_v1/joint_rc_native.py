"""Actual OpenDB import of scientifically accepted measured node couplings.

The tiny passive LEF anchors bind electrical node identities only. They are
not a routed copy of the field geometry, a block, or a parent physical design.
"""
import concurrent.futures
import json
from pathlib import Path
import sys
from joint_rc import assemble,emit_spef,receive


VARIANTS=['actual','wrong-unit','missing-coupling','permuted-ground','permuted-resistance','rewired-coupling']


def fixture_edges(geometry,nodes):
    from graph_field_verify import fixture_nodes
    points=dict(nodes['target']);pairs=fixture_nodes(geometry)[1]
    edges=[]
    for a,b in pairs:
        p,q=points[a],points[b]
        if p[2]!=q[2]:
            assert geometry=='via'and p[:2]==q[:2]
            # Explicit DC fixture hypothesis: its 0.8um square column uses
            # the native via9 0.5ohm value. It is NOT production via10 (0.6um).
            value=.5
        else:value=.03*sum(abs(p[i]-q[i])for i in [0,1])/.8
        edges.append(dict(a=a,b=b,ohm=value))
    near=dict(nodes['near']);a,b=list(near)
    return dict(target=edges,near=[dict(a=a,b=b,ohm=.03*sum(abs(near[a][i]-near[b][i])for i in [0,1])/.8)])


READBACK=r'''
proc node_key {node} {
  set prefix "[[$node getNet] getName]/"
  if {[$node isITerm]} {
    set term [$node getITerm]
    return "${prefix}I:[[$term getInst] getName]/[[$term getMTerm] getName]"
  }
  if {[$node isBTerm]} {return "${prefix}P:[[$node getBTerm] getName]"}
  return "${prefix}N:[$node getNode]"
}
set block [ord::get_db_block]
set gs [open nodes.tsv w]
set rs [open resistors.tsv w]
foreach net [$block getNets] {
  foreach node [$net getCapNodes] {puts $gs "[node_key $node]\t[$node getCapacitance]"}
  foreach edge [$net getRSegs] {
    set pair [lsort [list [node_key [$edge getSourceCapNode]] [node_key [$edge getTargetCapNode]]]]
    puts $rs "[lindex $pair 0]\t[lindex $pair 1]\t[$edge getResistance]"
  }
}
close $gs
close $rs
set cs [open coupling.tsv w]
set counts [open coupling-infile-count.tsv w]
foreach edge [$block getCCSegs] {
  set pair [lsort [list [node_key [$edge getSourceCapNode]] [node_key [$edge getTargetCapNode]]]]
  puts $cs "[lindex $pair 0]\t[lindex $pair 1]\t[$edge getCapacitance]"
  puts $counts "[lindex $pair 0]\t[lindex $pair 1]\t[$edge getInfileCnt]"
}
close $cs
close $counts
'''


def anchor_files(out,model,instances):
    lef=['VERSION 5.8 ;','BUSBITCHARS "[]" ;','DIVIDERCHAR "/" ;']
    for layer in [10,11,12]:
        name='ANCHOR'+str(layer)
        lef += ['MACRO '+name,' CLASS BLOCK ;',' ORIGIN 0 0 ;',' SIZE 0.08 BY 0.08 ;',
            ' SYMMETRY X Y ;',' PIN p','  DIRECTION INOUT ;','  USE SIGNAL ;','  PORT',
            '   LAYER metal%d ;'%layer,'   RECT 0 0 0.08 0.08 ;','  END',' END p','END '+name]
    lef+=['END LIBRARY'];(out/'anchors.lef').write_text('\n'.join(lef)+'\n')
    text='VERSION 5.8 ;\nDIVIDERCHAR "/" ;\nBUSBITCHARS "[]" ;\nDESIGN joint_rc_probe ;\nUNITS DISTANCE MICRONS 2000 ;\nDIEAREA ( 0 0 ) ( 128000 128000 ) ;\nCOMPONENTS %d ;\n'%len(instances)
    centers={10:11.09,11:13.89,12:16.69}
    for net in model['nets']:
        for node,p in model['nodes'][net].items():
            layer=min(centers,key=lambda k:abs(centers[k]-p[2]));assert abs(centers[layer]-p[2])<1e-8
            xy=[int(round((p[k]+32-.04)*2000))for k in [0,1]]
            text+='- %s ANCHOR%d + FIXED ( %d %d ) N ;\n'%(instances[net+'/'+node],layer,*xy)
    text+='END COMPONENTS\nNETS %d ;\n'%len(model['nets'])
    for net in model['nets']:
        text+='- '+net+' '+''.join('( '+instances[net+'/'+node]+' p ) 'for node in model['nodes'][net])+'+ USE SIGNAL ;\n'
    text+='END NETS\nEND DESIGN\n';(out/'anchors.def').write_text(text)


def verify(root,out,cpus,run,geometry):
    from io_slots import file_sha
    assert cpus>=1 and geometry in ('branch','via');base=out.parents[2]
    source=base/'block-v1-20261027-100/tasks'/('capture-'+geometry+'-fv')
    receipt=json.loads((source/'receipt.json').read_text());assert receipt['passed'] is True
    report=source/'capture-field-fv.json';assert file_sha(report)==receipt['outputs'][report.name]
    science=json.loads(report.read_text());assert science['passed'] is True and science['reciprocal_joint_coupling'] is True
    assert all(all(g.values())for g in science['directional_gates'].values())
    for name in ['capture_field_verify.py','graph_field_verify.py','partial_field_verify.py']:
        relative='project/experiments/block_v1/'+name;assert file_sha(root/relative)==receipt['inputs'][relative]
    inputs={str(source/'receipt.json'):file_sha(source/'receipt.json'),str(report):file_sha(report)}
    rows={net:series[-1]for net,series in science['field_rows'].items()}
    model=assemble(science['nodes'],fixture_edges(geometry,science['nodes']),rows)
    (out/'measured-joint-rc.json').write_text(json.dumps(model,indent=2)+'\n')
    _,instances,native=emit_spef(model);anchor_files(out,model,instances)
    original=base/'block-v1-20261027-009/tasks/route-probe';bound=json.loads((original/'receipt.json').read_text());assert bound['passed'] is True
    tech=original/'overlay/research12.tech.lef';assert file_sha(tech)==bound['outputs']['overlay/research12.tech.lef'];inputs[str(tech)]=file_sha(tech)
    (out/'create.tcl').write_text('set_thread_count 1\nread_lef {'+str(tech)+'}\nread_lef anchors.lef\nread_def anchors.def\nwrite_db anchors.odb\n')
    run(['openroad','-no_init','-exit',str(out/'create.tcl')],'create.log')
    odb=out/'anchors.odb';odb_sha=file_sha(odb)
    child='import os,sys;os.chdir(sys.argv[1]);os.execvp("openroad",["openroad","-no_init","-exit","receive.tcl"])'
    def execute(variant):
        folder=out/variant;folder.mkdir()
        text,current_instances,current_native=emit_spef(model,variant);assert current_instances==instances and current_native==native
        (folder/'candidate.spef').write_text(text)
        (folder/'receive.tcl').write_text('set_thread_count 1\nread_db {'+str(odb)+'}\nbench_read_spef candidate.spef\n'+READBACK)
        run([sys.executable,'-c',child,str(folder)],variant+'.log')
        result=receive(folder,model,native)
        assert result['passed']==(variant=='actual'),(variant,result)
        if variant=='rewired-coupling':
            actual_c={tuple(sorted((native[c['a']],native[c['b']]))):c['ff']for c in model['coupling']}
            measured_c={tuple(sorted((c['a'],c['b']))):c['value']for c in result['coupling_ff']}
            assert set(actual_c)==set(measured_c)
            degrees=lambda values:{n:sum(v for pair,v in values.items()if n in pair)for n in native.values()}
            expected,observed=degrees(actual_c),degrees(measured_c)
            assert all(abs(expected[n]-observed[n])<1e-7 for n in expected)
            assert result['checks']['exact_node_ground']and result['checks']['exact_edge_resistance']
            result['coupling_node_marginals_preserved']=True
        return variant,dict(result=result,spef_sha256=file_sha(folder/'candidate.spef'),script_sha256=file_sha(folder/'receive.tcl'))
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(cpus,len(VARIANTS)))as pool:variants=dict(pool.map(execute,VARIANTS))
    assert file_sha(odb)==odb_sha and all(file_sha(Path(p))==h for p,h in inputs.items())
    result=dict(schema='block-v1-joint-rc-native/1',passed=True,geometry=geometry,
        model_sha256=file_sha(out/'measured-joint-rc.json'),science_receipt_sha256=file_sha(source/'receipt.json'),
        science_report_sha256=file_sha(report),inputs=inputs,native_node_mapping=native,readback=variants,
        coupling_count=len(model['coupling']),resistor_count=len(model['resistors']),ground_node_count=len(model['ground_ff']),
        dc_hypothesis='0.03ohm/square, 0.8um wire; fixture-only0.8um square via uses0.5ohm. No production via10/11 DC qualification.',
        scope='Two independently accepted field fixtures -> measured node ground/pair-C -> exact native electrical SPEF import and corruption rejection; anchors bind identities only, no routed physical fixture/block, native/new-layer stitching or complete extraction qualification',
        qualified_routed_geometry=False,qualified_full_block=False,qualified_boundary_stitch=False)
    (out/'joint-rc-native.json').write_text(json.dumps(result,indent=2)+'\n')
