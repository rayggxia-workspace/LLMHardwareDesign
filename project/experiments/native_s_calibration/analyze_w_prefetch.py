"""Audit real two/four-W admission with the same direct wide-P DDR peer."""
import argparse
from collections import Counter, defaultdict
import csv
import io
import json
from pathlib import Path
import tarfile

from analyze_wide_p import distribution, fixed_return_replay, frames, sha

JOBS = {
    4: (102524, 113, '929590a5c334b6b42c116255ea6ee3c53e14a727', '6232af646f14103822cda135ead753b987ffde2c80a309ee79fc16075fd4daa1'),
    5: (102524, 113, '929590a5c334b6b42c116255ea6ee3c53e14a727', 'a85e89560dadefb4a3398a7dd5ffb2203a2d599eadbe02b59e125fe2cde8725f'),
    6: (102530, 114, '956ffcf6caf7b7d9c000d2bb599399ef1347c5fb', 'bbb2483edf072e9e255c920485b66a049185fd64e5b2e0e68099b0134b6fdd7a'),
}


def record_index(events, event):
    index = {key: (t, u, v) for t,key,u,v in events[event]}
    assert len(index) == len(events[event]) == 256
    return index


def peak(intervals):
    timeline = sorted((t, delta) for start,end in intervals for t,delta in ((start,1),(end,-1)))
    occupied = highest = 0
    for _,delta in timeline:
        occupied += delta
        assert occupied >= 0
        highest = max(occupied, highest)
    assert occupied == 0
    return highest


def peer_idle_cycle_counts(req, rsp, seed):
    """Classify time above one return per two cycles. Readiness is inferred only
    from accepted request timestamps and the test peer's explicit due rule."""
    requests = dict(req)
    responses = dict(rsp)
    assert len(requests) == len(responses) == 4352
    t_prev = None
    pending = {}
    idle = Counter()
    for t in range(min(requests), max(responses)+1):
        if t in requests:
            pending[requests[t]] = t + 7 + seed%4
        if t in responses:
            assert pending.pop(responses[t]) < t
            if t_prev is not None:
                assert t-t_prev >= 2
            t_prev = t
        elif t_prev is not None and t >= t_prev+2:
            if not pending:
                idle['no_outstanding_request'] += 1
            elif min(pending.values()) >= t:
                idle['only_not_yet_eligible_requests'] += 1
            else:
                idle['eligible_request_present'] += 1
    assert not pending
    assert sum(idle.values()) == max(responses)-min(responses)-2*(4352-1)
    return dict(idle)


