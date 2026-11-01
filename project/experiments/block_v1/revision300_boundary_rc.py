"""Finite all-port pi-RC timing sensitivity on unchanged accepted leaves."""
import json
import math
from pathlib import Path


def control(root,out,cpus,run):
    from revision300_boundary_spef import fixtures,augment,digest
    assert cpus==16
    structural=fixtures(out/'structural')
    verilog=out/'fixture.v'
    verilog.write_text('module revision300_rc_fixture(input clk,d,output q); DFF_X1 ff(.CK(clk),.D(d),.Q(q)); endmodule\n')
    sdc=out/'fixture.sdc'
    sdc.write_text('''create_clock -name clk -period 3.333333333333333 [get_ports clk]
set_clock_uncertainty 0.1 [get_clocks clk]
set_clock_transition 0.05 [get_clocks clk]
set_input_delay -clock clk -min 0.2 [get_ports d]
set_input_delay -clock clk -max 0.8 [get_ports d]
set_output_delay -clock clk -min 0.2 [get_ports q]
set_output_delay -clock clk -max 0.8 [get_ports q]
set_driving_cell -lib_cell BUF_X2 [get_ports d]
set_load 2 [get_ports q]
''')
    native=out/'structural/fixture.spef';observed={}
    for label in ('native','positive','huge-r','huge-c'):
        costs={p:dict(wire_cap_ff=20,series_r_ohm=10)for p in ('clk','d','q')}
        if label=='huge-r':costs['d']['series_r_ohm']=1000000
        if label=='huge-c':costs['d']['wire_cap_ff']=2000
        spef=native
        if label!='native':
            spef=out/(label+'.spef');augment(native,spef,costs)
        platform=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45')
        script=''.join('read_lef {'+str(platform/'lef'/n)+'}\n'for n in ('NangateOpenCellLibrary.tech.lef','NangateOpenCellLibrary.macro.mod.lef'))
        script+='read_liberty {'+str(platform/'lib/NangateOpenCellLibrary_typical.lib')+'}\n'
        script+='read_verilog {'+str(verilog)+'}\nlink_design revision300_rc_fixture\n'
        script+='read_sdc {'+str(sdc)+'}\nread_spef {'+str(spef)+'}\nset_propagated_clock [all_clocks]\nsta::find_timing\n'
        script+='set f [open {'+str(out/(label+'-endpoints.tsv'))+'} w]\n'
        script+='''foreach pin [sta::endpoints] {
 set fanout 0
 foreach reached [get_fanout -from [list $pin] -flat -pin_levels 2 -trace_arcs all] {
  if {$reached ne $pin} {incr fanout}
 }
 puts $f "[get_full_name $pin]\\t[get_property $pin slack_max]\\t[get_property $pin slack_min]\\t$fanout"
}
close $f
'''
        script+='report_parasitic_annotation -report_unannotated\nreport_checks -path_delay min_max -format full_clock_expanded -digits 12\n'
        p=out/(label+'.tcl');p.write_text(script);run(['openroad','-no_init','-exit',p],label+'.log')
        values={};unused={}
        for line in (out/(label+'-endpoints.tsv')).read_text().splitlines():
            name,setup,hold,fanout=line.split('\t');pair=[float(setup),float(hold)]
            if name=='ff/QN':
                assert setup==hold=='INF'and int(fanout)==0
                unused[name]=dict(setup=setup,hold=hold,fanout=int(fanout))
            else:
                assert all(math.isfinite(v)for v in pair);values[name]=pair
        assert set(values)=={'ff/D','q'}and set(unused)=={'ff/QN'}
        observed[label]=dict(endpoints=values,unused_fixture_qn=unused,spef_sha256=digest(spef))
    positive=observed['positive']['endpoints']['ff/D'][0]
    assert observed['huge-r']['endpoints']['ff/D'][0]<positive-1
    assert observed['huge-c']['endpoints']['ff/D'][0]<positive-.01
    assert observed['native']['endpoints']!=observed['positive']['endpoints']
    report=dict(passed=True,actual_openroad_spef_consumer_control=True,structural=structural,
        observed=observed,huge_resistance_negative_rejected=True,huge_capacitance_negative_rejected=True,
        scope='Real tiny DFF timing consumer controls; not native macro or process qualification.')
    (out/'revision300-boundary-rc-control.json').write_text(json.dumps(report,indent=2)+'\n')


