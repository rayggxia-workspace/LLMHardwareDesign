"""Verify captured FFN phases against frozen SystemC reports and the target budget."""
import argparse
import json
from pathlib import Path

from analyze_dynamic import TRACE
from analyze_native_dot import read_run


TARGET = 32_553_329
CLOCK = 300_000_000
DDR = 51_200_000_000
FIXTURE = Path(__file__).with_name('fixtures')/'ffn-three-p-102563-102564.json'


def ceildiv(n,d):
    return (n+d-1)//d


def audit(directory):
    receipt,files=read_run(directory)
    assert receipt['job']=='102589' and receipt['allocation']=='c96 nodes=1 ntasks=8 cpus-per-task=12'
    assert receipt['sacct'].splitlines()[0].split()[1:3]==['COMPLETED','0:0']
    fixture=json.loads(FIXTURE.read_text())
    rows={}
    for name,raw in files.items():
        if not name.endswith('/report.json'):
            continue
        report=json.loads(raw)
        assert report['passed'] and report['job']==receipt['job'] and report['input_trace_SHA256']==TRACE
        assert report['round']=='measured-three-P-FFN' and len(set(report['affinity']))==12
        assert [r['label'] for r in report['results']]==['micro','decode512']
        result=report['results'][-1]['result']
        assert result['tokens']==1 and result['max_outstanding_descriptors']<=32 and result['max_outstanding_beats']<=32
        assert result['KV_state_write_bytes']==73728
        assert -.001<=result['ticks']-CLOCK*result['seconds']<=1.001
        assert abs(1/result['seconds']-result['tokens_per_second'])<1e-8
        row=dict(cycles=result['ticks'],tokens_per_second=result['tokens_per_second'])
        ff=result.get('FFN_measured_replay')
        if ff:
            profile,=(p for p in fixture['profiles'] if p['job']==ff['job'])
            sample,=(r for r in profile['trials'] if (r['seed'],r['mode'],r['initial'])==(ff['seed'],ff['mode'],ff['initial']))
            assert ff['layers']==36 and ff['gate_cycles']==36*sample['gate'] and ff['down_cycles']==36*sample['down']
            measured=ff['gate_cycles']+ff['down_cycles']
            boundaries=ff['modeled_source_entry_cycles']+ff['modeled_result_export_cycles']
            assert ff['actual_W_bus_bytes']==2_586_968_064 and ff['mixed_accounted_weight_bus_bytes']==3_298_000_896
            assert 0<=measured+boundaries-result['spans_ticks']['FFN_closure']<=1
            assert 0<=measured+boundaries+ff['modeled_other_cycles']-result['ticks']<=2
            assert ff['remaining_cycles_after_FFN_under_target']==TARGET-measured
            assert not ff['whole_hardware_calibrated'] and not ff['measured_interference_with_other_operators']
            minimum_ffn=ceildiv(ff['actual_W_bus_bytes']*CLOCK,DDR)
            same_other=ff['modeled_other_cycles']+boundaries
            row.update(ff, measured_FFN_total_cycles=measured, modeled_entry_exit_plus_other_cycles=same_other,
                       FFN_weight_only_cycles_floor=minimum_ffn,
                       ideal_FFN_same_residual_cycles_floor=minimum_ffn+same_other,
                       ideal_FFN_required_other_reduction=max(0,minimum_ffn+same_other-TARGET))
        else:
            assert report['plan'].startswith('prior-modeled')
            row['prior_modeled_FFN_cycles']=result['spans_ticks']['FFN_closure']
        rows[report['plan']]=row
    assert len(rows)==8
    assert rows['measured-four-W-wave-AV']['cycles']==rows['measured-four-W-median-FFN-wave-AV']['cycles']==50_335_005
    assert rows['measured-four-W-serial-AV']['cycles']==53_575_227
    assert rows['measured-serial-serial-AV']['cycles']==78_222_303
    assert rows['measured-four-W-all-pressure']['cycles']==56_336_884
    return dict(job=receipt['job'],source_commit=receipt['source_commit'],trace_SHA256=TRACE,
                receipt_SHA256=receipt['receipts_archive_sha256'],target_cycles=TARGET,
                rows=rows,scope=fixture['boundary'],energy_estimated=False,pure_DP_result=False,
                whole_model_hardware_qualified=False,
                systemc_phase_replay='Observed Gate/Up→Mid and Down phase time. Source entry, result export and other operators separately modeled.')


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--run',type=Path,required=True)
    a=p.parse_args()
    result=audit(a.run)
    (a.run/'measured-ffn-audit.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
