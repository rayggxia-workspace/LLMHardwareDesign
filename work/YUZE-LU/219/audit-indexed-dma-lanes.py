"""Identify the remaining physical and request-format needs of indexed DMA."""

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ('base', 'contract', 'dma', 'layout', 'out'):
        parser.add_argument(arg, type=Path)
    args = parser.parse_args()
    base = json.loads(args.base.read_bytes())
    contract = json.loads(args.contract.read_bytes())
    layout = json.loads(args.layout.read_bytes())
    parts = ('source.sv', 'mc_dma_fabric_typed_p_commit.sv')
    source_seal = {name: digest for digest, name in
                   (line.split() for line in (args.dma/'input.sha256').read_text().splitlines())}
    source = {}
    for part in parts:
        raw = (args.dma/part).read_bytes()
        assert sha256(raw).hexdigest() == source_seal[part]
        source[part] = raw.decode()
    stage, fabric = (source[part] for part in parts)
    for marker in ('input_length!=2||c_req_address[64*client+6]!=input_beat[0]',
                   'input_beat!=0||input_channel_bit!=c_req_channel[client]'):
        assert marker in stage, marker
    for marker in ('client<9?{unused_tag[31:1]', 'c_rsp_data[client*512+:512]',
                   'grant_beat[r]+5\'d1==grant_length[r]'):
        assert marker in fabric, marker
    owners = contract['lane_owners']
    bound_clients = {int(n) for family in owners.values() for n in family.values()}
    pins = base['endpoints']
    # Columns are the emitted request stream and returned data/ownership, plus close.
    c_signals = {'req_valid': 1, 'req_ready': 1, 'req_address': 64, 'req_tag': 32,
                 'req_channel': 1, 'req_record_beats': 5, 'rsp_valid': 1, 'rsp_ready': 1,
                 'rsp_tag': 32, 'rsp_data': 512, 'close_valid': 1, 'close_ready': 1, 'close_tag_base': 32}
    inventory = {}
    for client in range(12):
        need = {f'dma/c_{signal}[{client*width+bit}]'
                for signal, width in c_signals.items() for bit in range(width)}
        inventory[client] = {'bound': client in bound_clients, 'data_endpoint_members': len(need),
                             'existing_m10_members': sum(bool(pins.get(name, {}).get('m10_shapes')) for name in need)}
    assert bound_clients == {0, 1, 2, 9, 10, 11}
    assert all(inventory[client]['existing_m10_members'] == 0 for client in range(3, 9))
    prompt = layout['regions']['prompt:0']
    weights = layout['regions']['constant:model.embed_tokens.weight']
    # Cover separate address lanes and stripe edges on the actual asset regions.
    rows = weights['bytes'] // 8192
    assert weights['bytes'] == 8192*rows and weights['base'] % 128 == 0
    assert prompt['base'] % 128 == 0 and prompt['bytes'] % 128 == 0
    def read_pair(address):
        start = address & ~127
        return start, start+64
    first = read_pair(prompt['base'])
    last = read_pair(prompt['base']+prompt['bytes']-64)
    assert first[0] == prompt['base'] and last[1]+64 == prompt['base']+prompt['bytes']
    counts = Counter()
    for index in (0, 1, rows-1):
        start = weights['base'] + index * 8192
        for offset in range(0, 8192, 128):
            a, b = read_pair(start + offset)
            assert a == start + offset and ((a>>11)&1) == ((b>>11)&1)
            if index == 0:
                counts[(a>>11)&1] += 1
    package = {
        'scope': 'static negotiation against staged v45 DMA and current Algo2 endpoint catalogue',
        'base_file_sha256': sha256(args.base.read_bytes()).hexdigest(),
        'joint_contract_sha256': sha256(args.contract.read_bytes()).hexdigest(),
        'dma_source_sha256': {part: source_seal[part] for part in parts},
        'client_inventory': inventory, 'selected_client': None,
        'unused_scope_clients': sorted(set(range(3, 9)) - bound_clients),
        'request_format': {'record_beats': 2, 'alignment_bytes': 128, 'returned_beat_bytes': 64,
                           'channel_address_bit': 11, 'beat_tag_low_bit': True},
        'context': {'prompt_pair_extra_bytes': 64, 'row_pairs': sum(counts.values()),
                    'row_ddr_bytes': 8192, 'row_pairs_by_channel': dict(counts)},
        'unqualified': ['physical scope client M10 landings', 'resident indexed service',
                        'provider return to U.S commit path', 'whole request retirement'],
    }
    args.out.write_text(json.dumps(package, sort_keys=True, indent=2)+'\n')
    print(json.dumps(package, sort_keys=True))


if __name__ == '__main__':
    main()
