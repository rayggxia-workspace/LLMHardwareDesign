"""Audit hierarchical RC coverage and type physical sinks from actual native ODBs."""
import json,subprocess,sys
from pathlib import Path


def audit(manifest,graph,out,library,bind):
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
    linked={}
    for line in (out/'linked-passive.tsv').read_text().splitlines():
        pin,master,direction,added=line.split('\t');assert pin not in linked
        linked[pin]=dict(master=master,direction=direction,explicitly_added=added)
    assert set(linked)==set(inventory),'Actual linked passive cells differ from actual native ODB inventory'
    assert all(row['master']=='ANTENNA_X1' and row['direction']=='input' and row['explicitly_added'] in ('0','1') for row in linked.values())
    typed=type_endpoints(out,out/'typed-endpoints',library.read_text(),inventory)
    record=dict(passed=coverage['passed'] and typed['passed'],coverage=coverage,typed=typed,
                actual_physical_passive_count=len(inventory),explicitly_queried_missing_passive_endpoints=[pin for pin,row in linked.items() if row['explicitly_added']=='1'],
                whole_system_qualified=False,
                scope='Exact native ODB passive typing and connected-driver coverage. Upper RC, geometry, PG and complete system acceptance remain separate.')
    (out/'native-system-audit.json').write_text(json.dumps(record,indent=2)+'\n')
    return record

