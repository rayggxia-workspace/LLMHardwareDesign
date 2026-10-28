"""Zero-wire-delay diagnostic for the corrected V mapping, never acceptance."""
import json
from pathlib import Path


def diagnose(root,out,cpus,run):
    from io_slots import file_sha
    from constraints import generate
    assert cpus==16
    base=out.parents[2]
    source=base/'block-v1-20261029-289/tasks/revision300-map-v'
    receipt=json.loads((source/'receipt.json').read_text())
    assert receipt['passed'] and receipt['mode']==source.name
    report=source/'revision300-rtl-map.json'
    assert file_sha(report)==receipt['outputs'][report.name]
    mapping=json.loads(report.read_text());assert mapping['passed']
    for name,digest in mapping['rtl_sha256'].items():assert file_sha(root/name)==digest
    mapped=source/'mapped.v'
    assert file_sha(mapped)==mapping['mapped_sha256']==receipt['outputs']['mapped.v']
    liberty=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib')
    assert file_sha(liberty)==mapping['liberty_sha256']
    budget=json.loads((root/'project/experiments/block_v1/physical-budget-300mhz.json').read_text())
    sdc=generate(budget).replace('create_clock -name core -period %g'%budget['clock_ns'],
                               'create_clock -name core -period %.12g'%budget['clock_ns'])
    (out/'input.sdc').write_text(sdc)
    script='read_liberty {'+str(liberty)+'}\nread_verilog {'+str(mapped)+'}\n'
    script+='link_design '+mapping['top']+'\nread_sdc {'+str(out/'input.sdc')+'}\n'
    script+='report_checks -path_delay max -group_path_count 30 -format full_clock_expanded -fields {slew cap fanout input_pin net} -digits 9\n'
    script+='report_worst_slack -max -digits 9\nreport_tns -digits 9\n'
    script+='puts BV1_ZERO_WIRE_DIAGNOSTIC_COMPLETE\n'
    (out/'diagnostic.tcl').write_text(script)
    run(['openroad','-no_init','-exit',out/'diagnostic.tcl'],'diagnostic.log')
    assert 'BV1_ZERO_WIRE_DIAGNOSTIC_COMPLETE' in (out/'diagnostic.log').read_text()
    assert file_sha(mapped)==mapping['mapped_sha256']
    result=dict(passed=True,source_mapping_receipt_sha256=file_sha(source/'receipt.json'),
        mapped_sha256=mapping['mapped_sha256'],rtl_sha256=mapping['rtl_sha256'],
        budget=budget,diagnostic_log_sha256=file_sha(out/'diagnostic.log'),
        physical_implementation_completed=False,qualified_hard_macro=False,
        scope='Diagnostic only: mapped combinational cell delay with ideal clock and zero wire RC. Negative slack is retained, not waived; positive slack grants no physical timing qualification.')
    (out/'revision300-v-map-timing.json').write_text(json.dumps(result,indent=2)+'\n')
