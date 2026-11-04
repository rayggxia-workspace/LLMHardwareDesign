"""Measured one-buffer pre-freeze hold ECO; all final gates remain mandatory."""
import hashlib
import itertools
import json
from pathlib import Path
import re
import shutil


def compare_def(before,after,instance,old,new):
    digest=hashlib.sha256();changes=[]
    with before.open('rb') as a,after.open('rb') as b:
        for x,y in itertools.zip_longest(a,b):
            assert x is not None and y is not None,'DEF line count changed'
            if x==y:digest.update(x);continue
            token=(' '+old+' ').encode()
            assert x.lstrip().startswith(('- '+instance+' '+old+' ').encode())
            assert y==x.replace(token,(' '+new+' ').encode(),1),'Unrelated DEF edit'
            changes.append(dict(before=x.decode().strip(),after=y.decode().strip()))
    assert len(changes)==1,'Expected one actual component-master change'
    return dict(identical_non_target_geometry=True,identical_target_terminal_connections=True,
                unchanged_routes_ports_placement=True,non_target_def_sha256=digest.hexdigest(),changes=changes)


def contacts(pins_path,wires_path):
    def rows(path):
        for line in path.read_text().splitlines():
            pin,layer,kind,*box=line.split('\t')
            yield pin,layer,kind,tuple(map(int,box))
    pins={};wires={}
    for pin,layer,kind,box in rows(pins_path):pins.setdefault((pin,layer),[]).append(box)
    for pin,layer,kind,box in rows(wires_path):wires.setdefault((pin,layer),[]).append(box)
    result={}
    for label in ('A','Z','VDD','VSS'):
        hits=[]
        for (pin,layer),boxes in pins.items():
            if pin!=label:continue
            for a in boxes:
                for b in wires.get((pin,layer),[]):
                    box=[max(a[0],b[0]),max(a[1],b[1]),min(a[2],b[2]),min(a[3],b[3])]
                    if box[0]<box[2] and box[1]<box[3]:hits.append(dict(layer=layer,box_dbu=box))
        assert hits,'Replacement terminal has no real conductor contact: '+label
        result[label]=hits
    return dict(passed=True,positive_area_contacts=result,
                scope='Actual transformed signal/PG pin contacts with unchanged wires; complete native/GDS DRC also required')


def controls(out):
    folder=out/'eco-controls';folder.mkdir()
    before=folder/'before.def';after=folder/'after.def'
    before.write_bytes(b'- target BUF_X2 + PLACED ( 0 0 ) N ;\nNETS 1 ;\n')
    after.write_bytes(b'- target BUF_X1 + PLACED ( 0 0 ) N ;\nNETS 1 ;\n')
    assert compare_def(before,after,'target','BUF_X2','BUF_X1')['identical_non_target_geometry']
    rejected=[]
    for text in [b'- target BUF_X1 + PLACED ( 1 0 ) N ;\nNETS 1 ;\n',b'- target BUF_X1 + PLACED ( 0 0 ) N ;\nNETS 2 ;\n']:
        after.write_bytes(text)
        try:compare_def(before,after,'target','BUF_X2','BUF_X1')
        except AssertionError:rejected.append(True)
    pins=folder/'pins.tsv';wires=folder/'wires.tsv'
    text=''.join(p+'\tmetal1\tpin\t0\t0\t100\t100\n' for p in ('A','Z','VDD','VSS'))
    pins.write_text(text);wires.write_text(text);assert contacts(pins,wires)['passed']
    for p in ('A','Z','VDD','VSS'):
        pins.write_text(''.join(line for line in text.splitlines(True) if not line.startswith(p+'\t')))
        try:contacts(pins,wires)
        except AssertionError:rejected.append(True)
    assert len(rejected)==6
    return dict(passed=True,negative_controls=6,scope='Reject moved component, changed unrelated DEF, and missing each signal/PG contact')


