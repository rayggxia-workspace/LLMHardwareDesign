"""Fresh P&R from an exact verified mapping; does not rerun passed RTL tests."""
import argparse,json,os,subprocess,sys,time
from pathlib import Path
from types import SimpleNamespace
from run import sha
def main():
    p=argparse.ArgumentParser();p.add_argument('--source-root',type=Path,required=True)
    p.add_argument('--verified',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--failed-producer-hold-budget',action='store_true',help='Reuse only successful RTL/mapping of exact retained R256 CTS RSZ-0060 failure; all physical/final gates rerun')
    p.add_argument('--verified-source-root',type=Path,help='Exact immutable source of reused RTL/mapping; only the new run.py dispatch may differ')
    p.add_argument('--r256-escape-drc',type=Path,help='Exact retained two-spacing R adapter failure; repair only rsp_data419/429 before fresh final extraction')
    p.add_argument('--strong-output-drivers',action='store_true');a=p.parse_args()
    assert os.environ.get('SLURM_JOB_ID') and len(os.sched_getaffinity(0))<=16
    a.out.mkdir(parents=True,exist_ok=False)
    r=json.loads((a.verified/'receipt.json').read_text());assert r['rtl_passed'] and len(r['runs'])==3
    if a.failed_producer_hold_budget:
        assert not r['passed']and not r.get('native_pipeline_completed')and a.strong_output_drivers
        assert r['top']in ('control_adapter_r','control_s_arbiter_r7')and r['mapped']['passed']and r['mapped']['mapped']
        last=r['commands'][-1];assert last['returncode']==2 and 'do-cts'in last['command']
        log=a.verified/last['log'];assert sha(log)==last['sha256']
        assert '[ERROR RSZ-0060] Max buffer count reached.'in log.read_text()
    else:assert r['passed']
    oldsource=a.verified_source_root or a.source_root
    for name,digest in r['source_sha256'].items():
        assert sha(oldsource/name)==digest
        if name!='project/experiments/control_v1/run.py'or not a.verified_source_root:assert sha(a.source_root/name)==digest
    if a.verified_source_root:
        assert oldsource.resolve().parent==a.source_root.resolve().parent
        source_manifest=json.loads((oldsource/'source-manifest.json').read_text())
        assert all(source_manifest['files'][name]==digest for name,digest in r['source_sha256'].items())
    receipt=dict(passed=False,rtl_passed=True,top=r['top'],source_sha256=r['source_sha256'],runs=r['runs'],mapped=r['mapped'],
        verified_producer=str(a.verified),verified_receipt_sha256=sha(a.verified/'receipt.json'),commands=[])
    # Gate runners bind the exact source which performed the reused tests,
    # rather than attributing those old executions to a newer dispatch file.
    if a.verified_source_root:receipt['verified_rtl_source_root']=str(oldsource)
    if a.r256_escape_drc:
        assert a.failed_producer_hold_budget and r['top']=='control_adapter_r'
        failed=json.loads((a.r256_escape_drc/'receipt.json').read_text());assert failed['passed']is False
        prior=Path(failed['producer']);pr=json.loads((prior/'receipt.json').read_text())
        assert pr['passed']and pr['native_pipeline_completed']and pr['top']==r['top']
        assert pr['mapped']==r['mapped']and pr['source_sha256']==r['source_sha256']
        assert failed['producer_receipt_sha256']==sha(prior/'receipt.json')
        report=a.r256_escape_drc/'native-whole-drc.rpt'
        assert sha(report)==failed['outputs'][report.name]=='a5d6dfd98e85db7e809ff950a2aaa76dbaca56b82867acd5d72a5ee0d65975ff'
        text=report.read_text();assert text.count('violation type: Metal Spacing')==text.count('on Layer metal10')==2
        receipt['retained_escape_failure']=dict(receipt=str(a.r256_escape_drc/'receipt.json'),sha256=sha(a.r256_escape_drc/'receipt.json'),report_sha256=sha(report),targets=['rsp_data[419]','rsp_data[429]'])
    if a.failed_producer_hold_budget:
        hook=a.source_root/'project/experiments/control_v1/r256_hold_budget.tcl'
        receipt['failed_hold_budget_retry']=dict(original_physical_failed=True,only_rtl_and_mapping_reused=True,
            previous_error='RSZ-0060',hook=str(hook),hook_sha256=sha(hook),all_physical_and_final_gates_required=True)
    try:
        sys.path.insert(0,str(a.source_root/'project/experiments/block_v2'));import physical
        out=a.out/'pnr';out.mkdir()
        args=SimpleNamespace(out=out,top=r['top'],mapping=a.verified/'mapping',input_receivers=True,
            remove_abc_buffers=False,placement_mode='timing',fanout_mode='original',r_compact_floorplan=False,
            r_strong_clock=False,refine_partition_placement=False,placement_hold_margin=None,hold_repair_margin=0.015 if r['top']=='control_d' else 0.0)
        args.strong_output_drivers=a.strong_output_drivers
        if a.r256_escape_drc:args.control_escape_repair=['rsp_data[419]','rsp_data[429]']
        def run(command,log):
            command=list(map(str,command));start=time.time()
            with (out/log).open('w') as f:q=subprocess.run(command,cwd=out,stdout=f,stderr=subprocess.STDOUT)
            receipt['commands'].append(dict(command=command,log='pnr/'+log,sha256=sha(out/log),returncode=q.returncode,seconds=time.time()-start))
            assert q.returncode==0,(log,q.returncode)
        physical.implement(args,run);receipt['passed']=True;receipt['native_pipeline_completed']=True
    finally:(a.out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
if __name__=='__main__':main()
