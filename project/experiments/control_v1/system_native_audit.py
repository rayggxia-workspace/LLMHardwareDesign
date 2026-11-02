"""Audit hierarchical RC coverage and type physical sinks from actual native ODBs."""
import json,subprocess,sys
from pathlib import Path


def audit(manifest,graph,out,library,bind,linked_passive=None):
    native=Path(__file__).resolve().parents[1]/'block_v1'
    sys.path.insert(0,str(native))
    from native_annotation import inspect
    from native_passive_endpoint import audit as type_endpoints
    for name in ('native_annotation.py','native_passive_endpoint.py','native_sta.py','native_cell_gate.py'):
        bind(native/name)
    inventories={}
    for top,row in manifest['leaves'].items():
        odb=row['final_files']['6_final.odb'];bind(odb['path'],odb['sha256'])
        folder=out/('inventory-'+top);folder.mkdir()
        script='read_db {'+odb['path']+'}\n'
        script+='''set f [open passive.tsv w]
foreach inst [[ord::get_db_block] getInsts] {
  set master [$inst getMaster]
  if {[$master getName] ne "ANTENNA_X1"} {continue}
  foreach term [$inst getITerms] {
    set definition [$term getMTerm]
    if {[$definition getSigType] in {POWER GROUND}} {continue}
    set net [$term getNet]
    if {$net eq "NULL"} {error "Disconnected passive input"}
    puts $f "[$inst getName]/[$definition getName]\\t[$master getName]\\t[$master getType]\\t[$definition getIoType]\\t[$net getName]"
  }
}
close $f
'''
        path=folder/'inventory.tcl';path.write_text(script)
        with (folder/'readback.log').open('w') as stream:
            result=subprocess.run(['openroad','-no_init','-exit',path],cwd=folder,stdout=stream,stderr=subprocess.STDOUT)
        assert result.returncode==0,top
        for generated in (path,folder/'passive.tsv',folder/'readback.log'):bind(generated)
        inventories[top]={}
        for line in (folder/'passive.tsv').read_text().splitlines():
            pin,master,kind,direction,net=line.split('\t')
            assert pin not in inventories[top]
            inventories[top][pin]=dict(master=master,type=kind,direction=direction,net=net,pin=pin.rsplit('/',1)[1])
    inventory={}
    for instance,top in graph['instances'].items():
        for pin,row in inventories[top].items():
            key=instance+'/'+pin;assert key not in inventory
            inventory[key]=dict(row,net=instance+'/'+row['net'])
    coverage=inspect(out)
    not_endpoints={}
    if linked_passive is not None:
        linked={}
        for line in linked_passive.read_text().splitlines():
            pin,master,direction,value=line.split('\t');assert pin not in linked
            linked[pin]=dict(master=master,direction=direction,value=value)
        assert set(linked)==set(inventory),'Actual linked passive cells differ from actual native ODB inventory'
        assert all(row['master']=='ANTENNA_X1' and row['direction']=='input' for row in linked.values())
        endpoints={line.split('\t')[0] for line in (out/'endpoints.tsv').read_text().splitlines()}
        not_endpoints={pin:dict(inventory[pin],linked=linked[pin]) for pin in set(inventory)-endpoints}
        assert all(row['linked']['value'] in ('0','1') for row in not_endpoints.values()),'Missing physical sink is not proven constant in actual linked STA graph'
    typed=type_endpoints(out,out/'typed-endpoints',library.read_text(),{pin:row for pin,row in inventory.items() if pin not in not_endpoints})
    record=dict(passed=coverage['passed'] and typed['passed'],coverage=coverage,typed=typed,
                actual_physical_passive_count=len(inventory),constant_passive_not_returned_as_sta_endpoint=not_endpoints,
                whole_system_qualified=False,
                scope='Exact native ODB passive typing and connected-driver coverage. Upper RC, geometry, PG and complete system acceptance remain separate.')
    (out/'native-system-audit.json').write_text(json.dumps(record,indent=2)+'\n')
    return record


def postaudit(a,bind,sha):
    """Retain exact prior STA tables; independently query the same linked cells."""
    import shutil
    source=a.audit_existing_results
    path=source/'receipt.json';bind(path);previous=json.loads(path.read_text())
    assert previous['execution_passed'] and previous['native_access_stitched']
    for path in (a.manifest,a.graph,a.topology,a.functional_views):
        assert previous['inputs'][str(path)]==sha(path);bind(path)
    for path,digest in previous['inputs'].items():bind(path,digest)
    for name in ('timing.tcl','endpoints.tsv','timing-summary.tsv','annotation.rpt','annotation-connectivity.tsv','constraints-readback.sdc','critical-first.rpt'):
        path=source/name;bind(path,previous['outputs'][name]);shutil.copyfile(path,a.out/name)
    # This is only a linked-cell/constant query. Do not rerun timing without
    # SPEF or substitute its values for the original complete RC timing tables.
    prefix=(source/'timing.tcl').read_text().split('read_sdc {',1)[0]
    query=prefix+'''sta::find_logic_constants
set f [open linked-passive.tsv w]
foreach cell [get_cells -hierarchical -filter {ref_name == ANTENNA_X1} *] {
  set name [get_full_name $cell]
  set pins [get_pins -quiet ${name}/A]
  if {[llength $pins]!=1} {error "Missing or ambiguous actual passive pin"}
  set pin [lindex $pins 0]
  puts $f "[get_full_name $pin]\\t[get_property $cell ref_name]\\t[string tolower [get_property $pin direction]]\\t[sta::pin_logic_value $pin]"
}
close $f
'''
    script=a.out/'linked-passive.tcl';script.write_text(query)
    with (a.out/'linked-passive.log').open('w') as stream:
        code=subprocess.run(['openroad','-no_init','-exit',script],cwd=a.out,stdout=stream,stderr=subprocess.STDOUT).returncode
    assert code==0,'linked-passive.log'
    manifest=json.loads(a.manifest.read_text());graph=json.loads(a.graph.read_text())
    lib=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib');bind(lib)
    result=audit(manifest,graph,a.out,lib,bind,a.out/'linked-passive.tsv')
    return dict(execution_passed=True,whole_system_qualified=False,original_sta_receipt=str(source/'receipt.json'),
                original_sta_receipt_sha256=sha(source/'receipt.json'),native_coverage_audit_passed=result['coverage']['passed'],
                typed_native_timing_passed=result['typed']['passed'],native_system_audit_passed=result['passed'],
                scope='Exact immutable native RC STA tables with new actual linked-cell constant/passive ownership query. Upper RC and full physical system qualification remain separate.')