def inspect(events, seed, mode):
    records, alloc, fill, execute, done = [record_index(events,k) for k in
        ('RECORD','W_ALLOC','W_FILL','M_EXEC','COMPLETE')]
    assert records.keys() == alloc.keys() == fill.keys() == execute.keys() == done.keys()
    assert len(events['S_WRITE']) == len(events['S_ACK']) == 32 and len(events['A_S_REQ']) == 256
    assert len(events['A_M']) == 2048
    assert set(Counter(v[2] for v in records.values()).values()) == {16}
    commands, responses = frames(events['LC_M']), frames(events['M_LR'])
    assert {k:len(v) for k,v in commands.items()} == {1:16, 4:16, 2:256, 3:256}
    assert {k:len(v) for k,v in responses.items()} == {10:16, 4:272, 1:256, 2:256, 3:256}
    offered = {}
    live = [0,0]
    peak_credit = [0,0]
    transfers = defaultdict(list)
    req = [(t,tag) for t,tag,_,_ in events['DDR_REQ']]
    rsp = [(t,tag) for t,tag,_,_ in events['DDR_RSP']]
    for t,kind,tag,address,channel in sorted(
        [(t,0,tag,a,ch) for t,tag,a,ch in events['DDR_REQ']] + [(t,1,tag,0,0) for t,tag in rsp]
    ):
        if not kind:
            assert tag not in offered and address%64 == 0 and channel in (0,1)
            offered[tag] = (t,address,channel)
            live[channel] += 1
            peak_credit[channel] = max(peak_credit[channel],live[channel])
            assert sum(live) <= 32
        else:
            at,address,channel = offered.pop(tag)
            live[channel] -= 1
            assert t > at
            transfers[tag>>5].append((tag&31,at,t,address,channel))
    assert not offered and live == [0,0] and len(transfers) == 256 and len(req) == len(rsp) == 4352
    sequences = sorted(alloc,key=lambda seq:alloc[seq][0])
    requests = sorted(transfers.values(),key=lambda rows:min(r[1] for r in rows))
    issue = sorted(execute,key=lambda seq:execute[seq][0])
    bank_intervals = defaultdict(list)
    windows = {}
    workload = []
    for seq,group in zip(sequences,requests,strict=True):
        rows = sorted(group)
        assert [r[0] for r in rows] == list(range(17))
        assert [r[3] for r in rows] == list(range(rows[0][3],rows[0][3]+1088,64))
        request_first,return_first,return_last = min(r[1] for r in rows),min(r[2] for r in rows),max(r[2] for r in rows)
        windows[seq] = request_first,return_first,return_last
        assert records[seq][0] < alloc[seq][0] < request_first <= return_first <= return_last < fill[seq][0] < execute[seq][0] < done[seq][0]
        assert alloc[seq][1] == execute[seq][1] == records[seq][2] == done[seq][2]
        assert execute[seq][2] == records[seq][1] == done[seq][1]-128
        workload.append((seq,records[seq][1:],tuple((r[3],r[4]) for r in rows)))
    for seq,(_,input_eop) in zip(issue,responses[3],strict=True):
        bank,generation = fill[seq][1:]
        assert 0 <= bank < 4 and execute[seq][0] < input_eop < done[seq][0]
        bank_intervals[bank].append((alloc[seq][0],input_eop,generation))
    for intervals in bank_intervals.values():
        intervals.sort()
        assert all(a[1] < b[0] and a[2] < b[2] for a,b in zip(intervals,intervals[1:]))
    physical_peak = peak([x[:2] for xs in bank_intervals.values() for x in xs])
    inflight_peak = peak([(t,r) for t,_,r in windows.values()])
    assert physical_peak == (4 if mode == 6 else 2) and inflight_peak == {4:1,5:2,6:4}[mode]
    k_windows = defaultdict(list)
    for seq,(first_request,_,last_return) in windows.items():
        k_windows[records[seq][1]].append((first_request,last_return))
    k_ranges = [(min(x[0] for x in k_windows[k]),max(x[1] for x in k_windows[k])) for k in sorted(k_windows)]
    assert len(k_ranges) == 16 and all(r0 < q1 for (_,r0),(q1,_) in zip(k_ranges,k_ranges[1:]))
    first,last = rsp[0][0],rsp[-1][0]
    terminal = max(t for t,_,_ in done.values())
    replay = fixed_return_replay([windows[seq][2] for seq in issue], [(0,fill[seq][0]) for seq in issue],
                                 [(0,execute[seq][0]) for seq in issue],terminal,first)
    replay = {k.replace('fill_EOP','native_FILL').replace('EXEC_EOP','core_EXEC'):v for k,v in replay.items()}
    assert events['S_ACK'][-1][0] < terminal and events['CASE_DONE'][0][1] >= last-first
    return dict(scope_cycles=events['CASE_DONE'][0][1], weight_bus_B=278528, A_S_read_words=256, A_M_beats=2048,
        terminal_S_ACKs=32, weight_records=256, peak_W_bank_owners=physical_peak,
        peak_concurrent_W_fetches=inflight_peak, peak_DDR_credits_by_channel=peak_credit,
        cross_K_tile_fetch_overlap=False, first_tile_peak_concurrent_W_fetches=peak(k_windows[0]),
        first_to_last_DDR_return_cycles=last-first, idle_beyond_one_return_per_two_cycles=peer_idle_cycle_counts(req,rsp,seed),
        native_ALLOC_to_first_DDR_request=distribution([t-alloc[k][0] for k,(t,_,_) in windows.items()]),
        first_DDR_request_to_first_return=distribution([f-t for t,f,_ in windows.values()]),
        last_return_to_native_FILL=distribution([fill[k][0]-r for k,(_,_,r) in windows.items()]),
        native_FILL_to_core_EXEC=distribution([execute[k][0]-fill[k][0] for k in fill]),
        last_DDR_return_to_last_result_completion=terminal-last,
        fixed_return_replay_core_EXEC=replay, exact_schedule_workload_sha256=sha(repr(sorted(workload)).encode()))


