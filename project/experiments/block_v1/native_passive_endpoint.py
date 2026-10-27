"""Prove capacitive protection sinks are not setup/hold checks.

Diagnostic only: retain the original strict failure, original physical loads,
all actual data endpoints and all electrical/clock/count gates. No source edits.
"""
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import os


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def qualify(liberty):
    from native_cell_gate import group,attribute
    body=group(liberty,'cell','ANTENNA_X1')
    pins=re.findall(r'\bpin\s*\(\s*"?([A-Za-z_][A-Za-z_0-9]*)"?\s*\)',body)
    assert pins==['A']
    pin=group(body,'pin','A')
    assert attribute(pin,'direction')=='input'
    assert attribute(pin,'function',False)is None
    assert attribute(pin,'clock',False)in (None,'false')
    assert not re.search(r'\b(?:timing|ff|ff_bank|latch|latch_bank|statetable)\s*\(',body)
    cap=float(attribute(pin,'capacitance'));assert math.isfinite(cap)and cap>0
    return dict(master='ANTENNA_X1',signal_pin='A',direction='input',capacitance_ff=cap,
                no_timing_arcs=True,no_state=True,no_function=True,
                cell_body_sha256=hashlib.sha256(body.encode()).hexdigest())


def audit(folder,destination,liberty,inventory):
    """inventory is exact actual ODB instance/pin/master/root-net evidence."""
    from native_sta import inspect
    proof=qualify(liberty)
    assert inventory and all(row['master']=='ANTENNA_X1'and row['pin']=='A'and row['net']
                             and row['direction']=='INPUT'and row['type']=='CORE_ANTENNACELL'
                             for row in inventory.values())
    rows=(folder/'endpoints.tsv').read_text().splitlines();kept=[];removed={};reported=set()
    for line in rows:
        name,*values=line.split('\t');assert name not in reported and len(values)==5
        reported.add(name)
        if name in inventory:
            maximum,minimum,is_port,direction,fanout=values
            assert maximum in ('INF','-INF')and minimum in ('INF','-INF')
            assert is_port=='0'and direction=='input'and fanout=='0'
            removed[name]=inventory[name]
        else:kept.append(line)
    assert set(removed)==set(inventory),'Every qualified physical sink must occur exactly once'
    destination.mkdir(exist_ok=False)
    (destination/'endpoints.tsv').write_text('\n'.join(kept)+'\n')
    shutil.copyfile(folder/'timing-summary.tsv',destination/'timing-summary.tsv')
    strict=inspect(folder);timed=inspect(destination)
    assert timed['reported_endpoint_count']+len(removed)==strict['reported_endpoint_count']
    assert timed['native_summary']==strict['native_summary']and timed['electrical']==strict['electrical']
    assert timed['clocks']==strict['clocks']and timed['explicit_unused_internal_outputs']==strict['explicit_unused_internal_outputs']
    def compact(result):
        result=dict(result);unused=result.pop('explicit_unused_internal_outputs')
        result['explicit_unused_internal_output_count']=len(unused)
        result['explicit_unused_internal_outputs_sha256']=hashlib.sha256(json.dumps(unused,sort_keys=True).encode()).hexdigest()
        return result
    return dict(passed=timed['passed'],qualified_passive_count=len(removed),qualified_passive_sinks=removed,
                liberty=proof,original_strict=compact(strict),timed_endpoints=compact(timed),
                original_endpoints_sha256=sha(folder/'endpoints.tsv'),
                retained_endpoints_sha256=sha(destination/'endpoints.tsv'),
                timing_summary_sha256=sha(folder/'timing-summary.tsv'),
                scope='Diagnostic endpoint typing; no physical load removal or waiver of any data endpoint/electrical/clock/count gate')


