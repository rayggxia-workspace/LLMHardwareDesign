"""Read-only output-load sensitivity on accepted leaves and actual P2 wires.

No new RTL/layout, no approved SDC mutation, no combined interface timing
qualification: series R, input wires, coupling and remote drivers stay separate.
"""
import json
from pathlib import Path


def serialization_reference(root,out,run,sdc,load):
    """Same-tool tiny fixture, exact tokens and actual wrong-load control."""
    from revision300_constraints_control import serialization
    from revision300_constraint_readback import audit
    tools=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45')
    fixture=out/'load-fixture.v'
    fixture.write_text('module revision300_load_fixture(input clk,d,output q); DFF_X1 ff(.CK(clk),.D(d),.Q(q)); endmodule\n')
    prefix=''.join('read_lef {'+str(tools/'lef'/name)+'}\n'for name in
        ('NangateOpenCellLibrary.tech.lef','NangateOpenCellLibrary.macro.mod.lef'))
    prefix+='read_liberty {'+str(tools/'lib/NangateOpenCellLibrary_typical.lib')+'}\n'
    prefix+='read_verilog {'+str(fixture)+'}\nlink_design revision300_load_fixture\n'
    (out/'load-fixture.sdc').write_text(sdc)
    refs={}
    for label,value in [('positive',load),('wrong-load',load+1.)]:
        script=prefix+'read_sdc {'+str(out/'load-fixture.sdc')+'}\nset_load %.15g [all_outputs]\n'%value
        script+='write_sdc -no_timestamp -digits 12 {'+str(out/(label+'-reference.sdc'))+'}\n'
        (out/(label+'-reference.tcl')).write_text(script)
        run(['openroad','-no_init','-exit',out/(label+'-reference.tcl')],label+'-reference.log')
        refs[label]=serialization((out/(label+'-reference.sdc')).read_text())
    assert {k:v for k,v in refs['positive'].items()if k!='output_load_ff'}=={k:v for k,v in refs['wrong-load'].items()if k!='output_load_ff'}
    assert refs['positive']['output_load_ff']!=refs['wrong-load']['output_load_ff']
    budget=json.loads((root/'project/experiments/block_v1/physical-budget-300mhz.json').read_text())
    budget['output_load_pf']=load/1000.
    pins=[dict(pin='clk',direction='input'),dict(pin='d',direction='input'),dict(pin='q',direction='output')]
    audit((out/'positive-reference.sdc').read_text(),pins,budget,refs['positive'])
    try:audit((out/'wrong-load-reference.sdc').read_text(),pins,budget,refs['positive'])
    except AssertionError:pass
    else:raise AssertionError('Actual wrong output load accepted')
    return refs['positive']


