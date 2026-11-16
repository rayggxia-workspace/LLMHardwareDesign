"""Audit SystemC phase replays from exact, separately scoped RTL receipts."""
import argparse
import json
from pathlib import Path

from analyze_dynamic import TRACE
from analyze_native_dot import read_run
from audit_measured_ffn_replay import CLOCK, DDR, TARGET, ceildiv


FIXTURES=Path(__file__).with_name('fixtures')


def audits(run):
    receipt,files=read_run(run)
    assert receipt['job'] in ('102605','102612','102621')
    assert receipt['sacct'].splitlines()[0].split()[1:3]==['COMPLETED','0:0']
    assert receipt['allocation']=='c96 nodes=1 ntasks=8 cpus-per-task=12'
    fixtures=[json.loads((FIXTURES/name).read_text()) for name in (
        'ffn-three-p-102563-102564.json','ffn-programmed-102604-102603.json')]
    phases={p['job']:p for fixture in fixtures for p in fixture['profiles']}
    rows={}
    for path,raw in files.items():
        if not path.endswith('/report.json'):
            continue
        report=json.loads(raw)
        assert report['passed'] and report['job']==receipt['job'] and report['input_trace_SHA256']==TRACE
        assert len(set(report['affinity']))==12 and [r['label'] for r in report['results']]==['micro','decode512']
        result=report['results'][-1]['result']; env=report['source_env']; native=result['native_service']
        assert result['tokens']==1 and abs(1/result['seconds']-result['tokens_per_second'])<1e-8
        assert result['max_outstanding_descriptors']<=32 and result['max_outstanding_beats']<=32
        assert 0<=sum(result['spans_ticks'].values())-result['ticks']<=len(result['spans_ticks'])
        save=native['dynamic_s32_AV_S80_saves']; restore=native['dynamic_s32_AV_S80_restores']
        assert save==restore and save==(6912 if int(env['NS_DOT_AV_CKPT_PAIRS']) else 0)
        exact=env['NS_DOT_CKPT_MEASURED']=='1'
        rate=(81 if env['NS_DOT_PRESSURE']=='1' else 56) if exact else 62
        assert native['dynamic_s32_AV_S80_snapshot_service_cycles']==save*rate
        assert native['dynamic_s32_AV_S80_snapshot_S_words']==44*save
        assert native['dynamic_s32_AV_checkpoint_primitive_RTL_job']==(102600 if exact and save else 0)
        assert not native['dynamic_s32_AV_checkpoint_RTL_qualified']
        row=dict(cycles=result['ticks'],tokens_per_second=result['tokens_per_second'],S80_cycles=save*rate,
                 S80_save_count=save,S80_restore_count=restore,S80_RTL_job=native['dynamic_s32_AV_checkpoint_primitive_RTL_job'],
                 spans=result['spans_ticks'])
        ff=result.get('FFN_measured_replay')
        if receipt['job']=='102605':
            assert not ff and 'NS_PRODUCT' not in env
        else:
            assert ff and env['NS_PRODUCT']=='1'
            source=phases[ff['job']]
            sample,=(r for r in source['trials'] if (r['seed'],r['mode'],r['initial'])==(ff['seed'],ff['mode'],ff['initial']))
            assert ff['layers']==36 and ff['gate_cycles']==36*sample['gate'] and ff['down_cycles']==36*sample['down']
            if 'program' in source:
                assert ff['actual_programmed_DDR_read_bytes']==source['program']['confirmed_reads']*36
                assert ff['actual_programmed_calls']==source['program']['calls']*36
                assert ff['actual_programmed_local_write_receipt_bytes']==source['program']['confirmed_writes']*36
            measured=ff['gate_cycles']+ff['down_cycles']
            entry=ff['modeled_source_entry_cycles']; export=ff['modeled_result_export_cycles']
            other=ff['modeled_other_cycles']; floor=ceildiv(ff['actual_W_bus_bytes']*CLOCK,DDR)
            assert 0<=measured+entry+export+other-result['ticks']<=2
            assert TARGET-measured==ff['remaining_cycles_after_FFN_under_target']
            assert ff['actual_W_bus_bytes']==2_586_968_064 and ff['mixed_accounted_weight_bus_bytes']==3_298_000_896
            assert not ff['whole_hardware_calibrated'] and not ff['measured_interference_with_other_operators']
            dot_shapes={m['key']:m['wall_subcycles']/result['detail']['subcycles_per_core_cycle'] for m in result['detail']['matrix_shapes']}
            row.update(FFN=ff,measured_FFN_cycles=measured,conditional_FFN_wire_floor_cycles=floor,
                       ideal_FFN_same_residual_floor_cycles=floor+entry+export+other,
                       dot_kernel_cycles=dot_shapes,dot_dispatch_residual_cycles=row['spans']['Dot']-sum(dot_shapes.values()))
        rows[report['plan']]=row
    assert len(rows)==8
    if receipt['job']=='102612':
        assert rows['wave2-historical']['cycles']==50_335_005 and rows['wave2-measured-S80']['cycles']==50_319_310
        assert rows['wave2-pressure-historical']['cycles']==53_148_616 and rows['wave2-pressure-measured-S80']['cycles']==53_197_934
    if receipt['job']=='102621':
        assert rows['programmed-baseline']['cycles']==50_374_174
        assert rows['programmed-early']['cycles']==50_003_806
        assert rows['programmed-early-pressure']['cycles']==56_194_178
        assert rows['programmed-early']['FFN']['modeled_other_cycles']==19_163_655
    result=dict(job=receipt['job'],source_commit=receipt['source_commit'],trace_sha256=TRACE,
        receipts_archive_sha256=receipt['receipts_archive_sha256'],target_cycles=TARGET,rows=rows,
        comparable=receipt['job']!='102605',system_numeric_verified=False,system_physical_qualified=False,
        energy_calibrated=False,pure_dp_result=False,
        scope=('102605 omitted production profile flags and never activated measured FFN dispatch. Preserve as diagnostic.'
               if receipt['job']=='102605' else
               'Frozen full decode512 configuration trace. Measured FFN phase replay, optionally measured S80 primitive fees. Other modeled services and all contention boundaries separately labeled.'))
    (run/'audit.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--run',type=Path,required=True)
    result=audits(parser.parse_args().run)
    print(json.dumps(dict(job=result['job'],cycles={name:r['cycles'] for name,r in result['rows'].items()})))