def verify(root,out,cpus,run):
    base=out.parents[2];platform=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45')
    library=platform/'lib/NangateOpenCellLibrary_typical.lib';text=library.read_text();qualified=qualify(text)
    failed=base/'block-v1-20261027-120/tasks/native-diode2-receive-transaction6k-a'
    source=base/'block-v1-20261027-111/tasks/native-diode-run-transaction6k-a'
    receipt=json.loads((failed/'receipt.json').read_text());bound=json.loads((source/'receipt.json').read_text())
    assert receipt['passed']is False and bound['passed']is True
    for name in ['endpoints.tsv','timing-summary.tsv','physical-input-diodes.tsv','native-physical-receiver.json']:
        assert sha(failed/name)==receipt['outputs'][name]
    physical=json.loads((failed/'native-physical-receiver.json').read_text())
    assert physical['source']==str(source)and physical['source_receipt_sha256']==sha(source/'receipt.json')
    assert physical['checks']['all_input_diodes_preserved_on_exact_root_nets']
    odb=source/'flow/results/nangate45/bv1_transaction6k_A/base/6_final.odb'
    original=sha(odb);assert original==bound['outputs'][str(odb.relative_to(source))]
    # Get type, exact connected pin and root from the actual immutable database.
    script='read_db {%s}\nset s [open passive-inventory.tsv w]\n'%odb
    script+='''foreach inst [[ord::get_db_block] getInsts] {
  set master [$inst getMaster]
  if {[$master getName] ne "ANTENNA_X1"} {continue}
  foreach term [$inst getITerms] {
    set definition [$term getMTerm]
    if {[$definition getSigType] in {POWER GROUND}} {continue}
    set net [$term getNet]
    puts $s "[$inst getName]/[$definition getName]\\t[$master getName]\\t[$master getType]\\t[$definition getIoType]\\t[$net getName]"
  }
}
close $s
'''
    (out/'inventory.tcl').write_text(script);run(['openroad','-no_init','-exit','inventory.tcl'],'inventory.log')
    inventory={}
    for line in(out/'passive-inventory.tsv').read_text().splitlines():
        name,master,kind,direction,net=line.split('\t');assert name not in inventory
        inventory[name]=dict(master=master,type=kind,direction=direction,net=net,pin=name.rsplit('/',1)[1])
    roots=dict(line.split('\t')for line in(failed/'physical-input-diodes.tsv').read_text().splitlines())
    assert {name.rsplit('/',1)[0]:row['net']for name,row in inventory.items()}==roots
    actual=audit(failed,out/'actual-typed-endpoints',text,inventory)
    assert actual['passed']and len(inventory)==189
    # Real DFF plus real Liberty protection, then actual SDC faults. The SPEF
    # has both physical input loads; the sink is not removed from the design.
    control=base/'block-v1-20261027-066/tasks/native-sta-control/positive'
    top_receipt=json.loads((control.parent/'receipt.json').read_text());assert top_receipt['passed']is True
    for name in ['probe.sdc','probe.spef']:
        assert sha(control/name)==top_receipt['outputs']['positive/'+name]
    fixture={}
    for mode in ['positive','bad-capacitance','bad-setup','unconstrained-data']:
        folder=out/mode;folder.mkdir()
        (folder/'probe.v').write_text('module sta_probe(input clk,d,output q); DFF_X1 u0(.CK(clk),.D(d),.Q(q)); ANTENNA_X1 protect(.A(d)); endmodule\n')
        sdc=(control/'probe.sdc').read_text()
        if mode=='bad-capacitance':sdc=re.sub(r'set_load 2 ', 'set_load 1000 ',sdc)
        elif mode=='bad-setup':sdc=sdc.replace('-period 10 ','-period .1 ')
        elif mode=='unconstrained-data':sdc='\n'.join(line for line in sdc.splitlines()if not line.startswith('set_input_delay'))+'\n'
        (folder/'probe.sdc').write_text(sdc)
        spef=(control/'probe.spef').read_text().replace('*I u0:D I\n','*I u0:D I\n*I protect:A I\n')
        spef=spef.replace('2 u0:D 0.5\n*RES\n1 d u0:D .1\n','2 u0:D 0.25\n3 protect:A 0.25\n*RES\n1 d u0:D .1\n2 d protect:A .1\n')
        assert '*I protect:A I'in spef and '3 protect:A 0.25'in spef
        (folder/'probe.spef').write_text(spef)
        prepare='read_liberty {%s}\n'%library
        for name in ['NangateOpenCellLibrary.tech.lef','NangateOpenCellLibrary.macro.mod.lef']:prepare+='read_lef {%s}\n'%(platform/'lef'/name)
        prepare+='read_verilog {%s}\nlink_design sta_probe\nwrite_db {%s}\n'%(folder/'probe.v',folder/'probe.odb')
        (folder/'prepare.tcl').write_text(prepare)
        env=dict(os.environ,BV1_ODB=str(folder/'probe.odb'),BV1_SDC=str(folder/'probe.sdc'),BV1_SPEF=str(folder/'probe.spef'))
        for argv,log in [(['openroad','-no_init','-exit','prepare.tcl'],'prepare.log'),(['openroad','-no_init','-exit',str(root/'project/experiments/block_v1/native_sta.tcl')],'sta.log')]:
            with(folder/log).open('w')as stream:code=subprocess.run(argv,cwd=folder,env=env,stdout=stream,stderr=subprocess.STDOUT).returncode
            assert code==0,(mode,log)
        inv={'protect/A':dict(master='ANTENNA_X1',type='CORE_ANTENNACELL',direction='INPUT',pin='A',net='d')}
        fixture[mode]=audit(folder,out/(mode+'-typed'),text,inv)
        assert fixture[mode]['passed']==(mode=='positive'),mode
    faults={}
    from native_cell_gate import group
    body=group(text,'cell','ANTENNA_X1')
    pin=group(body,'pin','A')
    for name,changed in [('timing-arc',body+'\ntiming() {}\n'),('output',re.sub(r'(direction\s*:\s*)input',r'\1output',body)),
                         ('function',body.replace(pin,pin+'\nfunction : "A";\n')),('state',body+'\nff(IQ,IQN) {}\n')]:
        assert changed!=body
        bad=text.replace(body,changed);rejected=False
        try:qualify(bad)
        except AssertionError:rejected=True
        assert rejected,name;faults[name]=rejected
    assert sha(odb)==original
    for name in ['endpoints.tsv','timing-summary.tsv','physical-input-diodes.tsv','native-physical-receiver.json']:assert sha(failed/name)==receipt['outputs'][name]
    record=dict(schema='block-v1-passive-endpoint-probe/1',passed=True,actual=actual,fixtures=fixture,
                library_faults=faults,library_sha256=sha(library),source_odb_sha256=original,
                failed_receipt_sha256=sha(failed/'receipt.json'),qualified_library=qualified,
                qualified_hard_macro=False,scope='Endpoint type proof and actual-library fault controls only; source physical receiver remains failed with 23 DRC items')
    (out/'native-passive-endpoint-probe.json').write_text(json.dumps(record,indent=2)+'\n')
