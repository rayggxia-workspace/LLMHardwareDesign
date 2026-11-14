"""Cross-check compiled KVR1 requests against the independent phase commit table."""
import argparse
from bisect import bisect_right
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
from struct import unpack_from
from zlib import crc32

from publish_native_request_handoff import hash_file, read, read_seal, require
from handoff import verify_handoff


REC_BYTES = 128
SCHEMA = int.from_bytes(b'KVR1', 'little')


def read_destinations(raw, step, streams, bases, capacity, row_bytes, first, rows, cursors):
    committed = Counter()
    for offset in range(0, len(raw), REC_BYTES):
        if raw[offset:offset+4] != b'KVR1':
            continue
        record = raw[offset:offset+REC_BYTES]
        header = unpack_from('<IHHII', record)
        require(header == (SCHEMA, REC_BYTES, 1, 0x02500002, cursors['topology']) or
                header == (SCHEMA, REC_BYTES, 2, 0x02500002, cursors['topology']),
                f'invalid KVR1 signature at phase {step} offset {offset}')
        require(crc32(record[:124]) == unpack_from('<I', record, 124)[0], 'KVR1 record CRC differs')
        address, tag = unpack_from('<QQ', record, 24)
        index = bisect_right(bases, address)-1
        require(index >= 0, 'KVR1 address precedes stream allocation')
        position, residue = divmod(address-bases[index], row_bytes)
        require(not residue and position < capacity and first <= position < first+rows and
                (header[2] == 2) == (streams[index]['kind'] == 'v'), 'wrong KVR1 stream, position or kind')
        require(position == cursors['positions'][index], 'missing, duplicate or out-of-order KV store')
        cursors['positions'][index] += 1
        require((address, row_bytes, tag) in cursors['writes'], 'KVR1 store has no compiled DDR reservation')
        committed[header[2]] += 1
    return committed


def audit(request, binding_dir, handoff, output):
    manifest_path = request/'proof.sha256'
    manifest = read_seal(manifest_path)
    request_sha = hash_file(manifest_path)
    spec = read(handoff/'algorithm2-input.json')
    admission = verify_handoff(spec, handoff)
    program_path = handoff/'program.json'
    require(read(program_path)['source']['package_proof_sha256'] == request_sha,
            'KV binding uses a different program handoff')
    for name in ('witness.json', 'ddr-writes.tsv', 'service-signatures.json'):
        require(hash_file(request/name) == manifest[name], f'changed archive: {name}')
    binding_path = binding_dir/'binding.json'
    table = read(binding_path)
    require(table['schema'] == 'native-request-kv-bindings/1' and table['row_bytes'] == 512,
            'unsupported KV shape or phase binding')
    streams, capacity, row_bytes = table['streams'], table['capacity'], table['row_bytes']
    bases = [row['base'] for row in streams]
    require(len(bases) == table['stream_count'] and bases and
            all(a + capacity*row_bytes <= b for a,b in zip(bases,bases[1:])),
            'overlapping or unordered KV regions')
    for name in ('kv-phases.tsv', 'kv-commit-ranges.tsv', 'kv-streams.hex'):
        require(hash_file(binding_dir/name) == table['files_sha256'][name], f'changed KV binding file: {name}')
    witness = read(request/'witness.json')
    require(len(witness['phases']) == len(table['phases']), 'phase coverage differs')
    with (request/'ddr-writes.tsv').open() as stream:
        writes = {tuple(map(int,line.split())) for line in stream}
    cursors = dict(topology=witness['topology'], positions=[0 for _ in bases], writes=writes)
    reports, expect_first, totals = [], 0, Counter()
    for source, phase in zip(witness['phases'],table['phases']):
        step = phase['step']
        first, rows, end = (phase[key] for key in ('first', 'rows', 'exclusive_end'))
        require(step == source['step'] == len(reports) and source['graph_sha256'] == phase['graph_sha256']
                and first == expect_first and first+rows == end and 0 < rows <= capacity-first,
                'KV phase differs from the selected compiler graph')
        name = f'phase-{step}/descriptors.bin'
        raw = (request/name).read_bytes()
        require(len(raw) == source['descriptor_bytes'] and len(raw)%REC_BYTES == 0 and
                sha256(raw).hexdigest() == manifest[name], f'changed descriptor arena at phase {step}')
        observed = read_destinations(raw, step, streams, bases, capacity, row_bytes, first, rows, cursors)
        require(all(position == end for position in cursors['positions']) and
                sum(observed.values()) == phase['required_commits'] == rows*len(streams),
                f'missing KV stores at phase {step}')
        expect_first = end
        totals.update(observed)
        reports.append(dict(step=step, first=first, rows=rows, exclusive_end=end,
                            stores=dict(observed), graph_sha256=source['graph_sha256']))
    registered = {row['opcode']: row['calls'] for row in read(request/'service-signatures.json')
                  if row['schema'] == SCHEMA and row['abi'] == 0x02500002 and
                  row['completion'] == 'destination_commit_ack'}
    require(totals == registered and expect_first == capacity and
            sum(totals.values()) == table['expected_commits'], 'KV command coverage differs from manifest')
    result = dict(schema='block-v2-request-kv-program-link/1',
                  request_sha256=request_sha, binding_sha256=hash_file(binding_path),
                  program_sha256=hash_file(program_path), base_sha256=admission['base_sha256'],
                  handoff_receipt_sha256=admission['receipt_sha256'],
                  topology=witness['topology'], streams=len(streams), stream_rows=capacity,
                  expected_stores=sum(totals.values()), expected_store_bytes=sum(totals.values())*row_bytes,
                  expected_stores_by_opcode=dict(totals), phase_records=reports,
                  status='requires_live_provider_and_ack', live_commit_proof=False)
    output.write_text(json.dumps(result, sort_keys=True, indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='phase_records'},sort_keys=True))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('request', 'binding_dir', 'handoff', 'output'):
        parser.add_argument(name, type=Path)
    audit(**vars(parser.parse_args()))