SNAPSHOT=r'''proc local_s_contacts {inst prefix} {
 set stream [open ${prefix}-pins.tsv w]
 set wire_stream [open ${prefix}-wires.tsv w]
 set itr [odb::new_dbWirePathItr]
 set path [odb::new_dbWirePath]
 set element [odb::new_dbWirePathShape]
 foreach term [$inst getITerms] {
  set label [[$term getMTerm] getName]
  foreach pin [[$term getMTerm] getMPins] {foreach box [$pin getGeometry] {
   bvgeom::db_box $stream $label $box pin [$inst getTransform]
  }}
  set net [$term getNet]
  if {$net eq "NULL"} {error "Disconnected measured terminal"}
  set wire [$net getWire]
  if {$wire ne "NULL"} {
   $itr begin $wire
   while {[$itr getNextPath $path]} {while {[$itr getNextShape $element]} {
    bvgeom::wire_shape $wire_stream $label [odb::dbWirePathShape_shape_get $element]
   }}
  }
  foreach special [$net getSWires] {foreach box [$special getWires] {bvgeom::db_box $wire_stream $label $box special}}
 }
 close $stream;close $wire_stream
 odb::delete_dbWirePathShape $element;odb::delete_dbWirePath $path;odb::delete_dbWirePathItr $itr
}
proc local_s_nets {inst} {
 set rows {}
 foreach term [$inst getITerms] {lappend rows [list [[$term getMTerm] getName] [[$term getNet] getName]]}
 return [lsort $rows]
}
'''


