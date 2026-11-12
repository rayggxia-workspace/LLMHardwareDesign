"""Re-run #251's actual finite FFN DDR provider against candidate read plans."""
import argparse
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import tarfile

from benchmark_native_dma_read import Request, check_case, event_input, moves_by_task, write_case
from cover_frontier import search
from verify_cover_frontier import verify


ARCHIVE_SHA256 = '058b32a84fbb7b3613dcf9fa6ab5fb74685d08a740ba417f569bedf6968d1d24'
NATIVE = 'source/project/experiments/block_local_native/test_ffn_three_p_native.sv'
FABRIC = 'source/project/rtl/mother_control_native/mc_dma_fabric_typed_p.sv'
SEED = 25001
RECORD_BYTES = 17 * 64
WEIGHTS = (
    Request(1, 9, 0x02000000, 16 * RECORD_BYTES, 17),
    Request(3, 10, 0x04000000, 16 * RECORD_BYTES, 17),
)
SCOPES = (Request(2, 0, 4096, 1024), Request(3, 1, 8192, 1024))
REPLICA_OFFSET = 0x100800


def build_wrapper(archive, directory):
    with archive.open('rb') as source:
        if hashlib.file_digest(source, 'sha256').hexdigest() != ARCHIVE_SHA256:
            raise ValueError('expected the pinned #251 102603 source archive')
    with tarfile.open(archive, 'r:gz') as source:
        original = source.extractfile(NATIVE).read().decode()
        fabric = source.extractfile(FABRIC).read()
    rtl = fabric.decode()
    ports = rtl.split(') (', 1)[1].split('\n);', 1)[0].replace('output reg', 'output wire')
    for width, name in ((3, 'd_req_ready'), (3, 'd_rsp_valid'), (255, 'd_rsp_tag'), (2047, 'd_rsp_data')):
        before = f'input wire [{width}:0] {name}'
        if ports.count(before) != 1:
            raise ValueError(f'cannot expose the provider-owned port {name}')
        ports = ports.replace(before, before.replace('input', 'output', 1))
    start = original.index('  for(genvar lane=0;lane<4;lane++)begin: finite_backend_lane')
    stop = original.index('  for(genvar ch=0;ch<2;ch++)begin: limit', start)
    provider = original[start:stop]
    first = provider.rindex('\n', 0, provider.index('if(d_tag[')) + 1
    last = provider.rindex('\n', first, provider.index('due[tail]', first)) + 1
    # The FFN payload comes from its numerical fixture. Use an address pattern
    # instead, retaining the original queue, READY, VALID and due expressions.
    provider = provider[:first] + (
        '        for(integer word=0;word<16;word++)\n'
        '         payload[tail][32*word+:32]<=d_addr[64*lane+:32]^32\'(word);\n'
    ) + provider[last:]
    empty = 'assign backend_empty[lane]=count==0;'
    if provider.count(empty) != 1:
        raise ValueError('cannot expose full status for the FFN provider')
    provider = provider.replace(empty, 'assign backend_full[lane]=count==16;')
    wrapper = f"""module ffn_dma_read_probe (
 input wire [31:0] cycle, mode, seed,
 output wire [3:0] backend_full,{ports}
);
 mc_dma_fabric_typed_p fabric(.*);
 wire [3:0] d_req=d_req_valid, d_rsp;
 wire [255:0] d_addr=d_req_address, d_tag=d_req_tag, d_ret_tag;
 wire [2047:0] d_ret_data;
 wire fence_pending=d_fence_done_valid;
 assign d_rsp_valid=d_rsp;
 assign d_rsp_tag=d_ret_tag;
 assign d_rsp_data=d_ret_data;
{provider}endmodule
"""
    (directory / 'mc_dma_fabric_typed_p.sv').write_bytes(fabric)
    (directory / 'ffn_dma_read_probe.sv').write_text(wrapper, encoding='utf-8')


def cases():
    for mode in (0, 1):
        for split in (False, True):
            gate, up = WEIGHTS
            if split:
                up = replace(up, address=up.address + 2048)
            yield f'ffn-{mode}-split-{int(split)}', (gate, up, *SCOPES), (), {'mode': mode, 'seed': SEED}
    stress = tuple(Request(1 + client % 2, client, 0x10000 * client, 2048) for client in range(9))
    yield 'full', stress, ((0, 68, 0),), {'mode': 1, 'seed': SEED, 'cycle_offset': 4}
    for old_channel in (0, 1):
        reads = paired_reads(old_channel)
        yield f'old-{old_channel}-primary', reads, (), {'mode': 0, 'seed': SEED}
        yield (f'old-{old_channel}-replica', (reads[0], replace(reads[1], address=reads[1].address + REPLICA_OFFSET)),
               (), {'mode': 0, 'seed': SEED})


def paired_reads(old_channel):
    gate, up = WEIGHTS
    return (replace(gate, address=gate.address + old_channel * 2048, size=RECORD_BYTES),
            replace(up, release=1, size=RECORD_BYTES))


def paired_input(old_channel):
    reads = paired_reads(old_channel)
    tasks, hardware = event_input(reads, ffn_provider={'mode': 0, 'seed': SEED})
    spec = hardware['event_model']
    up = reads[1].address
    spec['typed_dma']['addresses']['v1'] = {'primary': up, 'replica': up + REPLICA_OFFSET}
    original = spec['routes']['P1.read-10']
    spec['routes']['P1.read-10-replica'] = {**original, 'typed_dma': {**original['typed_dma'], 'replica': 'replica'}}
    spec['external_capacity_bytes'] = 3 * RECORD_BYTES
    return tasks, hardware


def check_choices(result):
    choices = {}
    for old_channel in (0, 1):
        costs = {name: result[f'old-{old_channel}-{name}']['ticks'] for name in ('primary', 'replica')}
        expected = 'replica' if old_channel == 0 else 'primary'
        if costs[expected] >= max(costs.values()):
            raise ValueError('old traffic did not reverse the RTL candidate ranking')
        tasks, hardware = paired_input(old_channel)
        route = 'P1.read-10-replica' if expected == 'replica' else 'P1.read-10'
        for width in (1, 8):
            plan = search(tasks, hardware, width=width)
            verify(tasks, hardware, (), plan)
            if (moves_by_task(plan)[1]['route'], plan['makespan']) != (route, costs[expected]):
                raise ValueError('search failed to choose the faster backed weight replica')
        choices[f'old_channel_{old_channel}'] = {**costs, 'selected': expected}
    return choices


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare', 'check'))
    parser.add_argument('directory', type=Path)
    parser.add_argument('--archive', type=Path)
    args = parser.parse_args()
    if args.action == 'prepare':
        if args.archive is None:
            parser.error('prepare requires the pinned #251 source archive')
        args.directory.mkdir(exist_ok=True)
        build_wrapper(args.archive, args.directory)
        for name, reads, stalls, profile in cases():
            write_case(args.directory, name, reads, client_stalls=stalls, ffn_provider=profile)
    else:
        result = {name: check_case(args.directory, name, reads, client_stalls=stalls, ffn_provider=profile)
                  for name, reads, stalls, profile in cases()}
        if not sum(result['full']['full_lane_ticks']):
            raise ValueError('pressure case did not fill a physical FIFO')
        print(json.dumps({'cases': result, 'choices': check_choices(result)}, indent=2))


if __name__ == '__main__':
    main()
