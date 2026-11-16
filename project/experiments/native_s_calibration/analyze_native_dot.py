"""Read back the exact full-decode native-dot comparison and its failed first run."""
import argparse
import base64
import hashlib
import io
import json
from pathlib import Path
import tarfile

from analyze_dynamic import TRACE


def digest(data):
    return hashlib.sha256(data).hexdigest()


def files_in(data):
    with tarfile.open(fileobj=io.BytesIO(data), mode='r:gz') as archive:
        return {item.name: archive.extractfile(item).read() for item in archive if item.isfile()}


def read_run(directory):
    info = json.loads((directory / 'recovery.json').read_text())
    receipts = base64.b64decode(b''.join((directory / 'receipts.tar.gz.b64').read_bytes().split()), validate=True)
    source = (directory / 'source.tar.gz').read_bytes()
    assert digest(receipts) == info['receipts_archive_sha256']
    assert digest(source) == info['source_archive_sha256']
    files = files_in(receipts)
    assert {name: digest(data) for name, data in files.items()} == info['members']
    sources = files_in(source)
    for line in sources['source.sha256'].decode().splitlines():
        expected, name = line.split('  ', 1)
        assert digest(sources[name]) == expected
    return info, files


def analyze(directory):
    info, files = read_run(directory)
    job=int(info['job'])
    assert job in (102434, 102443, 102476, 102482, 102496, 102557)
    repaired = job != 102434
    rows = []
    for name, data in sorted(files.items()):
        if not name.endswith('/report.json'):
            continue
        report = json.loads(data)
        assert report['input_trace_SHA256'] == TRACE and len(report['affinity']) == 12
        placeholder = report['plan'] == 'native32-placeholder-reference'
        assert report['passed'] == (placeholder or repaired)
        if not report['passed']:
            assert 'CalledProcessError(1,' in report['error']
            rows.append(dict(plan=report['plan'], passed=False, error=report['error']))
            continue
        result = report['results'][-1]['result']
        assert report['results'][-1]['label'] == 'decode512' and result['tokens'] == 1
        assert result['logical_write_bytes'] == 8191232 and result['KV_state_write_bytes'] == 73728
        assert result['max_outstanding_beats'] <= 32 and result['max_outstanding_descriptors'] <= 32
        assert result['closure']['S_peak'] <= 16384
        assert sum(c['flows']['weight']['bus_read'] for c in result['detail']['channels']) == 3298000896
        ns = result['native_service']
        env = report['source_env']
        m2_records = ns.get('M2_short_guard_candidate_EXECs', 0)
        expected_ffn = 18625835
        if m2_records:
            assert job in (102496,102557) and m2_records == 3013376 and not ns['M2_short_guard_P2_qualified']
            expected_ffn = 17103730 if report['plan'].endswith('first-DDR-offer') else 17072934
        assert result['spans_ticks']['FFN_closure'] == expected_ffn
        assert ns['new_local_SRAM_B'] == 0 and ns['dynamic_partials'] == 0
        assert ns['max_W_banks'] <= 4 and ns['max_A_tiles'] <= 2 and ns['max_command_result_slots'] <= 2
        assert not ns['whole_system_calibrated'] and not ns['numerically_replayed'] and not ns['physical_system_qualified']
        assert ns['dynamic_s32_enabled'] != placeholder
        if placeholder:
            assert result['ticks'] == 36872345
        else:
            assert ns['dynamic_s32_MACs'] == 75497472 and ns['dynamic_s32_calls'] == 216
            stage = env.get('NS_DOT_STAGE64') == '1'
            assert ns['dynamic_s32_RTL_job'] == (102510 if env.get('NS_DOT_REFILL_NEXT')=='1' else 102444 if stage else 102419)
            assert ns['dynamic_s32_peak_raw_slots'] <= 6 and ns['dynamic_s32_S_peak_B'] <= 16384
            assert ns['dynamic_s32_result_write_ACKs'] == ns['dynamic_s32_export_read_words']
            assert not ns['dynamic_s32_production_source_and_LC_qualified'] and not ns['dynamic_s32_physical_qualified']
            if stage:
                assert ns['dynamic_s32_stage_RTL_job'] == 102473
                assert max(ns['dynamic_s32_landing_peak_by_channel']) <= 3
                assert ns['dynamic_s32_landing_B'] == ns['dynamic_s32_read_bus_B']
            if int(env.get('NS_DOT_AV_CKPT_PAIRS', '0')):
                assert ns['dynamic_s32_AV_checkpoint_candidate'] and not ns['dynamic_s32_AV_checkpoint_RTL_qualified']
                saves = ns['dynamic_s32_AV_S80_saves']
                assert saves == ns['dynamic_s32_AV_S80_restores'] == 36*2*16*2*3
                assert ns['dynamic_s32_AV_S80_snapshot_S_words'] == 2*22*saves
                assert ns['dynamic_s32_AV_paired_DDR_beats'] == 36*2*8*512
        rows.append(dict(plan=report['plan'], passed=True, ticks=result['ticks'],
                         token_per_second=result['tokens_per_second'],
                         DDR_read_bus_B=result['read_bus_bytes'], DDR_logical_read_B=result['logical_read_bytes'],
                         spans=result['spans_ticks'], M2_candidate_EXECs=m2_records,
                         dynamic={k.removeprefix('dynamic_s32_'): v for k, v in ns.items() if k.startswith('dynamic_s32_')}))
    assert len(rows) == 8
    plans = {r['plan']: r for r in rows}
    result = dict(passed=True, job=info['job'], source_commit=info['source_commit'], trace_SHA256=TRACE,
                  receipt_archive_SHA256=info['receipts_archive_sha256'], rows=rows,
                  meets_9_215647_target=False, whole_system_calibrated=False,
                  energy_qualified=False, added_SRAM_B=0)
    if job == 102443:
        cold = plans['native32-16lane-staged']
        reused = plans['native32-16lane-AB-resident']
        best = plans['native32-16lane-AB-two-raw-slots']
        assert best['ticks'] == 42263912 and best['dynamic']['S_peak_B'] == 12672
        assert best['dynamic']['read_bus_B'] == 98795520 and best['dynamic']['peak_raw_slots'] == 6
        result['R4_same_one_raw_slot_residency_throughput_gain'] = cold['ticks'] / reused['ticks'] - 1
        result['R4_same_one_raw_slot_residency_cycle_reduction'] = 1 - reused['ticks'] / cold['ticks']
    elif job == 102476:
        old = plans['old-stage-16lane-AB-two-slots']
        cold = plans['stage64-16lane-cold-two-slots']
        reused = plans['stage64-16lane-AB-two-slots']
        assert old['ticks'] == 42263912
        result['R4_same_two_raw_slot_residency_throughput_gain'] = cold['ticks']/reused['ticks']-1
        result['R4_same_two_raw_slot_residency_cycle_reduction'] = 1-reused['ticks']/cold['ticks']
    elif job == 102482:
        serial = plans['stage64-serial-AV-reference']
        wave = plans['AV-S80-pair-wave2']
        result['candidate_two_pair_vs_serial_AV_full_throughput_gain'] = serial['ticks']/wave['ticks']-1
        result['candidate_snapshot_qualification'] = 'Sensitivity only; exact S80 snapshot and B stride4 need RTL/physical validation.'
    elif job == 102496:
        serial = plans['single-M-wave-AV-reference']
        m2 = plans['M2-guard15-wave-AV']
        assert serial['ticks'] == 38497905 and m2['ticks'] == 36670196
        assert plans['M2-guard15-wave-AV-first-DDR-offer']['ticks'] == 36697961
        result['candidate_M2_throughput_gain_at_same_AV_wave'] = serial['ticks']/m2['ticks']-1
        result['candidate_M2_qualification'] = 'Isolated actual issuer/guard2 timing, not sustained wide P coordination. See wide-P actual DDR trace audit.'
    elif job == 102557:
        for kind, old_ticks, new_ticks in (('serial',39910050,39492506),('wave',36670196,36252284)):
            old=plans[f'old-{kind}-AV'];new=plans[f'refill-{kind}-AV']
            assert old['ticks']==old_ticks and new['ticks']==new_ticks
            assert old['DDR_read_bus_B']==new['DDR_read_bus_B'] and old['spans']['FFN_closure']==new['spans']['FFN_closure']
            result[f'{kind}_AV_same_work_refill_cycle_reduction']=1-new_ticks/old_ticks
        result['qualification']='The S128 refill fee is measured in 102510. Non-FFN and formerly modeled FFN results are diagnostic; 102563/102564 now supersede the FFN estimate.'
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', required=True, type=Path)
    args = parser.parse_args()
    result = analyze(args.run)
    (args.run / 'native-dot-audit.json').write_text(json.dumps(result, indent=2) + '\n',newline='\n')
    print(json.dumps(dict(job=result['job'], rows=[(r['plan'], r.get('token_per_second')) for r in result['rows']])))
