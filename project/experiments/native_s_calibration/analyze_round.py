"""Audit complete-round evidence with fixed workload and bounded resources."""
import argparse
import base64
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import tarfile

TRACE = '6ed2129e2f13842dc53b4ba2135ea41886d1c126d842661dc7d5ac38ffb26f1d'


def analyze(directory):
    receipt = json.loads((directory / 'recovery.json').read_text())
    data = base64.b64decode(b''.join((directory / 'receipts.tar.gz.b64').read_bytes().split()), validate=True)
    assert hashlib.sha256(data).hexdigest() == receipt['receipts_archive_sha256']
    with tarfile.open(fileobj=io.BytesIO(data), mode='r:gz') as archive:
        files = {}
        for member in archive:
            assert member.isfile() and not PurePosixPath(member.name).is_absolute() and '..' not in PurePosixPath(member.name).parts
            files[member.name] = archive.extractfile(member).read()
    assert {k: hashlib.sha256(v).hexdigest() for k, v in files.items()} == receipt['members']
    rows = []
    for name, raw in sorted(files.items()):
        if not name.endswith('/report.json'):
            continue
        report = json.loads(raw)
        assert report['passed'] and not report.get('error'), (name, report.get('error'))
        assert report['input_trace_SHA256'] == TRACE
        assert len(report['affinity']) == 12
        assert [r['label'] for r in report['results']] == ['micro', 'decode512']
        result = report['results'][-1]['result']
        assert result['tokens'] == 1 and result['M_commands'] == 3028352
        assert result['read_bus_bytes'] == 3388365824
        assert result['logical_read_bytes'] == 3365952512
        assert result['logical_write_bytes'] == 8191232
        assert result['KV_state_write_bytes'] == 73728
        assert result['max_outstanding_beats'] <= 32
        assert result['max_outstanding_descriptors'] <= 32
        assert result['closure']['S_peak'] <= 16384
        ns = result['native_service']
        assert ns['max_W_banks'] <= 4 and ns['max_A_tiles'] <= 2 and ns['max_command_result_slots'] <= 2
        assert ns['RAW_groups'] == ns['RF_RNE_groups']
        if ns['static_M_records']:
            assert ns['RF_RNE_groups'] == ns['static_M_records'] + 7*(151936//8)*(2048//128)
        assert not ns['whole_system_calibrated'] and not ns['numerically_replayed']
        if ns['native_product_EOP_profile']:
            assert report['measured_quantizer_and_copy_selfcheck']
            assert ns['max_total_record_owners'] <= ns['record_owner_limit']
            assert ns['record_owner_limit'] in (4, 6) and ns['shared_S_owner_peak'] <= 2
            assert ns['scope_slots_per_P'] == 16
            if ns.get('G_next_projection_overlap_candidate'):
                assert ns['G_ring_peak_values'] <= 256 and ns['G_pending_group_limit'] == 2
                assert not ns['G_overlap_RTL_qualified']
        assert {'dynamic_layout1_2_S32xS32', 'E32_vector_services', 'N_full_S32_numeric_profile'} <= set(ns['unqualified'])
        channels = result['detail']['channels']
        assert sum(c['flows']['weight']['bus_read'] for c in channels) == 3298000896
        rows.append(dict(plan=report['plan'], tokens_s=result['tokens_per_second'],
                         cycles=result['ticks'], spans=result['spans_ticks'],
                         bus_read_B=result['read_bus_bytes'], logical_read_B=result['logical_read_bytes'],
                         bus_write_B=result['write_bus_bytes'], logical_write_B=result['logical_write_bytes'],
                         M_records=result['M_commands'], S_peak_B=result['closure']['S_peak'], native=ns,
                         env=report['source_env'], affinity=report['affinity']))
    assert len(rows) == 8
    assert len(set().union(*(set(r['affinity']) for r in rows))) == 96
    reference = next(r for r in rows if 'reference' in r['plan']) if any('reference' in r['plan'] for r in rows) else None
    # Historical-width references and guard0 lower bounds cannot satisfy the
    # new-native timing target by appearing as an otherwise faster table row.
    eligible = [r for r in rows if r['native']['level'] >= 3 and r['native']['guard_issue_sensitivity_cycles'] >= 3]
    if any(r['native']['native_product_EOP_profile'] for r in rows):
        eligible = [r for r in eligible if r['native']['native_product_EOP_profile']]
    if any(r['native'].get('M_profile_job') == 102202 for r in eligible):
        eligible = [r for r in eligible if r['native'].get('M_profile_job') == 102202]
    # New RF has a measured5-cycle guard handoff. Faster1/3-cycle rows are
    # explicit control candidates and cannot satisfy the current-service gate.
    if any(r['native'].get('M_profile_job') == 102228 for r in rows):
        eligible = [r for r in rows if r['native'].get('M_profile_job') == 102228 and r['native']['M_next_EXEC_gap_cycles'] >= 5]
    return dict(passed=True, job=receipt['job'], source_commit=receipt['source_commit'], rows=rows,
                reference=reference['plan'] if reference else None,
                best_tokens_s=max((r['tokens_s'] for r in eligible), default=None), target_tokens_s=9.21564723269,
                partial_timing_target_met=any(r['tokens_s'] >= 9.21564723269 for r in eligible),
                system_acceptance_met=False,
                qualification='partial calibrated timing model; not full numeric/RTL/control/physical system evidence')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', type=Path, required=True)
    args = parser.parse_args()
    result = analyze(args.run)
    (args.run / 'summary.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'rows'}))