def measure(root,out,cpus,run,kind,variant):
    from io_slots import file_sha
    from revision300_delivery import accepted
    from revision300_receive import source
    from revision300_load import serialization_reference
    from revision300_constraint_readback import audit as constraints
    from native_passive_endpoint import audit as passive
    from native_annotation import inspect as annotation
    from revision300_boundary_spef import augment
    assert cpus==16 and kind in 'mvrst' and len(kind)==1 and variant in ('base','high')
    base=out.parents[2]
    controls=out.parent/'revision300-boundary-rc-control'
    if kind in 'svr':
        controls=qualified_shared_control(root,base)
    cr=json.loads((controls/'receipt.json').read_text());assert cr['passed']
    cp=controls/'revision300-boundary-rc-control.json';assert file_sha(cp)==cr['outputs'][cp.name]
    assert json.loads(cp.read_text())['actual_openroad_spef_consumer_control']
    index,odb,provenance,count,die=accepted(root,out,kind)
    folder,receipt,flow,results=source(root,out,kind)
    from revision300_interface_source import selected
    escaped=selected(root,out,kind)
    er=json.loads((escaped/'receipt.json').read_text());assert er['passed']
    ep=escaped/'revision300-escape.json';assert file_sha(ep)==er['outputs'][ep.name]
    escape=json.loads(ep.read_text());assert escape['source_delivery']==provenance and escape['all_signal_bits']==count
    assert escape['source_odb_sha256']==index['final_files']['6_final.odb']['sha256']
    plan=json.loads((folder/'pins.json').read_text())['pins']
    costs={p['net']:dict(wire_cap_ff=p[variant+'_wire_cap_ff'],series_r_ohm=p['base_series_r_ohm']*(1.5 if variant=='high'else 1.))for p in escape['early_rc_costs']}
    assert set(costs)=={p['pin']for p in plan}
    modified=out/'boundary.spef';proof=augment(results/'6_final.spef',modified,costs)
    assert proof['port_count']==count and 'clk'in proof['ports']
    for p in plan:assert proof['ports'][p['pin']]['direction']==p['direction'][0].upper()
    physical=Path(index['gate_receipts']['physical']['report_path']).parent
    pr=json.loads((physical/'receipt.json').read_text());inv=physical/'passive-inventory.tsv'
    assert file_sha(inv)==pr['outputs'][inv.name]
    inventory={}
    for line in inv.read_text().splitlines():
        name,master,typ,direction,net=line.split('\t');assert name not in inventory
        inventory[name]=dict(master=master,type=typ,direction=direction,net=net,pin=name.rsplit('/',1)[1])
    tools=root/'project/experiments/block_v1';body=(tools/'native_sta.tcl').read_text()
    anchor='read_sdc $::env(BV1_SDC)\n';assert body.count(anchor)==1
    body=body.replace(anchor,anchor+'set_load 2 [all_outputs]\n')
    lookup='[file join [file dirname [info script]] native_annotation.tcl]';assert body.count(lookup)==1
    body=body.replace(lookup,'{'+str(tools/'native_annotation.tcl')+'}')
    files={'BV1_ODB':odb,'BV1_SDC':results/'6_final.sdc','BV1_SPEF':modified}
    prefix=''.join('set ::env('+k+') {'+str(p)+'}\n'for k,p in files.items())
    prefix+='rename write_sdc bv1_original_write_sdc\nproc write_sdc {args} {uplevel 1 [list bv1_original_write_sdc -digits 12 {*}$args]}\n'
    (out/'interface-sta.tcl').write_text(prefix+body)
    run(['openroad','-no_init','-exit',out/'interface-sta.tcl'],'interface-sta.log')
    reference=serialization_reference(root,out,run,(results/'6_final.sdc').read_text(),2.)
    boundary=constraints((out/'constraints-readback.sdc').read_text(),plan,dict(flow['budget'],output_load_pf=.002),reference)
    lib=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib')
    timing=passive(out,out/'timed-endpoints',lib.read_text(),inventory);rc=annotation(out);assert rc['passed']
    for key,row in index['final_files'].items():assert file_sha(Path(row['path']))==row['sha256']
    report=dict(schema='revision300-boundary-pi-sensitivity/1',passed=True,experiment_completed=True,
        macro=kind.upper(),variant=variant,source_delivery=provenance,source_escape_receipt_sha256=file_sha(escaped/'receipt.json'),
        control_receipt_sha256=file_sha(controls/'receipt.json'),all_input_output_clock_pi_rc=proof,
        receiver_load_ff=2,approved_budget_and_final_files_unchanged=True,
        declared_pi_boundary_sta_passed=timing['passed'],timing=timing,annotation=rc,constraint_readback=boundary,
        combined_system_timing_qualified=False,calibrated_12layer_rc_qualified=False,
        scope='All actual P2 signal exits including inputs/output/clock modeled as series-R/two-half-C pi, native extracted coupling retained. Approved I/O delays now refer to declared virtual outside boundary; data BUF_X2 source and ideal clock transition unchanged;2fF receiver replaces50fF, avoiding double counting. High uses1.5x R/C as an explicit uncalibrated sensitivity. New-layer coupling/remote driver implementation/array/manufacturing are not qualified. Timing failures remain failures, no constraint relaxation or source change.')
    (out/'revision300-boundary-rc.json').write_text(json.dumps(report,indent=2)+'\n')


