"""Overlap real final-cell programs with independent remaining physical gates.

This does not qualify C or R PG. Final system acceptance must still compare
every actual final PG signal-view hash and the entire wired topology exactly.
"""
import json,os
from pathlib import Path
from r256_scene import SCHEMA,BASE
from r256_selection import REPLACEMENTS


def prepare(a,root,sha):
    assert os.environ.get('SLURM_JOB_ID')and len(os.sched_getaffinity(0))<=16
    a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=False)
    b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');inputs={}
    def read(p,expected=None):
        p=Path(p);digest=sha(p)
        if expected is not None:assert digest==expected,str(p)
        inputs[str(p)]=digest;return json.loads(p.read_text())
    receipt=dict(passed=False,inputs=inputs,whole_system_qualified=False,native_leaf_qualified=False)
    try:
        physical=read(b/'s-ready-composition-01/1391/selected/physical.json')
        functions=read(b/'s-ready-composition-01/1391/selected/functions.json')
        assert len(physical['leaves'])==len(functions['leaves'])==21
        for top in REPLACEMENTS:del physical['leaves'][top];del functions['leaves'][top]
        selected={
          'control_route_r8':b/'r256-fixed-pg-235/2292/delivery',
          'control_status_r8':b/'r256-fixed-pg-235/2294/delivery',
          'control_reset_distribution_r28':b/'r256-fixed-pg-235/2295/delivery',
          'control_s_arbiter_r7':b/'r256-fixed-pg-246/2333/delivery',
          'control_adapter_r':b/'r256-fixed-pg-254/2430/delivery'}
        for top,folder in selected.items():
            r=read(folder/'receipt.json');assert r['passed']and r['native_leaf_qualified']
            d=read(folder/'delivery.json',r['outputs']['delivery.json']);assert d['passed']and d['top']==top
            assert d['reused_function_and_strict_lec_via_exact_full_view_identity']
            physical['leaves'][top]=dict(final_files=d['final_files'],pins=str(folder/'pins.json'),pins_sha256=d['pins_sha256'],die_um=d['die_um'])
            report=folder/'final-function.json';f=read(report,r['outputs'][report.name]);assert f['passed']and f['full_final_netlist']['full_view_sha256']==d['full_final_netlist']['full_view_sha256']
            functions['leaves'][top]=dict(receipt=str(folder/'receipt.json'),receipt_sha256=sha(folder/'receipt.json'),report=str(report),report_sha256=sha(report))
        # All native C state/logic is from its actual finished P&R and passed
        # final-cell function gate, while its full GDS DRC runs independently.
        c=b/'r256-native-237/2371';producer=read(c/'native/receipt.json');assert producer['passed']and producer['native_pipeline_completed']and producer['top']=='control_c_r8'
        flow=read(c/'native/pnr/native-flow.json');assert flow['passed']and flow['pipeline_completed']
        gate=c/'gates/function';g=read(gate/'receipt.json');assert g['passed']
        report=gate/'final-function.json';f=read(report,g['outputs'][report.name]);assert f['passed']
        pins=c/'gates/sealed/pins.json'
        physical['leaves']['control_c_r8']=dict(final_files=flow['final_files'],pins=str(pins),pins_sha256=sha(pins),die_um=flow['die_um'])
        functions['leaves']['control_c_r8']=dict(receipt=str(gate/'receipt.json'),receipt_sha256=sha(gate/'receipt.json'),report=str(report),report_sha256=sha(report))
        rfolder=b/'r256-native-reuse-251';r=read(rfolder/'receipt.json');assert r['passed']and r['new_actual_complete_signal_view_export']
        row=read(rfolder/'physical.json',r['outputs']['physical.json'])['leaves']['r_stream_local']
        physical['leaves']['r_stream_local']=row
        gate=rfolder/'reused-gates/function';g=read(gate/'receipt.json');assert g['passed']
        report=gate/'final-function.json';f=read(report,g['outputs'][report.name]);assert f['passed']
        functions['leaves']['r_stream_local']=dict(receipt=str(gate/'receipt.json'),receipt_sha256=sha(gate/'receipt.json'),report=str(report),report_sha256=sha(report))
        assert set(physical['leaves'])==set(functions['leaves'])==set(BASE.values())|{'control_link8'}
        for data in [physical,functions]:data.update(scene=SCHEMA,inputs=inputs,candidate_for_function_only=True,whole_system_qualified=False,native_leaf_qualified=False)
        for name,data in [('physical.json',physical),('functions.json',functions)]:(a.out/name).write_text(json.dumps(data,indent=2)+'\n')
        receipt.update(passed=True,actual_final_function_types=23,remaining_independent_physical_gates=['C complete GDS DRC and fixed PG','R new fixed PG complete native/GDS/RC/300MHz'],scope='Actual final-cell function input assembly only. No new physical qualification; final collector requires exact final PG full-view and complete topology identity plus all unchanged physical gates.')
    finally:
        receipt['outputs']={p.name:sha(p)for p in a.out.iterdir()if p.is_file()}
        (a.out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
