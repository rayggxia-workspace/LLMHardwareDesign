"""Portable source-gate and real subprocess controls; no EDA qualification."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import native_view_group as group
from native_views import received_contract


def verify(destination):
    assert not destination.exists()
    # Explicit fixture only. It does not impersonate a successful EDA receipt.
    checks=dict.fromkeys(['timing','rc_coverage','mapped_to_final_lec','unplaced_zero','all_pg_iterms_correct',
        'pg_vdd','pg_vss','open_signal_inputs_zero','exact_prefabricated_m10_pins','undriven_used_signal_nets_zero',
        'exact_native_layers','same_die','core_inside_die','active_cell_area_within_cap','independent_native_drc_zero','native_drt_drc_zero'],True)
    positive=dict(passed=True,checks=checks,historical_input_contract=False,top='shared109',policy='A',
        pipeline='native_pipeline_const_protected.json',source='fixture-source',source_receipt_sha256='fixture-digest',
        independent_drc_items=0,rc_coverage_qualified=True,mapped_to_final_lec=dict(passed=True))
    def receive(proof):received_contract(proof,Path('fixture-source'),'fixture-digest','native_pipeline_const_protected.json','shared109','A')
    receive(positive)
    faults={'failed':dict(passed=False),'empty-gates':dict(checks={}),
        'nonboolean-gate':dict(checks=dict(checks,timing=1)),'failed-extra-gate':dict(checks=dict(checks,extra=False)),
        'historical':dict(historical_input_contract=True),'wrong-leaf':dict(top='transaction6k'),
        'wrong-policy':dict(policy='C'),'wrong-pipeline':dict(pipeline='native_pipeline_viaonly.json'),
        'wrong-source':dict(source='other-source'),'wrong-receipt':dict(source_receipt_sha256='other-digest'),
        'drc-marker':dict(independent_drc_items=1),'rc-unqualified':dict(rc_coverage_qualified=False),
        'formal-failed':dict(mapped_to_final_lec=dict(passed=False))}
    for name,change in faults.items():
        value=copy.deepcopy(positive);value.update(change);rejected=False
        try:receive(value)
        except AssertionError:rejected=True
        assert rejected,name
    stub='''import hashlib,json,sys,time
from pathlib import Path
mode=sys.argv[2];started=time.time();time.sleep(.7)
top,policy=mode.removeprefix('native-prefab-view-').rsplit('-',1)
passed=mode!=FAIL_MODE
path=Path('native-view-generation.json');path.write_text(json.dumps(dict(passed=passed,top=top,policy=policy.upper())))
Path('receipt.json').write_text(json.dumps(dict(mode=mode,cpus=int(sys.argv[3]),passed=passed,started=started,finished=time.time(),outputs={path.name:hashlib.sha256(path.read_bytes()).hexdigest()})))
sys.exit(0 if passed else 1)
'''
    original=group.memory_snapshot;cases={}
    try:
        with tempfile.TemporaryDirectory()as temporary:
            for name,failure,available,parallel in [('four',None,1000,4),('two',None,500,2),('one',None,200,1),
                ('failed-peer','native-prefab-view-transaction6k-c',1000,4)]:
                base=Path(temporary)/name;root=base/'src';worker=root/'project/experiments/block_v1/worker.py'
                worker.parent.mkdir(parents=True);worker.write_text('FAIL_MODE='+repr(failure)+'\n'+stub)
                out=base/'tasks/native-prefab-view-group';out.mkdir(parents=True)
                group.memory_snapshot=lambda:dict(MemTotal=1024*1024**3,MemAvailable=available*1024**3)
                rejected=False
                try:group.verify(root,out,32)
                except AssertionError:rejected=True
                result=json.loads((out/'native-view-group.json').read_text());children=result['children']
                assert result['simultaneous_workers']==parallel and result['maximum_concurrent_cpu_ceilings']==8*parallel
                assert rejected==(failure is not None)and result['passed']==(failure is None)
                assert len(children)==4 and sum(c['passed']for c in children)==(4 if failure is None else 3)
                assert all(c['receipt_sha256']and c['proof_sha256']for c in children)
                receipts=[json.loads((out.parent/c['mode']/'receipt.json').read_text())for c in children]
                overlap=max(sum(r['started']<=at<r['finished']for r in receipts)for at in [r['started']for r in receipts])
                assert overlap==parallel
                cases[name]=dict(passed=True,actual_stub_process_overlap=overlap,parent_rejected=rejected,retained_child_receipts=len(children))
    finally:group.memory_snapshot=original
    report=dict(passed=True,source_gate_positive_fixture=True,rejected_source_faults=sorted(faults),subprocess_controls=cases,
        source_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest()for p in [Path(__file__),Path(group.__file__),Path(__file__).with_name('native_views.py')]},
        scope='Explicit synthetic provenance fixtures and actual stub processes with injected memory snapshots only. No actual candidate view, EDA qualification, peak RAM or utilization proof.')
    destination.parent.mkdir(parents=True,exist_ok=True);destination.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(passed=True,rejected_source_faults=len(faults),actual_stub_cases=len(cases))))


if __name__=='__main__':
    parser=argparse.ArgumentParser(__doc__);parser.add_argument('out',type=Path);verify(parser.parse_args().out)
