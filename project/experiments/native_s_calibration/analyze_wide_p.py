"""Read actual wide P DDR/ALLOC/FILL/EXEC traces and separate their costs."""
import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import io
import json
from pathlib import Path
import tarfile


JOBS = {
    '102470': dict(run=101, mode=0, source='5f137509c9ce6b2f4b47ba36e7c48a3ec55e2fd3', archive='9ade4ad4db014798673157216f336a33d4663aff22a0f8e1fc9d261ef470e744'),
    '102474': dict(run=102, mode=4, source='747969c55c541b50b5f5651a26ee9cb3e443726e', archive='0934facdb7f56069e7321ec33c321c3682d56ce967923ca3293f85e68a28b47d'),
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def distribution(values):
    data = sorted(values)
    return dict(min=data[0], p50=data[len(data)//2], p95=data[(len(data)-1)*95//100], max=data[-1], total=sum(data))


def frames(rows):
    result = defaultdict(list)
    active = None
    for cycle, sop, eop, payload in rows:
        if sop:
            assert active is None
            active = cycle, payload
        assert active is not None
        if eop:
            result[active[1]].append((active[0], cycle))
            active = None
    assert active is None
    return result


def fixed_return_replay(last_rsp, fill, issue, done_cycle, first_rsp):
    # Optimistic experiment: hold the exact accepted weight response timestamps
    # fixed, but allow the controller to issue as early as the fastest observed
    # fill/issue paths permit. Omitting A, BEGIN/CTX, output ACK contention and
    # end-of-scope control makes this an optimistic bound, never a product rate.
    fill_tail = min(f[1]-r for f,r in zip(fill,last_rsp,strict=True))
    issue_after_fill = min(e[1]-f[1] for e,f in zip(issue,fill,strict=True))
    issue_ii = min(b[1]-a[1] for a,b in zip(issue,issue[1:]))
    assert min(fill_tail, issue_after_fill, issue_ii) > 0
    end = -1
    slack = []
    for response,e in zip(last_rsp,issue,strict=True):
        end = max(response + fill_tail + issue_after_fill, end + issue_ii)
        assert end <= e[1]
        slack.append(e[1]-end)
    assert end <= issue[-1][1] < done_cycle
    return dict(captured_weight_events=4352, captured_record_order_preserved=True,
        observed_min_last_return_to_fill_EOP=fill_tail, observed_min_fill_EOP_to_EXEC_EOP=issue_after_fill,
        observed_min_EXEC_EOP_spacing=issue_ii, replay_last_EXEC_EOP_cycle=end,
        replay_first_return_to_last_EXEC_EOP=end-first_rsp,
        actual_first_return_to_last_EXEC_EOP=issue[-1][1]-first_rsp,
        actual_last_EXEC_EOP_to_last_complete=done_cycle-issue[-1][1],
        actual_EXEC_EOP_later_than_optimistic_replay=distribution(slack))


def inspect_case(events):
    records = {seq: (cycle, offset, ctx) for cycle,seq,offset,ctx in events['RECORD']}
    done = {seq: (cycle, next_k, ctx) for cycle,seq,next_k,ctx in events['COMPLETE']}
    assert len(records) == len(done) == len(events['RECORD']) == 256 and set(records) == set(done)
    for seq, (cycle, offset, ctx) in records.items():
        assert done[seq][0] > cycle and done[seq][1:] == (offset+128, ctx)
    assert set(Counter(v[2] for v in records.values()).values()) == {16}
    assert len(events['S_WRITE']) == len(events['S_ACK']) == 32 and len(events['A_S_REQ']) == 256
    assert len(events['A_M']) == 256*8
    commands, responses = frames(events['LC_M']), frames(events['M_LR'])
    assert {k: len(v) for k,v in commands.items()} == {1:16, 4:16, 2:256, 3:256}
    assert {k: len(v) for k,v in responses.items()} == {10:16, 4:272, 1:256, 2:256, 3:256}
    alloc, fill, issue = commands[2], responses[2], commands[3]
    offered = {}
    requests = {}
    peak_credit = [0, 0]
    live = [0, 0]
    transfers = defaultdict(list)
    for cycle,kind,tag,address,channel in sorted(
        [(t,0,k,a,c) for t,k,a,c in events['DDR_REQ']] + [(t,1,k,0,0) for t,k,_,_ in events['DDR_RSP']]
    ):
        if kind == 0:
            assert tag not in offered and address % 64 == 0 and channel in (0,1)
            offered[tag] = (cycle,address,channel)
            assert tag not in requests
            requests[tag] = cycle
            live[channel] += 1
            peak_credit[channel] = max(peak_credit[channel], live[channel])
            assert sum(live) <= 32
        else:
            at, address, channel = offered.pop(tag)
            live[channel] -= 1
            assert cycle > at
            transfers[tag>>5].append((tag&31, at, cycle, address))
    assert not offered and live == [0, 0] and len(transfers) == 256 and len(requests) == 4352
    groups = sorted((sorted(t) for t in transfers.values()), key=lambda t: min(row[1] for row in t))
    for group in groups:
        assert [b for b,*_ in group] == list(range(17))
        assert [a for _,_,_,a in group] == list(range(group[0][3], group[0][3]+1088, 64))
    first_req = [min(row[1] for row in g) for g in groups]
    returns = [sorted(row[2] for row in g) for g in groups]
    first_rsp = [g[0] for g in returns]
    last_rsp = [g[-1] for g in returns]
    assert all(a < b for a,b in zip(last_rsp, first_req[1:]))  # one W record on this real source path
    assert all(a[1] < q < r < d[1] for a,q,r,d in zip(alloc,first_req,last_rsp,fill,strict=True))
    within = [b-a for g in returns for a,b in zip(g,g[1:])]
    assert len(within) == 256*16 and min(within) >= 2
    across = [nxt-cur for cur,nxt in zip(last_rsp,first_rsp[1:])]
    source_gap = [nxt-cur for cur,nxt in zip(last_rsp,first_req[1:])]
    admit_gap = [nxt[1]-cur for cur,nxt in zip(last_rsp,alloc[1:])]
    same_peer_latency = [a-b for a,b in zip(first_rsp,first_req,strict=True)]
    assert sum(within)+sum(across) == last_rsp[-1]-first_rsp[0]
    assert sum(source_gap)+sum(same_peer_latency[1:]) == sum(across)
    assert min(admit_gap) > 0
    assert all(fill[i+1][1]<issue[i][1]<issue[i+1][1] for i in range(0,256,2))
    final = max(v[0] for v in done.values())
    assert events['S_ACK'][-1][0] < final
    scope = events['CASE_DONE'][0][1]
    assert scope > last_rsp[-1]-first_rsp[0] and final > last_rsp[-1]
    return dict(cycles_start_to_terminal=scope, native_records=256, exact_weight_bus_B=4352*64,
        DDR_request_beat_count=4352, DDR_RSP_count=4352, result_S_ACK=32, A_reads=256,
        W_records_concurrently_transferring=1, peak_fixture_outstanding_beats_by_channel=peak_credit,
        observed_first_to_last_DDR_return_cycles=last_rsp[-1]-first_rsp[0],
        max_link_rate_no_gaps_return_span=2*(4352-1), within_W_record_return_cycles=sum(within),
        within_W_record_gap=distribution(within),
        cross_W_record_return_cycles=sum(across), cross_record_idle_beyond_2cyc=sum(x-2 for x in across),
        cross_record_gap=distribution(across), previous_last_return_to_next_first_request=distribution(source_gap),
        previous_last_return_to_next_ALLOC_EOP=distribution(admit_gap),
        within_prepared_pair_return_to_next_ALLOC_EOP=distribution(admit_gap[::2]),
        between_prepared_pairs_return_to_next_ALLOC_EOP=distribution(admit_gap[1::2]),
        record_first_req_to_first_rsp=distribution(same_peer_latency),
        alloc_EOP_to_first_req=distribution([q-a[1] for a,q in zip(alloc,first_req,strict=True)]),
        record_last_rsp_to_fill_EOP=distribution([f[1]-r for r,f in zip(last_rsp,fill,strict=True)]),
        EXEC_EOP_spacing=distribution([b[1]-a[1] for a,b in zip(issue,issue[1:])]),
        last_DDR_return_to_last_result_completion=final-last_rsp[-1],
        same_return_trace_cannot_complete_before_cycle=last_rsp[-1],
        trace_first_DDR_return_cycle=first_rsp[0], trace_last_DDR_return_cycle=last_rsp[-1],
        fixed_return_replay=fixed_return_replay(last_rsp,fill,issue,final,first_rsp[0]))


def audit(job, path, reference=None):
    info = JOBS[job]
    data = path.read_bytes()
    if reference is None:
        assert sha(data) == info['archive']
    cases = []
    with tarfile.open(fileobj=io.BytesIO(data), mode='r:gz') as a:
        source_digest = sha(a.extractfile('source.sha256').read())
        for seed in range(1,7):
            for init in range(3):
                stem = f'p-resident-{info["mode"]}-{seed}-{init}'
                raw = a.extractfile(stem+'.csv').read()
                log = a.extractfile(stem+'.log').read()
                assert b'PASS p_resident_x_compare' in log and b'W64=8704 S128ACK=64 Aread=512' in log
                events = defaultdict(lambda: defaultdict(list))
                for row in csv.DictReader(io.StringIO(raw.decode())):
                    events[int(row['case'])][row['event']].append(tuple(int(row[k]) for k in ('cycle','identity','detail','value')))
                assert set(events) == {0,1}
                cases += [dict(seed=seed, init=init, case=c, trace_sha256=sha(raw), log_sha256=sha(log),
                               **inspect_case(events[c])) for c in (0,1)]
    assert len(cases) == 36
    result = dict(job=job, source=info['source'], source_manifest_sha256=source_digest,
                source_run=f'issue250-control-prep-20261110-{info["run"]}', archive_sha256=info['archive'],
                scope='One real P: N64 gate + N64 up, K2048, two scopes. Captured 32-entry finite DDR peer across both channels; no full chip performance claim.',
                effective_cycles=distribution([c['cycles_start_to_terminal'] for c in cases]),
                fixed_DDR_return_span=distribution([c['observed_first_to_last_DDR_return_cycles'] for c in cases]),
                fixed_DDR_idle_cycles=distribution([c['cross_record_idle_beyond_2cyc'] for c in cases]),
                fixed_DDR_replay_min_exec_span=distribution([c['fixed_return_replay']['replay_first_return_to_last_EXEC_EOP'] for c in cases]),
                rows=cases)
    if reference is not None:
        # Permit re-packing raw remote files (gzip header/order may differ),
        # only if every CSV/log/manifest hash and derived result still matches.
        assert result == json.loads(reference.read_text())
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--job', choices=JOBS, required=True)
    p.add_argument('--archive', type=Path, required=True)
    p.add_argument('--reference', type=Path, help='Checked-in JSON to verify a re-packed archive file-by-file')
    p.add_argument('--out', type=Path, required=True)
    args = p.parse_args()
    result = audit(args.job, args.archive, args.reference)
    args.out.write_text(json.dumps(result,indent=2)+'\n',newline='\n')
    print(json.dumps({k:v for k,v in result.items() if k!='rows'}))
