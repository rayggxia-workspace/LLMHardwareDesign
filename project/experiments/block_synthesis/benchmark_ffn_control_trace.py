"""Record real MC/LC handshakes in the frozen #251 programmed FFN."""
import argparse
import json
from pathlib import Path

from dma_read import Profile, Read
from event_replay import Operation, Phase, replay


ANCHOR = ' end else begin: direct_test'
MONITOR = """  reg [2:0] probe_offer_seen=0;
  reg [2:0] probe_fetch_seen=0;
  reg [31:0] probe_fetch_tag[3];
  always @(posedge clk) if($test$plusargs("TRACE_CONTROL")&&!reset)begin
   if(program_start&&program_ready)$display("CONTROL start %0d",cycle);
   if(program_result&&program_result_take)
    $display("CONTROL result %0d %0d %0d",cycle,terminal_reads,terminal_writes);
   if(control.tx_valid&&control.tx_ready&&control.tx_eop)
    $display("CONTROL call %0d %0d",cycle,control.tx_target);
   if(control.rx_valid&&control.rx_ready&&control.rx_eop)
    $display("CONTROL terminal %0d %0d",cycle,control.rx_source);
   for(integer p=0;p<3;p++)begin
    if(dr_valid[p]&&(!probe_fetch_seen[p]||probe_fetch_tag[p]!=dr_tag[p*32+:32]))
     $display("CONTROL fetch_valid %0d %0d %0d %0d",cycle,p,dr_tag[p*32+:32],dr_address[p*64+:64]);
    if(dr_valid[p]&&dr_ready[p])
     $display("CONTROL fetch %0d %0d %0d %0d",cycle,p,dr_tag[p*32+:32],dr_address[p*64+:64]);
    if(dr_rsp_valid[p]&&dr_rsp_ready[p])
     $display("CONTROL fetch_return %0d %0d %0d",cycle,p,dr_rsp_tag[p*32+:32]);
    if(lc_call[p]&&!probe_offer_seen[p])
     $display("CONTROL offer %0d %0d %0d",cycle,p,lc_owner[p*128+:32]);
    if(lc_call[p]&&lc_call_ready[p])
     $display("CONTROL dispatch %0d %0d %0d",cycle,p,lc_owner[p*128+:32]);
    if(lc_done[p]&&lc_done_ready[p])
     $display("CONTROL done %0d %0d %0d %0d %0d",cycle,p,lc_done_owner[p*128+:32],
              lc_done_reads[p*32+:32],lc_done_writes[p*32+:32]);
    probe_offer_seen[p]<=lc_call[p];
    probe_fetch_seen[p]<=dr_valid[p];
    probe_fetch_tag[p]<=dr_tag[p*32+:32];
   end
  end
"""

# From the last accepted CALL flit, the LC accepts the frame, reads PM and
# metadata, then presents the first 64 B fetch. CRC scans 124 bytes after the
# final data handshake. The two following edges consume CRC and assert service.
CALL_TO_FETCH = 46
DESCRIPTOR_CHECK_TICKS = 125  # DMA phase ends one edge after the final beat.
DONE_TO_TERMINAL_FRAME = 5
TERMINAL_FRAME_WITH_BUBBLE = 5
TERMINAL_EOP_OFFSET = 3


def require(condition, message):
    if not condition:
        raise ValueError(message)


def instrument(source, destination):
    rtl = source.read_text(encoding='utf-8')
    if rtl.count(ANCHOR) != 1:
        raise ValueError('expected the unique programmed FFN block in #251')
    with destination.open('x', encoding='utf-8', newline='\n') as output:
        output.write(rtl.replace(ANCHOR, MONITOR + ANCHOR))


def read_trace(source):
    open_calls = {}
    scopes = []
    start = result = program = None
    passed = False
    for line in source:
        if line.startswith('PROGRAM_PROFILE '):
            require(program is None, 'duplicate programmed FFN profile')
            program = dict(item.split('=') for item in line.split()[1:])
        if line.startswith('PASS ffn_three_p_native ') and ' program=1 ' in line:
            passed = True
        if not line.startswith('CONTROL '):
            continue
        _, kind, raw_tick, *fields = line.split()
        tick = int(raw_tick)
        values = tuple(map(int, fields))
        if kind == 'start':
            require(start is None and not values, 'duplicate or malformed program start')
            start = tick
        elif kind == 'result':
            require(result is None and len(values) == 2, 'duplicate or malformed program result')
            result = tick, *values
        else:
            client, *fields = values
            require(0 <= client < 3 and start is not None and tick >= start, 'invalid LC event')
            if kind == 'call':
                require(client not in open_calls, f'new CALL before LC {client} retired')
                open_calls[client] = {'client': client}
                scopes.append(open_calls[client])
            require(client in open_calls, f'LC {client} event without CALL')
            open_calls[client].setdefault(kind, []).append((tick, *fields))
            if kind == 'terminal':
                del open_calls[client]
    require(passed and start is not None and result is not None and not open_calls and program is not None,
            'incomplete programmed FFN trace')
    require(len(scopes) == 192, 'expected all 192 native calls')
    return scopes, start, result, program


