"""Failure-only lower bound: actual boundary input cells plus native/wire CAP.

The smallest declared Liberty pin capacitance is conservative here. Missing
capacitance contributes zero. Detours, vias and coupling remain omitted; this
diagnostic never qualifies geometry or timing.
"""
import json,math,re,subprocess,sys
from pathlib import Path


def minimum_pin_cap(values):
    values=[float(v)for v in values if v is not None]
    assert all(math.isfinite(v)and v>=0 for v in values)
    return min(values)if values else 0.


def loads(graph,inventories,pin_cap):
    result={}
    for bit,row in graph['connections'].items():
        cells={}
        for end in [row['driver'],*row['sinks']]:
            instance=end['instance']
            if instance=='TOP':continue
            top=graph['instances'][instance]
            for cell,master,pin in inventories[top][end['pin']]:
                key=(instance,cell,pin)
                assert cells.setdefault(key,(master,pin))==(master,pin)
        result['net_'+bit]=dict(minimum_input_pin_cap_ff=sum(pin_cap(*v)for v in cells.values()),actual_input_pin_count=len(cells))
    return result


def inspect(manifest_path,graph_path,residual_path,out,bind):
    def read(path):
        path=Path(path);bind(path);return json.loads(path.read_text())
    manifest=read(manifest_path);graph=read(graph_path);residual=read(residual_path)
    assert graph['passed']and residual['passed']and not residual['whole_system_qualified']
    proof=read(Path(residual_path).parent/'receipt.json');assert proof['passed']
    bind(residual_path,proof['outputs'][Path(residual_path).name])
    for p in [manifest_path,graph_path]:bind(p,proof['inputs'][str(p)])
    native=Path(__file__).resolve().parents[1]/'block_v1';sys.path.insert(0,str(native))
    from native_cell_gate import group,attribute
    bind(native/'native_cell_gate.py')
    lib=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib');bind(lib);text=lib.read_text()
    assert re.search(r'capacitive_load_unit\s*\(\s*1\s*,\s*ff\s*\)',text,re.I)
    cache={}
    def pin_cap(master,pin):
        key=master,pin
        if key not in cache:
            body=group(group(text,'cell',master),'pin',pin)
            assert attribute(body,'direction')=='input'
            cache[key]=minimum_pin_cap([attribute(body,n,False)for n in ['capacitance','rise_capacitance','fall_capacitance']])
        return cache[key]
    inventories={}
    for top,row in manifest['leaves'].items():
        entry=row['final_files']['6_final.odb'];bind(entry['path'],entry['sha256'])
        folder=out/top;folder.mkdir();table=folder/'pins.tsv'
        script='set_thread_count 16\nread_db {'+entry['path']+'}\nset f [open {'+str(table)+'} w]\n'+r'''
foreach port [[ord::get_db_block] getBTerms] {
 if {[$port getSigType] in {POWER GROUND}} {continue}
 set net [$port getNet];if {$net eq "NULL"} {error "Disconnected actual boundary"}
 puts $f "PORT\t[$port getName]"
 foreach term [$net getITerms] {
  set pin [$term getMTerm]
  if {[$pin getSigType] in {POWER GROUND}} {continue}
  if {[$pin getIoType] ne "INPUT"} {continue}
  set inst [$term getInst]
  puts $f "PIN\t[$port getName]\t[$inst getName]\t[[$inst getMaster] getName]\t[$pin getName]"
 }
}
close $f
'''
        path=folder/'inventory.tcl';path.write_text(script)
        with (folder/'inventory.log').open('w')as log:subprocess.run(['openroad','-no_init','-exit',path],stdout=log,stderr=subprocess.STDOUT,check=True)
        bind(entry['path'],entry['sha256'])
        for p in [path,table,folder/'inventory.log']:bind(p)
        inventory={}
        for line in table.read_text().splitlines():
            parts=line.split('\t')
            if parts[0]=='PORT':
                assert len(parts)==2 and parts[1]not in inventory;inventory[parts[1]]=[]
            else:
                assert parts[0]=='PIN'and len(parts)==5
                inventory[parts[1]].append(tuple(parts[2:]))
        inventories[top]=inventory
    caps=loads(graph,inventories,pin_cap);placements=[]
    for placement in residual['placements']:
        rows=[]
        for row in placement['rows']:
            c=caps[row['net']];totals={k:v+c['minimum_input_pin_cap_ff']for k,v in row['optimistic_total_ff'].items()}
            rows.append(dict(row,**c,optimistic_total_with_minimum_pin_ff=totals,minimum_pin_bound_violates={k:v>row['max_capacitance_ff']+1e-9 for k,v in totals.items()}))
        placements.append(dict(placement=placement['placement'],violations={k:sum(r['minimum_pin_bound_violates'][k]for r in rows)for k in ['low','base','high']},rows=rows))
    return dict(passed=True,diagnostic_executed=True,whole_system_qualified=False,placements=placements,liberty_minimum_pin_cap_ff={m+'/'+p:c for(m,p),c in cache.items()},scope='Actual final ODB boundary input pins deduplicated by physical instance/pin, minimum declared Liberty capacitance plus exact native ground CAP and optimistic upper HPWL. Failure-only lower bound; zero violations never grants physical/timing qualification.')