def measure(root,out,cpus,run,kind,variant):
    from io_slots import file_sha
    from revision300_delivery import accepted
    from revision300_receive import source
    from revision300_constraint_readback import audit as constraints
    from native_passive_endpoint import audit as passive
    from native_annotation import inspect as annotation
    assert cpus==16 and kind in 'mvrst' and len(kind)==1 and variant in ('approved','base','high')
    index,odb,provenance,count,die=accepted(root,out,kind)
    folder,receipt,flow,results=source(root,out,kind)
    base=out.parents[2]
    from revision300_interface_source import selected
    escaped=selected(root,out,kind)
    er=json.loads((escaped/'receipt.json').read_text())
    assert er['passed'] and er['mode']==escaped.name
    ep=escaped/'revision300-escape.json'
    assert file_sha(ep)==er['outputs'][ep.name]
    escape=json.loads(ep.read_text())
    assert escape['passed'] and escape['all_signal_bits']==count
    assert escape['source_odb_sha256']==index['final_files']['6_final.odb']['sha256']
    assert escape['source_delivery']==provenance
    plan=json.loads((folder/'pins.json').read_text())['pins']
    outputs={p['pin']for p in plan if p['direction']=='output'}
    costs={p['net']:p for p in escape['early_rc_costs']}
    assert set(costs)=={p['pin']for p in plan} and outputs
    loads={n:50. if variant=='approved'else 2.+costs[n][variant+'_wire_cap_ff'] for n in outputs}
    uniform=len(set(loads.values()))==1
    load=next(iter(loads.values())) if uniform else None
    physical=Path(index['gate_receipts']['physical']['report_path']).parent
    pr=json.loads((physical/'receipt.json').read_text())
    inv=physical/'passive-inventory.tsv'
    assert file_sha(inv)==pr['outputs'][inv.name]
    inventory={}
    for line in inv.read_text().splitlines():
        name,master,typ,direction,net=line.split('\t')
        assert name not in inventory
        inventory[name]=dict(master=master,type=typ,direction=direction,net=net,pin=name.rsplit('/',1)[1])
    tools=root/'project/experiments/block_v1'
    original=(tools/'native_sta.tcl').read_text()
    anchor='read_sdc $::env(BV1_SDC)\n'
    assert original.count(anchor)==1
    changed=''if variant=='approved'else ''.join(
        'set_load %.15g [get_ports {%s}]\n'%(value,name) for name,value in sorted(loads.items()))
    body=original.replace(anchor,anchor+changed)
    # Keep the helper's own source-relative annotation lookup bound to the
    # unchanged committed helper, not to this generated task directory.
    lookup='[file join [file dirname [info script]] native_annotation.tcl]'
    assert body.count(lookup)==1
    body=body.replace(lookup,'{'+str(tools/'native_annotation.tcl')+'}')
    prefix=''.join('set ::env('+k+') {'+str(results/name)+'}\n'for k,name in
        [('BV1_ODB','6_final.odb'),('BV1_SDC','6_final.sdc'),('BV1_SPEF','6_final.spef')])
    prefix+='rename write_sdc bv1_original_write_sdc\nproc write_sdc {args} {uplevel 1 [list bv1_original_write_sdc -digits 12 {*}$args]}\n'
    (out/'load-sta.tcl').write_text(prefix+body)
    run(['openroad','-no_init','-exit',out/'load-sta.tcl'],'load-sta.log')
    readback=(out/'constraints-readback.sdc').read_text()
    if uniform:
        budget=dict(flow['budget'],output_load_pf=load/1000.)
        reference=serialization_reference(root,out,run,(results/'6_final.sdc').read_text(),load)
        boundary=constraints(readback,plan,budget,reference)
    else:
        reference,boundary=per_port_reference(root,out,run,(results/'6_final.sdc').read_text(),
                                            readback,plan,flow['budget'],loads)
    lib=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib')
    timing=passive(out,out/'timed-endpoints',lib.read_text(),inventory)
    rc=annotation(out)
    assert rc['passed']
    if variant=='approved':
        assert timing['passed'],'Accepted baseline must independently reproduce'
    # Sensitivity may legitimately expose violations: keep them, never use
    # experiment completion as a claim that its loaded timing passed.
    for name,row in index['final_files'].items():
        assert file_sha(Path(row['path']))==row['sha256']
    report=dict(schema='revision300-output-load-sensitivity/1',passed=True,macro=kind.upper(),variant=variant,
        experiment_completed=True,loaded_native_sta_passed=timing['passed'],source_delivery=provenance,
        source_odb_sha256=file_sha(odb),source_sdc_sha256=file_sha(results/'6_final.sdc'),
        source_spef_sha256=file_sha(results/'6_final.spef'),source_escape_receipt_sha256=file_sha(escaped/'receipt.json'),
        source_escape_report_sha256=file_sha(ep),approved_budget_unchanged=True,output_count=len(outputs),
        applied_output_load_ff=load,receiver_ff=2.,load_by_port_ff=loads,constraint_readback=boundary,
        native_serialization_reference=reference,actual_wrong_load_negative_rejected=True,
        timing=timing,annotation=rc,original_final_files_unchanged=True,
        combined_300mhz_interface_timing_qualified=False,calibrated_rc_qualified=False,
        scope='Same accepted native ODB/SDC/SPEF, output lumped-C sensitivity only. Base/high use actual P2 exit lengths and uncalibrated RC, plus2fF receiver; replace original50fF, do not double-count it. Series R/input/clock wires/coupling/remote driver timing not modeled. No new physical implementation or system qualification.')
    (out/'revision300-load.json').write_text(json.dumps(report,indent=2)+'\n')