def check(source, mode, seed):
    scopes, start, result, program = read_trace(source)
    transfers, terminals = [], []
    sequence = [0] * 3
    read_bytes = write_bytes = 0
    for index, scope in enumerate(scopes):
        client = scope['client']
        sequence[client] += 1
        serial = sequence[client]
        prefix = f'CALL {index + 1}, LC {client}'
        require(all(len(scope.get(event, ())) == count for event, count in
                    (('call', 1), ('fetch_valid', 2), ('fetch', 2), ('fetch_return', 2),
                     ('offer', 1), ('dispatch', 1), ('done', 1), ('terminal', 1))),
                f'{prefix} missing or duplicated events')
        (call,), = scope['call']
        (offer, offer_owner), = scope['offer']
        (dispatch, dispatch_owner), = scope['dispatch']
        (done, done_owner, reads, writes), = scope['done']
        (terminal,), = scope['terminal']
        require(offer_owner == dispatch_owner == done_owner == serial and offer <= dispatch <= done < terminal,
                f'{prefix} service ownership or boundaries differ')
        read_bytes += reads + 128
        write_bytes += writes
        addr = 4096 + 128 * index
        expected = ((serial * 2, addr), (serial * 2 + 1, addr + 64))
        require(tuple(row[1:] for row in scope['fetch_valid']) ==
                tuple(row[1:] for row in scope['fetch']) == expected, f'{prefix} descriptor identity differs')
        require(sorted(row[1] for row in scope['fetch_return']) == [serial * 2, serial * 2 + 1],
                f'{prefix} returned tags differ')
        require(tuple(row[0] for row in scope['fetch_valid']) ==
                (call + CALL_TO_FETCH, scope['fetch'][0][0] + 1), f'{prefix} source VALID timing differs')
        transfers.append(Operation((
            Phase('decode CALL', CALL_TO_FETCH),
            Phase('descriptor DMA', 1, dma_read=Read(client, addr, 128, 2)),
            Phase('CRC and service offer', DESCRIPTOR_CHECK_TICKS),
        ), release=call))
        terminals.append(Operation((
            Phase('terminal packet and receive bubble', TERMINAL_FRAME_WITH_BUBBLE, (('MC.rx', 1),), client),
        ), release=done + DONE_TO_TERMINAL_FRAME))

    profile = Profile.from_spec({'ffn_provider': {'mode': mode, 'seed': seed}})
    grants = replay(transfers + terminals, {'MC.rx': 1}, dma_profile=profile)
    for scope, transfer, terminal in zip(scopes, grants[:len(scopes)], grants[len(scopes):]):
        beats = transfer[1].dma_beats
        require(tuple(beat.reserved for beat in beats) == tuple(row[0] for row in scope['fetch'])
                and sorted((beat.delivered, scope['fetch'][i][1]) for i, beat in enumerate(beats)) ==
                scope['fetch_return'], 'descriptor DMA handshakes differ')
        require(transfer[-1].end == scope['offer'][0][0], 'CRC or service offer timing differs')
        require(terminal[0].start + TERMINAL_EOP_OFFSET == scope['terminal'][0][0],
                'terminal arbitration or framing differs')
    require((int(program['calls']), int(program['confirmed_reads']), int(program['confirmed_writes'])) ==
            (len(scopes), read_bytes, write_bytes) and result[1:] == (read_bytes, write_bytes),
            'program byte accounting differs')
    require(result[0] > max(s['terminal'][0][0] for s in scopes), 'program result preceded child retirement')
    return {'calls': len(scopes), 'descriptor_beats': 2 * len(scopes), 'start': start,
            'result_accept': result[0], 'read_bytes': read_bytes, 'write_bytes': write_bytes,
            'longest_service_offer_wait': max(s['dispatch'][0][0] - s['offer'][0][0] for s in scopes),
            'longest_done_to_terminal': max(s['terminal'][0][0] - s['done'][0][0] for s in scopes)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    prepare = sub.add_parser('instrument')
    prepare.add_argument('source', type=Path)
    prepare.add_argument('destination', type=Path)
    verify = sub.add_parser('check')
    verify.add_argument('log', type=Path)
    verify.add_argument('--mode', type=int, choices=(0, 1), required=True)
    verify.add_argument('--seed', type=int, default=25001)
    args = parser.parse_args()
    if args.action == 'instrument':
        instrument(args.source, args.destination)
    else:
        with args.log.open(encoding='utf-8') as source:
            print(json.dumps(check(source, args.mode, args.seed), indent=2))


if __name__ == '__main__':
    main()
