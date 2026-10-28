"""Read-only output-load sensitivity on accepted leaves and actual P2 wires.

No new RTL/layout, no approved SDC mutation, no combined interface timing
qualification: series R, input wires, coupling and remote drivers stay separate.
"""
import json
import re
from pathlib import Path


def measure(root,out,cpus,run,kind,variant):
    from io_slots import file_sha
    from revision300_delivery import accepted
    from revision300_receive import source
    from constraint_readback import audit as constraints
    from native_passive_endpoint import audit as passive
    from native_annotation import inspect as annotation
    assert cpus==16 and kind in ('m','t') and variant in ('approved','base','high')
    index,odb,provenance,count,die=accepted(root,out,kind)
    folder,receipt,flow,results=source(root,out,kind)
    base=out.parents[2]
    escaped=base/('block-v1-20261029-'+('262'if kind=='m'else'261'))/'tasks'/('revision300-escape-'+kind)
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
    # Both current finite demonstrators use equal-length exits. Refuse a
    # future unequal design rather than quietly replacing it by an average.
    loads={n:50. if variant=='approved'else 2.+costs[n][variant+'_wire_cap_ff'] for n in outputs}
    assert len(set(loads.values()))==1
    load=next(iter(loads.values()))
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
    changed=''if variant=='approved'else 'set_load %.15g [all_outputs]\n'%load
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
    # Existing strict grammar expects four zero decimals on driver slew.
    # Normalize only exact zero tokens; all budget and slack checks unchanged.
    normalized=re.sub(r'(-input_transition_(?:rise|fall) )0\.0+(?= )',r'\g<1>0.0000',readback)
    budget=dict(flow['budget'],output_load_pf=load/1000.)
    boundary=constraints(normalized,plan,budget)
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
        timing=timing,annotation=rc,original_final_files_unchanged=True,
        combined_300mhz_interface_timing_qualified=False,calibrated_rc_qualified=False,
        scope='Same accepted native ODB/SDC/SPEF, output lumped-C sensitivity only. Base/high use actual P2 exit lengths and uncalibrated RC, plus2fF receiver; replace original50fF, do not double-count it. Series R/input/clock wires/coupling/remote driver timing not modeled. No new physical implementation or system qualification.')
    (out/'revision300-load.json').write_text(json.dumps(report,indent=2)+'\n')