def audit(path, mode, reference=None):
    job,run,source,archive_digest = JOBS[mode]
    data = path.read_bytes()
    if reference is None:
        assert sha(data) == archive_digest
    rows = []
    with tarfile.open(fileobj=io.BytesIO(data),mode='r:gz') as archive:
        manifest = sha(archive.extractfile('source.sha256').read())
        for seed in range(1,7):
            for init in range(3):
                stem = f'p-resident-{mode}-{seed}-{init}'
                raw,log = [archive.extractfile(stem+ext).read() for ext in ('.csv','.log')]
                assert f'PASS p_resident_x_compare mode={mode} seed={seed} scopes=2 groups=8 W64=8704 S128ACK=64 Aread=512 copy=512'.encode() in log
                events = defaultdict(lambda: defaultdict(list))
                for row in csv.DictReader(io.StringIO(raw.decode())):
                    events[int(row['case'])][row['event']].append(tuple(int(row[k]) for k in ('cycle','identity','detail','value')))
                assert set(events) == {0,1}
                rows += [dict(seed=seed,init=init,case=c,trace_sha256=sha(raw),log_sha256=sha(log),**inspect(events[c],seed,mode)) for c in (0,1)]
    result = dict(job=job,mode=mode,source=source,archive_sha256=archive_digest,source_manifest_sha256=manifest,
        source_run=f'issue250-control-prep-20261110-{run}',same_DDR_peer=True,whole_P3_perf_qualified=False,
        scope_cycles=distribution([r['scope_cycles'] for r in rows]),rows=rows)
    if reference is not None:
        assert result == json.loads(reference.read_text())
    return result


def compare(paths):
    datasets = [json.loads(p.read_text()) for p in paths]
    assert [d['mode'] for d in datasets] == [4,5,6]
    for group in zip(*(d['rows'] for d in datasets),strict=True):
        assert len({(r['seed'],r['init'],r['case'],r['exact_schedule_workload_sha256']) for r in group}) == 1
        assert all(r['weight_bus_B']==278528 and r['terminal_S_ACKs']==32 for r in group)
        assert all(not r['cross_K_tile_fetch_overlap'] for r in group)
    return dict(schema='wide-P-weight-prefetch-paired/1', shape='K2048 N64 gate and N64 up, one P', scopes_per_mode=36,
        exact_same_addresses_channels_contexts_K=True, actual_same_direct_DDR_peer=True,
        actual_production_P3_throughput=False, same_DDR_return_limit_B_per_cycle=32,
        SRAM_added_B=0, four_prefetch_metadata_bits=506, four_candidate_earlier_pair_save_bits=33,
        modes=[dict(mode=d['mode'],job=d['job'],input_JSON_SHA256=sha(p.read_bytes()),cycles=d['scope_cycles'],
            total_cycle_reduction_from_mode4=1-d['scope_cycles']['total']/datasets[0]['scope_cycles']['total'],
            return_span=distribution([r['first_to_last_DDR_return_cycles'] for r in d['rows']]),
            peer_idle={reason:distribution([r['idle_beyond_one_return_per_two_cycles'].get(reason,0) for r in d['rows']])
                for reason in ('no_outstanding_request','only_not_yet_eligible_requests','eligible_request_present')},
            max_first_tile_W_fetches=max(r['first_tile_peak_concurrent_W_fetches'] for r in d['rows']))
            for p,d in zip(paths,datasets,strict=True)])


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--mode',type=int,choices=JOBS)
    mode.add_argument('--compare',type=Path,nargs=3,metavar='MODE_JSON')
    parser.add_argument('--archive',type=Path)
    parser.add_argument('--reference',type=Path)
    parser.add_argument('--out',type=Path,required=True)
    args = parser.parse_args()
    if args.compare:
        if args.archive or args.reference:
            parser.error('--compare consumes checked-in JSON rather than raw archives')
        result = compare(args.compare)
    else:
        if args.archive is None:
            parser.error('--mode requires --archive')
        result = audit(args.archive,args.mode,args.reference)
    args.out.write_text(json.dumps(result,indent=2)+'\n',newline='\n')
    print(json.dumps({k:v for k,v in result.items() if k != 'rows'}))
