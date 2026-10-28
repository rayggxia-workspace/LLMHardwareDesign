"""Read-only old-final-source diagnosis under the selected new leaf budget.

Passing this task means the measurement completed, never that a revised macro
or the old source received 300 MHz or coarse-interface acceptance.
"""
import json
from pathlib import Path
import re


def screen(root,out,cpus,run,macro):
    from constraints import generate
    from io_slots import file_sha,slot
    from native_sta import inspect
    assert cpus==16 and macro in ('M','V','R','S','T')
    folder=root/'project/experiments/block_v1'
    d=json.loads((folder/'review-baseline-100mhz.json').read_text())['macros'][macro]
    budget=json.loads((folder/'physical-budget-300mhz.json').read_text())
    sdc=generate(budget)
    sdc=re.sub(r'create_clock -name core -period [^ ]+',
               'create_clock -name core -period %.12g'%budget['clock_ns'],sdc)
    (out/'input.sdc').write_text(sdc)
    sources={k:d['final_files'][k]for k in ('6_final.odb','6_final.spef')}
    for f in sources.values():
        assert Path(f['path']).stat().st_size==f['bytes']
        with slot(out.parents[2]):assert file_sha(Path(f['path']))==f['sha256']
    prefix='set ::env(BV1_ODB) {'+sources['6_final.odb']['path']+'}\n'
    prefix+='set ::env(BV1_SPEF) {'+sources['6_final.spef']['path']+'}\n'
    prefix+='set ::env(BV1_SDC) {'+str(out/'input.sdc')+'}\n'
    prefix+='source {'+str(folder/'native_sta.tcl')+'}\n'
    (out/'screen.tcl').write_text(prefix)
    run(['openroad','-no_init','-exit',out/'screen.tcl'],'screen.log')
    report=inspect(out)
    # Keep full endpoint diagnostics on the server, plus a compact summary.
    unused=report.pop('explicit_unused_internal_outputs')
    report['explicit_unused_internal_output_count']=len(unused)
    report['nonfinite_endpoint_count']=len(report['endpoints_without_finite_both_limits'])
    report['endpoints_without_finite_both_limits']=report['endpoints_without_finite_both_limits'][:32]
    for f in sources.values():
        with slot(out.parents[2]):assert file_sha(Path(f['path']))==f['sha256']
    result=dict(passed=True,macro=macro,baseline_commit='ad3c2b34511d58792ec5b550252590912f03252e',
                baseline_source_receipt_sha256=d['source_receipt_sha256'],source_files=sources,
                budget=budget,budget_sha256=file_sha(folder/'physical-budget-300mhz.json'),
                actual_sdc_sha256=file_sha(out/'input.sdc'),diagnostic=report,
                revised_leaf_qualified=False,coarse_interface_qualified=False,
                scope='Old sealed native geometry diagnosed at new300MHz/50fF contract, no optimizations. Task passed means measurement completed; passive input loads and all negative timing/electrical checks are retained, not waived. Revised RTL/final P&R remains required.')
    (out/'revision300-screen.json').write_text(json.dumps(result,indent=2)+'\n')