def implement(a,out,run,root,sha,dump):
    from qualify import source
    folder,receipt,flow,results=source(a.sealed)
    assert a.variant=='n5' and a.repair_instance in ('hold40630','wire1414','wire1415')
    instance=a.repair_instance;old='CLKBUF_X1' if instance=='hold40630' else 'BUF_X2';new='BUF_X1'
    failed=a.gates/'physical';fr=json.loads((failed/'run.json').read_text())
    f=failed/'five-macro-physical.json';assert not fr['passed'] and sha(f)==fr['outputs'][f.name]
    failure=json.loads(f.read_text());assert not failure['passed']
    assert failure['source_receipt_sha256']==sha(folder/'receipt.json')
    timing=failure['timing']['timed_endpoints']
    assert timing['minimum_hold_ns']<0 and timing['native_summary']['hold_checks']==1
    assert all(v for k,v in failure['checks'].items() if k!='all_real_timed_endpoints')
    assert all(v for k,v in timing['checks'].items() if k not in ('all_hold_nonnegative','native_hold_count_zero'))
    report=failed/'timing.rpt';assert sha(report)==fr['outputs'][report.name]
    assert ' '+instance+'/Z ('+old+')' in report.read_text(),'Target not on actual failed path'
    dump(out/'eco-audit-controls.json',controls(out))
    lib=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib')
    text=lib.read_text();starts=list(re.finditer(r'\bcell\s*\(\s*([^\s)]+)\s*\)\s*\{',text));functions={}
    for i,m in enumerate(starts):
        if m.group(1) not in (old,new):continue
        body=text[m.end():starts[i+1].start() if i+1<len(starts) else len(text)]
        assert not re.search(r'\b(?:ff|latch)\s*\(',body)
        assert re.findall(r'\bfunction\s*:\s*"([^"]+)"',body)==['A']
        functions[m.group(1)]=hashlib.sha256(body.encode()).hexdigest()
    assert set(functions)=={old,new}
    script='set_thread_count 16\nread_liberty {'+str(lib)+'}\nread_db {'+str(results/'6_final.odb')+'}\n'
    script+='source {'+str(root/'project/experiments/block_v1/odb_geometry.tcl')+'}\n'+SNAPSHOT
    script+='set inst [[ord::get_db_block] findInst {'+instance+'}]\n'
    script+='if {$inst eq "NULL" || [[$inst getMaster] getName] ne "'+old+'"} {error "Measured instance identity changed"}\n'
    script+='set original [local_s_nets $inst]\nset location [$inst getLocation]\nset orientation [$inst getOrient]\n'
    script+='set size [list [[$inst getMaster] getWidth] [[$inst getMaster] getHeight]]\n'
    script+='write_def before.def\nlocal_s_contacts $inst before\n'
    script+='if {[replace_cell [get_cells [list {'+instance+'}]] '+new+']!=1} {error "Native buffer replacement rejected"}\n'
    script+='if {[local_s_nets $inst] ne $original || [$inst getLocation] ne $location || [$inst getOrient] ne $orientation} {error "Terminal/placement identity changed"}\n'
    script+='if {[[$inst getMaster] getWidth]>[lindex $size 0] || [[$inst getMaster] getHeight]!=[lindex $size 1]} {error "Replacement exceeds original footprint"}\n'
    script+='local_s_contacts $inst after\nwrite_def after.def\nwrite_db edited.odb\n'
    script+='drt::check_drc_cmd native-whole-drc.rpt 0 0 0 0 local_s_hold_eco\n'
    (out/'edit.tcl').write_text(script);run(['openroad','-no_init','-exit',out/'edit.tcl'],'edit.log')
    geometry=compare_def(out/'before.def',out/'after.def',instance,old,new)
    physical=contacts(out/'after-pins.tsv',out/'after-wires.tsv')
    native=(out/'native-whole-drc.rpt').read_text();assert not native.strip(),'Changed candidate has native DRC'
    proof=dict(passed=True,kind='local-s-single-buffer-delay',source=str(folder),source_receipt_sha256=sha(folder/'receipt.json'),
        source_files=flow['final_files'],failure_receipt_sha256=sha(failed/'run.json'),failure_report_sha256=sha(f),
        target=dict(instance=instance,old_master=old,new_master=new),liberty_sha256=sha(lib),equivalent_functions=functions,
        native_whole_drc_zero=True,pin_contacts=physical,edited_odb_sha256=sha(out/'edited.odb'),**geometry)
    dump(out/'route-repair-proof.json',proof)
    nickname='bv1_'+flow['top'];relative='flow/results/nangate45/'+nickname+'/base'
    target=out/relative;target.mkdir(parents=True)
    for category in ('logs','reports','objects'):(out/'flow'/category/'nangate45'/nickname/'base').mkdir(parents=True)
    shutil.copyfile(out/'edited.odb',target/'6_1_fill.odb')
    shutil.copyfile(folder/'original-flow-final.sdc',target/'6_1_fill.sdc')
    for name in ('1_synth_lec.v','bv1-input-diodes.tsv','feed-input-receivers.tsv','feed-partition-fanout.tsv'):
        shutil.copyfile(results/name,target/name)
    for name in ('pins.json','pins.tcl','input.sdc','partition-fanout.tcl'):
        shutil.copyfile(folder/name,out/name)
    # Native final-report/RCX reads an already routed+filled database; routes
    # and all other components are proved identical above, never re-created.
    original=Path(flow['raw_source'])
    assert sha(original/'receipt.json')==flow['raw_receipt_sha256']
    original_receipt=json.loads((original/'receipt.json').read_text());assert original_receipt['passed']
    for name in ('input.v','input-diodes.tcl'):
        assert sha(original/name)==original_receipt['outputs'][name]
        shutil.copyfile(original/name,out/name)
    config=(folder/'config.mk').read_text().replace(str(original),str(out)).replace(str(folder),str(out))
    (out/'config.mk').write_text(config)
    for key,value in list(flow['actual_variables'].items()):
        flow['actual_variables'][key]=value.replace(str(original),str(out)).replace(str(folder),str(out))
    flow.update(passed=False,pipeline_completed=False,final_files={},config_sha256=sha(out/'config.mk'),
        postroute_repair=dict(proof_sha256=sha(out/'route-repair-proof.json')),
        postroute_scope='Historical six native stages completed; one measured buffer ECO followed by fresh native final-report/RCX; all four final gates fresh')
    command=['make','-C','/OpenROAD-flow-scripts/flow','DESIGN_CONFIG='+str(out/'config.mk'),'WORK_HOME='+str(out/'flow'),'NUM_CORES=16']
    run(command+['do-6_report'],'do-6_report.log')
    # A fresh native writer must retain the exact accepted ECO geometry.
    (out/'readback.tcl').write_text('read_db {'+str(target/'6_final.odb')+'}\nwrite_def final-readback.def\n')
    run(['openroad','-no_init','-exit',out/'readback.tcl'],'readback.log')
    assert sha(out/'final-readback.def')==sha(out/'after.def')
    assert sha(target/'6_final.sdc')==sha(folder/'original-flow-final.sdc')
    for ext in ('v','sdc','def','odb','spef'):
        f=target/('6_final.'+ext);assert f.stat().st_size>0
        flow['final_files'][f.name]=dict(path=str(f),bytes=f.stat().st_size,sha256=sha(f))
    assert source(folder)[1]==receipt
    flow.update(passed=True,pipeline_completed=True,raw_postroute_source_receipt_sha256=sha(folder/'receipt.json'))
    dump(out/'native-flow.json',flow)
    dump(out/'receipt.json',dict(passed=True,outputs={str(p.relative_to(out)):sha(p) for p in out.rglob('*') if p.is_file() and p.name not in ('receipt.json','run.json')},
        scope='Completed original native flow plus measured single-buffer ECO and fresh RCX; independent final acceptance pending'))
