"""Offline read-only audit; never runs the service model."""
import argparse
import json
from pathlib import Path, PurePosixPath
import tarfile


def analyze(path):
    with tarfile.open(path, 'r:gz') as archive:
        members = archive.getmembers()
        assert all(m.isfile() and not PurePosixPath(m.name).is_absolute() and
                   '..' not in PurePosixPath(m.name).parts for m in members)
        files = {m.name: archive.extractfile(m).read() for m in members}
    rows = []
    for name, raw in sorted(files.items()):
        if not name.endswith('/report.json'):
            continue
        report = json.loads(raw)
        assert report['passed'] and not report.get('error')
        assert [r['label'] for r in report['results']] == ['micro', 'decode512']
        result = report['results'][-1]['result']
        rows.append(dict(plan=report['plan'], tokens_s=result['tokens_per_second'],
                         core_cycles=result['ticks'], spans_cycles=result['spans_ticks'],
                         bus_read_B=result['read_bus_bytes'], logical_read_B=result['logical_read_bytes'],
                         bus_write_B=result['write_bus_bytes'], M_commands=result['M_commands'],
                         trace_sha256=report['input_trace_SHA256'], env=report['source_env']))
    assert len(rows) == 8
    for key in ('bus_read_B', 'logical_read_B', 'bus_write_B', 'M_commands', 'trace_sha256'):
        assert len({r[key] for r in rows}) == 1, key
    row = {r['plan']: r for r in rows}
    assert abs(row['legacy-Xreg']['tokens_s'] - 9.21564723269) < 1e-10
    assert abs(row['legacy-NoPool']['tokens_s'] - 9.2237871361) < 1e-10
    historical = row['legacy-Xreg']['tokens_s']
    native = row['all128-NoPool']['tokens_s']
    return dict(passed=True, rows=rows,
                native_improvement_over_same_native_Xreg_percent=100 * (native / row['all128-Xreg']['tokens_s'] - 1),
                native_change_from_historical_target_percent=100 * (native / historical - 1),
                historical_target_met=native >= historical,
                qualification='port sensitivity, not full RTL calibration, numeric execution or physical acceptance')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--receipts', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    value = analyze(args.receipts)
    args.out.write_text(json.dumps(value, indent=2) + '\n')
    print(json.dumps({k: v for k, v in value.items() if k != 'rows'}))