def per_port_reference(root,out,run,sdc,readback,plan,budget,loads):
    """Bind each unequal load to same-tool serialization; preserve all other audits."""
    import re
    from decimal import Decimal
    from revision300_constraint_readback import audit
    reference=serialization_reference(root,out,run,sdc,50.)
    values=sorted(set(loads.values()))
    tools=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45')
    fixture=out/'load-map-fixture.v'
    names=['q%d'%i for i in range(len(values))]
    fixture.write_text('module revision300_load_map(input clk,d,output '+','.join(names)+');\n'+
        ''.join('DFF_X1 f%d(.CK(clk),.D(d),.Q(%s));\n'%(i,n)for i,n in enumerate(names))+'endmodule\n')
    prefix=''.join('read_lef {'+str(tools/'lef'/name)+'}\n'for name in
        ('NangateOpenCellLibrary.tech.lef','NangateOpenCellLibrary.macro.mod.lef'))
    prefix+='read_liberty {'+str(tools/'lib/NangateOpenCellLibrary_typical.lib')+'}\n'
    prefix+='read_verilog {'+str(fixture)+'}\nlink_design revision300_load_map\n'
    grammar=r'set_load -pin_load (\S+) \[get_ports \{([^}]+)\}\]'
    def tokens(text):
        result={}
        for line in text.splitlines():
            if line.startswith('set_load '):
                m=re.fullmatch(grammar,line);assert m, line
                token,name=m.groups();assert name not in result;result[name]=token
        return result
    observed={}
    for label in ('positive','wrong-load'):
        script=prefix+'create_clock -name core -period 3.333333333333 [get_ports clk]\n'
        script+=''.join('set_load %.15g [get_ports {%s}]\n'%(v+(1. if label=='wrong-load'and i==0 else 0.),n)
                        for i,(n,v) in enumerate(zip(names,values)))
        script+='write_sdc -no_timestamp -digits 12 {'+str(out/('map-'+label+'.sdc'))+'}\n'
        (out/('map-'+label+'.tcl')).write_text(script)
        run(['openroad','-no_init','-exit',out/('map-'+label+'.tcl')],'map-'+label+'.log')
        observed[label]=tokens((out/('map-'+label+'.sdc')).read_text())
        assert set(observed[label])==set(names)
    assert observed['positive'][names[0]]!=observed['wrong-load'][names[0]]
    assert all(observed['positive'][n]==observed['wrong-load'][n]for n in names[1:])
    value_tokens=dict(zip(values,[observed['positive'][n]for n in names]))
    expected={n:value_tokens[v]for n,v in loads.items()}
    def checked(text,expected_tokens):
        actual=tokens(text);assert set(actual)==set(loads)
        assert all(Decimal(actual[n])==Decimal(expected_tokens[n])for n in actual)
        normalized=[]
        for line in text.splitlines():
            if line.startswith('set_load '):
                match=re.fullmatch(grammar,line)
                line='set_load -pin_load '+reference['output_load_ff']+' [get_ports {'+match.group(2)+'}]'
            normalized.append(line)
        result=audit('\n'.join(normalized)+'\n',plan,dict(budget,output_load_pf=.05),reference)
        result.update(output_load_ff=None,per_port_load_ff=loads,per_port_native_tokens=actual,
                      exact_per_port_load_coverage=True)
        return result
    boundary=checked(readback,expected)
    wrong=dict(expected)
    first=next(n for n,v in loads.items()if v==values[0])
    wrong[first]=observed['wrong-load'][names[0]]
    try:checked(readback,wrong)
    except AssertionError:pass
    else:raise AssertionError('Actual single-port wrong load accepted')
    return dict(uniform_reference=reference,per_port_native_tokens=expected,
                actual_single_port_wrong_load_rejected=True),boundary
