"""Independent finite-credit/address/bandwidth audit of generated width models.

The original Fraction oracle, all 725 numerical outputs and ten negative Pool
controls are retained. Only its C++ consumer-segment bound is widened; the old
single-issue timing checker is replaced with the explicit physical audit below.
"""
import argparse
from collections import defaultdict
from copy import deepcopy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import random
import signal
import subprocess
import sys
import traceback

HERE = Path(__file__).resolve().parent
FROZEN = {'numeric_check.py': '09edbb06851f162a22cb191e367a507e379fdc96617018a520b387f23df21453',
          'numeric_reference.py': '243d609190800373819ad3d2f22cde4743c2f26ccfdf4f533772b9c2b769c916'}
C = 1000


def need(ok, message):
    if not ok:
        raise AssertionError(message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def group(address, groups, mapping):
    return 0 if groups == 1 else (address >> (14 if mapping == 'contiguous' else 6)) & 1


def audit_events(events, values, width, groups, mapping, legacy, require_selection=True):
    """Derive service intervals and byte ownership from immutable observations.

    Callback print order is NOT chronological: an issue may be printed at its
    retirement. Credits therefore use sorted actual issue timestamps, while
    ownership is checked by unique (case,worker,tile,physical line).
    """
    specs = {v['id']: v for v in values}
    begin, end, tiles, finished = {}, {}, {}, {}
    issues, consumes, selects = defaultdict(list), defaultdict(list), defaultdict(list)
    epochs = {}
    for e in events:
        cid, kind = e['case'], e['kind']
        need(cid in specs, 'unknown input case')
        if kind == 'begin':
            need(cid not in begin, 'duplicate begin')
            v = specs[cid]
            whole = ((v['k'] * 4 + 63) // 64) * 64
            prefix = v['k'] if whole * v['rows'] <= v['capacity_bytes'] else (v['capacity_bytes'] // v['rows'] // 4 // 256) * 256
            stride = ((prefix * 4 + 63) // 64) * 64
            need(e['prefix_k'] == prefix and e['stride'] == stride, 'capacity/stride changed')
            need(v['rows'] * stride <= v['capacity_bytes'], 'physical capacity overflow')
            epoch_key = (v['capacity_bytes'], v['fifo_beats']) if legacy else cid
            need(e['epoch'] == epochs.get(epoch_key, 0) + 1, 'generation/epoch mismatch')
            epochs[epoch_key] = e['epoch']; begin[cid] = e
        elif kind == 'end':
            need(cid not in end, 'duplicate object end'); end[cid] = e
        elif kind in ('tile', 'endtile'):
            key = (cid, e['worker'], e['tile'])
            target = tiles if kind == 'tile' else finished
            need(key not in target, 'duplicate tile boundary'); target[key] = e
        elif kind in ('issue', 'consume', 'select'):
            {'issue': issues, 'consume': consumes, 'select': selects}[kind][(cid, e['worker'], e['tile'])].append(e)
        else:
            raise AssertionError('unknown event ' + kind)
    need(set(begin) == set(end) == set(specs), 'missing object lifecycle')
    need(set(tiles) == set(finished) and set(issues) <= set(tiles) and set(consumes) <= set(tiles) and set(selects) <= set(tiles), 'orphan/missing tile')
    services, credit_events = [], defaultdict(list)
    per_cycle = defaultdict(lambda: [0, set()])
    chosen_packets = defaultdict(lambda: [0, set(), set(), set()])
    per_issue_cycle = defaultdict(int)
    per_case_service = defaultdict(list)
    delivered = total_reads = peak = 0
    for key, t in tiles.items():
        cid, worker, tid = key; v = specs[cid]; b = begin[cid]
        need(worker in (0, 1) and 0 <= t['start'] < v['k'] and t['count'] > 0 and t['start'] + t['count'] <= v['k'], 'tile range')
        if legacy:
            need((t['col'] // 16) % 2 == worker, 'wrong output ownership')
        row_start, rows = t.get('row_start', 0), t.get('rows', v['rows'])
        wanted = {(r, k) for r in range(row_start, row_start + rows)
                  for k in range(t['start'], min(t['start'] + t['count'], b['prefix_k']))}
        seen = set(); read_by_line = {}; consumed_by_line = defaultdict(list)
        choices = {}
        for e in selects[key]:
            choice_key = (e['pool'], e['bytes'], e['ready'])
            need(choice_key not in choices and e['epoch'] == b['epoch'], 'duplicate/invalid selection event')
            need(e['ready'] <= e['chosen'] and e['chosen'] % C == 0, 'future unreturned line selected')
            choices[choice_key] = e
        for e in issues[key]:
            need(e['epoch'] == b['epoch'] and 0 < e['bytes'] <= 64 and e['pool'] % 64 + e['bytes'] <= 64, 'invalid read extent/epoch')
            line = e['pool'] // 64
            need(line not in read_by_line, 'same tile reread without a distinct request identity')
            read_by_line[line] = e
            start, stop = e['ready'] - 3 * C, e['ready'] - 2 * C
            need(start >= e['issued'] >= b['time'] and stop - start == C, 'bank service/latency before issue or fill')
            need(e['issued'] % C == start % C == stop % C == 0, 'probe service not core-cycle aligned')
            g = group(e['pool'], groups, mapping)
            services.append((start, stop, g, cid, worker, tid, line))
            per_case_service[cid].append((start, stop, g, worker))
            credit_events[(cid, worker)].append(e)
            per_issue_cycle[(cid, worker, e['issued'])] += 1
            total_reads += 1
        for e in consumes[key]:
            need(e['epoch'] == b['epoch'] and 0 < e['bytes'] <= min(64, width) and e['bytes'] % 4 == 0, 'consumer segment width/epoch')
            need(e['source'] % 4 == 0 and e['pool'] % 64 + e['bytes'] <= 64, 'consumer crosses physical line or S32 element')
            need(row_start <= e['row'] < row_start + rows, 'consumer row ownership')
            offset = e['source'] - 4096 - e['row'] * v['k'] * 4
            need(offset >= 0 and offset % 4 == 0, 'source address alignment')
            ki = offset // 4
            need(e['pool'] == e['row'] * b['stride'] + ki * 4, 'source-to-pool address mismatch')
            line = e['pool'] // 64
            need(line in read_by_line, 'consume without physical read')
            req = read_by_line[line]
            need(req['pool'] <= e['pool'] and e['pool'] + e['bytes'] <= req['pool'] + req['bytes'], 'consume outside returned valid mask')
            need(e['ready'] == req['ready'] and e['consumed'] >= e['ready'] + C and e['consumed'] % C == 0, 'consume before response or core edge')
            for k in range(ki, ki + e['bytes'] // 4):
                element = (e['row'], k)
                need(element in wanted and element not in seen, 'duplicate or out-of-range consumed byte')
                seen.add(element)
            consumed_by_line[line].append(e)
            packet = per_cycle[(cid, worker, e['consumed'])]
            packet[0] += e['bytes']; packet[1].add(line)
            if require_selection:
                chosen = choices.pop((e['pool'], e['bytes'], e['ready']), None)
                need(chosen is not None and chosen['row'] == e['row'] and e['consumed'] >= chosen['chosen'] + C,
                     'missing selection proof or consume before selection')
                batch = chosen_packets[(cid, worker, chosen['chosen'])]
                batch[0] += e['bytes']; batch[1].add(line); batch[2].add(e['row']); batch[3].add(e['consumed'])
            delivered += e['bytes']
        need(not choices, 'selection without actual consumption')
        need(seen == wanted, 'missing shared prefix elements')
        for line, req in read_by_line.items():
            segments = consumed_by_line[line]
            need(bool(segments) and sum(e['bytes'] for e in segments) == req['bytes'], 'unconsumed or duplicate read payload')
            need(req['release'] == max(e['consumed'] for e in segments), 'credit released before/after final valid byte')
        f = finished[key]
        need(f['bytes'] == len(wanted) * 4 and f['time'] >= max([e['consumed'] for e in consumes[key]] + [b['time']]), 'tile receipt/retirement mismatch')
        need(end[cid]['epoch'] == b['epoch'] and end[cid]['time'] >= f['time'], 'object released before reader drain')
        if t['local_ready']:
            shared_k = max(0, min(t['start'] + t['count'], b['prefix_k']) - t['start'])
            local_cycles = ((t['count'] - shared_k) * 4 + 31) // 32
            need(f['time'] >= t['local_ready'] + rows * local_cycles * C, 'mixed suffix before local response')
    need(all(n <= (2 if width == 128 else 1) for n in per_issue_cycle.values()), 'per-P issue width exceeded')
    for (cid, worker), es in credit_events.items():
        live = []
        for e in sorted(es, key=lambda x: (x['issued'], x['outstanding'])):
            live = [stamp for stamp in live if stamp > e['issued']]
            live.append(e['release'])
            need(len(live) == e['outstanding'] and len(live) <= specs[cid]['fifo_beats'], 'inflight+returned FIFO credit exceeded')
            peak = max(peak, len(live))
    max_lines = 2 if width == 128 else 1
    need(all(n <= width and len(lines) <= max_lines for n, lines in per_cycle.values()), 'per-cycle consumer bytes/lines exceeded')
    occupied = defaultdict(list)
    for (cid, worker, chosen), (n, lines, rows, finishes) in chosen_packets.items():
        need(n <= width and len(lines) <= max_lines and len(rows) == 1 and len(finishes) == 1, 'consumer selection packet exceeded width or crossed row')
        occupied[(cid, worker)].append((chosen, next(iter(finishes))))
    for packets in occupied.values():
        ordered = sorted(packets)
        need(all(a[1] <= b[0] for a, b in zip(ordered, ordered[1:])), 'consumer accepted another packet while backpressured')
    by_group = defaultdict(list); global_starts = defaultdict(list)
    for service in services:
        by_group[service[2]].append(service); global_starts[service[0]].append(service)
    for g, spans in by_group.items():
        ordered = sorted(spans)
        need(all(a[1] <= b[0] for a, b in zip(ordered, ordered[1:])), 'physical group double-booked, including same-address consumers')
    need(all(len(es) <= groups and len({e[2] for e in es}) == len(es) for es in global_starts.values()), 'global fabric exceeded independent groups')
    if legacy:
        for cid, v in specs.items():
            for col in range(0, v['columns'], 8):
                ts = sorted((t for (c, _, _), t in tiles.items() if c == cid and t['col'] == col), key=lambda x: x['start'])
                cursor = 0
                for t in ts:
                    need(t['start'] == cursor, 'K discontinuity'); cursor += t['count']
                need(cursor == v['k'], 'missing final K')
        need(peak == 4, 'depth-four FIFO not exercised')
    detail = {}
    for cid in specs:
        starts = defaultdict(list)
        for a, z, g, w in per_case_service[cid]: starts[a].append((g, w))
        packets = [x for (c, _, _), x in per_cycle.items() if c == cid]
        prefetch = 0
        for key, es in issues.items():
            if key[0] != cid: continue
            row_final = defaultdict(int)
            for e in consumes[key]: row_final[e['row']] = max(row_final[e['row']], e['consumed'])
            for e in es:
                row = e['pool'] // begin[cid]['stride']
                if row - 1 in row_final and e['issued'] < row_final[row - 1]: prefetch += 1
        detail[cid] = dict(peak_consumer_bytes=max((x[0] for x in packets), default=0),
            double_line_consumer_cycles=sum(len(x[1]) == 2 for x in packets),
            dual_group_service_cycles=sum(len(es) == 2 for es in starts.values()),
            one_worker_dual_group_service_cycles=sum(len(es) == 2 and es[0][1] == es[1][1] for es in starts.values()),
            cross_row_prefetch_reads=prefetch,
            elapsed_subcycles=end[cid]['time'] - begin[cid]['time'])
    return dict(events=len(events), tiles=len(tiles), consumed_bytes=delivered,
                issued_reads=total_reads, credit_peak=peak, cases=detail)


def directed_cases():
    shapes = [
        (100, 2, 4096, False, [(0, 1, 0, 4096), (1, 1, 0, 4096)]),
        (101, 1, 1024, False, [(0, 1, 0, 1024), (0, 1, 0, 1024)]),
        (102, 1, 2048, False, [(0, 1, 0, 2048), (0, 0, 0, 0)]),
        (103, 3, 65, True, [(0, 3, 1, 63), (0, 3, 1, 63)]),
        (104, 1, 4097, True, [(0, 1, 4093, 4), (0, 1, 4093, 4)]),
        (105, 1, 2048, 2, [(0, 1, 0, 2048), (0, 0, 0, 0)]),
    ]
    values = []
    for cid, rows, k, stall, requests in shapes:
        rng = random.Random(2473300 + cid)
        a = [rng.randrange(-10000, 10001) for _ in range(rows * k)]
        b = [[rng.randrange(-128, 128) for _ in range(k)] for _ in range(2)]
        expected = [sum(a[r * k + i] * b[w][i]
                        for r in range(row, row + count_rows) for i in range(ki, ki + count))
                    for w, (row, count_rows, ki, count) in enumerate(requests)]
        values.append(dict(id=cid, rows=rows, k=k, stall=stall, requests=requests,
                           capacity_bytes=32768, fifo_beats=4, A=a, B=b, expected=expected))
    return values


def write_directed(path, values):
    lines = [str(len(values))]
    for v in values:
        lines.append(f"{v['id']} {v['rows']} {v['k']} {int(v['stall'])}")
        lines += [' '.join(map(str, r)) for r in v['requests']]
        lines.append(' '.join(map(str, v['A'])))
        lines += [' '.join(map(str, row)) for row in v['B']]
    path.write_text('\n'.join(lines) + '\n', encoding='ascii')


def execute(cmd, log, seconds=240):
    with log.open('wb') as output:
        process = subprocess.Popen(list(map(str, cmd)), stdout=output, stderr=subprocess.STDOUT,
                                   start_new_session=True)
        try:
            code = process.wait(timeout=seconds)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()
            raise
        need(code == 0, 'probe command failed; see ' + str(log))


def main():
    parser = argparse.ArgumentParser()
    for key in ('repo', 'model', 'out', 'systemc-prefix'):
        parser.add_argument('--' + key, type=Path, required=True)
    parser.add_argument('--width', type=int, choices=(16, 32, 64, 128), required=True)
    parser.add_argument('--groups', type=int, choices=(1, 2), required=True)
    parser.add_argument('--mapping', choices=('single', 'contiguous', 'striped'), required=True)
    parser.add_argument('--cxx', default='g++')
    args = parser.parse_args()
    need((args.groups == 1 and args.mapping == 'single') or
         (args.groups == 2 and args.mapping in ('contiguous', 'striped')), 'group/mapping mismatch')
    need(bool(os.environ.get('SLURM_JOB_ID')), 'probe compilation/execution requires actual Slurm allocation')
    out = args.out.resolve()
    need(not out.exists() or not any(out.iterdir()), 'probe output must be empty')
    out.mkdir(parents=True, exist_ok=True)
    report = dict(passed=False, width=args.width, groups=args.groups, mapping=args.mapping,
                  scope='Actual generated conditional scheduler events with independent synthetic-payload Fraction/dot oracles; no RTL/full-LLM numerical qualification',
                  model_header_sha256=sha(args.model / 'shared_pool.hpp'),
                  source_sha256={p.name: sha(p) for p in (Path(__file__), HERE / 'probe.cpp')})
    try:
        frozen = args.repo / 'project/experiments/shared_pool_study'
        for name, digest in FROZEN.items(): need(sha(frozen / name) == digest, 'frozen numeric source drift ' + name)
        sys.path.insert(0, str(frozen))
        old = load(frozen / 'numeric_check.py', 'width_frozen_numeric')
        reference = load(frozen / 'numeric_reference.py', 'width_frozen_reference')
        values = reference.cases()
        changed_capacity = []
        if args.groups != 1 or args.width not in (16, 32):
            for v in values:
                if v['capacity_bytes'] != 32768:
                    changed_capacity.append(dict(case=v['id'], old_capacity_bytes=v['capacity_bytes'], new_capacity_bytes=32768))
                    v['capacity_bytes'] = 32768
        report['legacy_725_capacity_changes'] = changed_capacity
        reference.write_input(out / 'legacy-input.txt', values)
        source = old.PROBE
        anchor = 'e.bytes&&e.bytes<=32&&e.bytes%4==0'
        need(source.count(anchor) == 1, 'frozen numeric consumer anchor drift')
        source = source.replace(anchor, f'e.bytes&&e.bytes<={min(args.width,64)}&&e.bytes%4==0')
        hook = 'pool.consumer_ready_at=[&](const shared_pool::Consumed& e){'
        need(source.count(hook) == 1, 'frozen numeric selection anchor drift')
        selection = r'''
    events<<"{\"kind\":\"select\",\"case\":"<<c.id<<",\"worker\":"<<e.worker<<",\"tile\":"<<e.tile_id<<",\"epoch\":"<<e.epoch
     <<",\"row\":"<<e.row<<",\"pool\":"<<e.pool_address<<",\"bytes\":"<<e.bytes<<",\"ready\":"<<e.ready_at<<",\"chosen\":"<<e.consumed_at-C<<"}\n";
'''
        source = source.replace(hook, hook + selection)
        (out / 'legacy-probe.cpp').write_text(source, encoding='utf8')
        prefix = args.systemc_prefix
        builds = [('legacy', out / 'legacy-probe.cpp'), ('directed', HERE / 'probe.cpp')]
        for label, cpp in builds:
            cmd = [args.cxx, '-std=c++17', '-O2', '-Wall', '-Wextra', '-Werror', '-pthread', cpp,
                   '-I' + str(args.model.resolve()), '-I' + str(prefix / 'include'),
                   '-L' + str(prefix / 'lib'), '-Wl,-rpath,' + str(prefix / 'lib'), '-lsystemc', '-o', out / label]
            execute(cmd, out / (label + '-build.log'))
        execute([out / 'legacy', out / 'legacy-input.txt', out / 'legacy-events.jsonl', out / 'legacy-actual.json'], out / 'legacy-run.log')
        actual = json.loads((out / 'legacy-actual.json').read_bytes())
        comparisons = reference.compare(actual['cases'], values)
        need(comparisons == 725, 'lost original numerical regression outputs')
        negatives = {'missing_fill', 'read_before_fill', 'padding_write', 'duplicate_fill_byte', 'early_fill_ack',
                     'out_of_range_read', 'early_epoch_release', 'overwrite_live_epoch', 'reconfigure_live_epoch', 'reuse_live_consumer_fifo'}
        need(set(actual['negative_controls']) == negatives, 'lost original ten negative controls')
        events = [json.loads(line) for line in (out / 'legacy-events.jsonl').open(encoding='utf8')]
        report['legacy'] = dict(output_comparisons=comparisons, negative_controls=actual['negative_controls'],
            events=audit_events(events, values, args.width, args.groups, args.mapping, True),
            input_cases=reference.evidence(values))
        cases = directed_cases(); write_directed(out / 'directed-input.txt', cases)
        execute([out / 'directed', out / 'directed-input.txt', out / 'directed-events.jsonl', out / 'directed-actual.json'], out / 'directed-run.log')
        got = json.loads((out / 'directed-actual.json').read_bytes())['cases']
        need(got == [dict(id=v['id'], dot=v['expected']) for v in cases], 'independent directed dot-product mismatch')
        directed = [json.loads(line) for line in (out / 'directed-events.jsonl').open(encoding='utf8')]
        stats = audit_events(directed, cases, args.width, args.groups, args.mapping, False)
        if args.width < 128 or (args.groups == 2 and args.mapping == 'striped'):
            need(stats['cases'][102]['peak_consumer_bytes'] == args.width, 'selected attainable no-stall width never exercised')
        if args.groups == 2:
            need(stats['cases'][100]['dual_group_service_cycles'] > 0, 'balanced dual-group path not exercised')
            if args.mapping == 'contiguous':
                need(stats['cases'][101]['dual_group_service_cycles'] == 0, 'same-group same-address conflict was broadcast/free-parallelized')
        if args.width == 128:
            need(stats['cases'][105]['peak_consumer_bytes'] == 128 and stats['cases'][105]['double_line_consumer_cycles'] > 0,
                 '128 mode never consumed two already-returned lines after controlled first-beat backpressure')
            need(stats['cases'][103]['cross_row_prefetch_reads'] > 0, '128 scheduler drained FIFO at every row boundary')
            if args.groups == 2 and args.mapping == 'striped':
                need(stats['cases'][102]['one_worker_dual_group_service_cycles'] > 0, '128 striped single worker never issued true simultaneous different-group reads')
        # These targeted evidence corruptions must each be independently rejected.
        rejected = []
        def corrupt(name, mutate):
            bad = deepcopy(directed); mutate(bad)
            try: audit_events(bad, cases, args.width, args.groups, args.mapping, False)
            except AssertionError: rejected.append(name); return
            raise AssertionError('audit negative escaped: ' + name)
        corrupt('duplicate_consumption', lambda es: es.append(deepcopy(next(e for e in es if e['kind'] == 'consume'))))
        corrupt('missing_consumption', lambda es: es.remove(next(e for e in es if e['kind'] == 'consume')))
        corrupt('wrong_source_address', lambda es: next(e for e in es if e['kind'] == 'consume').__setitem__('source', 0))
        corrupt('early_response_consumption', lambda es: next(e for e in es if e['kind'] == 'consume').__setitem__('consumed', 0))
        corrupt('unreturned_line_selected', lambda es: next(e for e in es if e['kind'] == 'select').__setitem__('chosen', 0))
        corrupt('early_credit_release', lambda es: next(e for e in es if e['kind'] == 'issue').__setitem__('release', 0))
        corrupt('fifth_FIFO_credit', lambda es: next(e for e in es if e['kind'] == 'issue').__setitem__('outstanding', 5))
        corrupt('free_read_broadcast', lambda es: es.append(deepcopy(next(e for e in es if e['kind'] == 'issue'))))
        report.update(passed=True, directed=dict(output_comparisons=2 * len(cases), events=stats,
            input_cases=[{k:v for k,v in c.items() if k not in ('A','B','expected')} for c in cases]),
            audit_negative_controls=rejected, frozen_numeric_source_sha256=FROZEN)
    except Exception as exc:
        report.update(error=str(exc), traceback=traceback.format_exc())
    report['artifact_sha256'] = {p.name:sha(p) for p in out.iterdir() if p.is_file() and p.name != 'result.json'}
    (out / 'result.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf8')
    print(json.dumps(dict(passed=report['passed'], result=str(out / 'result.json'))), flush=True)
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