def qualified_shared_control(root,base):
    """Reuse the actual 287 consumer controls only with identical control code/tool."""
    import shutil
    from io_slots import file_sha
    folder=base/'block-v1-20261029-287'
    controls=folder/'tasks/revision300-boundary-rc-control'
    rp=controls/'receipt.json'
    assert file_sha(rp)=='dae552951665422d08aed4dbdc6088f951c38385734ebf00655fe4d2af346e1e'
    receipt=json.loads(rp.read_text())
    assert receipt['passed'] and receipt['mode']==controls.name
    assert receipt['source_commit']=='b217f8bf3ff68ab91109ff9a0aeb552dd6166f88'
    state=json.loads((folder/'node-queue-state.json').read_text())
    assert state['tasks'][controls.name]['status']=='PASSED'
    relative='project/experiments/block_v1/'
    old=folder/'src'/relative/'revision300_boundary_rc.py'
    assert file_sha(old)==receipt['inputs'][relative+'revision300_boundary_rc.py']
    # measure() is extended for three other leaves; the entire actual control
    # function and its imports above measure() must remain byte-identical.
    separator=b'\ndef measure('
    assert old.read_bytes().split(separator)[0]==Path(__file__).read_bytes().split(separator)[0]
    for name in ['revision300_boundary_spef.py','io_slots.py']:
        assert file_sha(root/relative/name)==receipt['inputs'][relative+name]
    tool=Path(shutil.which('openroad')).resolve()
    assert file_sha(tool)==receipt['tool_hashes'][str(tool)]
    for name,digest in receipt['outputs'].items():
        assert file_sha(controls/name)==digest
    report=json.loads((controls/'revision300-boundary-rc-control.json').read_text())
    assert report['passed'] and report['actual_openroad_spef_consumer_control']
    assert report['huge_resistance_negative_rejected'] and report['huge_capacitance_negative_rejected']
    return controls
